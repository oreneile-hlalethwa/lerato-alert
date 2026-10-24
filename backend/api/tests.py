"""Run with:  python manage.py test api"""
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from . import models
from .services import ai, notify


@override_settings(BREVO_API_KEY='', BREVO_SENDER_EMAIL='', ANTHROPIC_API_KEY='', GOOGLE_MAPS_API_KEY='')
class ApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.c = APIClient()
        res = self.c.post('/api/users/register/', {'name': 'Thandi', 'surname': 'Mokoena', 'email': 't@example.com', 'phone': '071 234 5678', 'password': 'safe-pass-1'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.token = res.json()['token']

    def auth(self):
        return {'HTTP_X_LERATO_TOKEN': self.token}

    def test_register_validates_phone(self):
        res = self.c.post('/api/users/register/', {'name': 'A', 'surname': 'B', 'email': 'a@b.co', 'phone': '123', 'password': 'safe-pass-1'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_password_is_hashed_and_login_restores_account(self):
        from .models import Member
        m = Member.objects.get(email='t@example.com')
        self.assertNotEqual(m.password, 'safe-pass-1')
        self.c.post('/api/contacts/', {'name': 'Mom', 'channel': 'email', 'value': 'mom@example.com', 'type': 'kin'}, format='json', **self.auth())
        bad = self.c.post('/api/users/login/', {'email': 'T@example.com', 'password': 'wrong-pass'}, format='json')
        self.assertEqual(bad.status_code, 403)
        ok = self.c.post('/api/users/login/', {'email': 'T@example.com', 'password': 'safe-pass-1'}, format='json')
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()['token'], self.token)
        self.assertEqual(ok.json()['contacts'][0]['name'], 'Mom')

    def test_register_rejects_duplicate_email_and_short_password(self):
        dup = self.c.post('/api/users/register/', {'name': 'A', 'surname': 'B', 'email': 'T@example.com', 'phone': '0712345670', 'password': 'safe-pass-1'}, format='json')
        self.assertEqual(dup.status_code, 400)
        short = self.c.post('/api/users/register/', {'name': 'A', 'surname': 'B', 'email': 'n@example.com', 'phone': '0712345670', 'password': 'short'}, format='json')
        self.assertEqual(short.status_code, 400)

    def test_settings_sync_and_restore_on_login(self):
        lock = {'salt': 'ab' * 16, 'hash': 'cd' * 32, 'iter': 150000}
        body = {'safe_word': 'pineapple', 'disguise_type': 'messages', 'secret_lock': lock, 'vault_pin': lock}
        self.assertEqual(self.c.put('/api/users/settings/', body, format='json').status_code, 403)
        self.assertEqual(self.c.put('/api/users/settings/', body, format='json', **self.auth()).status_code, 200)
        plain = dict(body, vault_pin='123456')
        self.assertEqual(self.c.put('/api/users/settings/', plain, format='json', **self.auth()).status_code, 400)
        s = self.c.post('/api/users/login/', {'email': 't@example.com', 'password': 'safe-pass-1'}, format='json').json()['settings']
        self.assertEqual(s['safe_word'], 'pineapple')
        self.assertEqual(s['disguise_type'], 'messages')
        self.assertEqual(s['vault_pin'], lock)

    def test_contact_delete(self):
        cid = self.c.post('/api/contacts/', {'name': 'Mom', 'channel': 'email', 'value': 'mom@example.com', 'type': 'kin'}, format='json', **self.auth()).json()['id']
        self.assertEqual(self.c.delete(f'/api/contacts/{cid}/', **self.auth()).status_code, 204)
        login = self.c.post('/api/users/login/', {'email': 't@example.com', 'password': 'safe-pass-1'}, format='json').json()
        self.assertEqual(login['contacts'], [])

    def test_contacts_need_token(self):
        body = {'name': 'Mom', 'channel': 'email', 'value': 'mom@example.com', 'type': 'kin'}
        self.assertEqual(self.c.post('/api/contacts/', body, format='json').status_code, 403)
        self.assertEqual(self.c.post('/api/contacts/', body, format='json', **self.auth()).status_code, 201)
        sms = {'name': 'Mom', 'channel': 'number', 'value': '0712345678', 'type': 'kin'}
        self.assertEqual(self.c.post('/api/contacts/', sms, format='json', **self.auth()).status_code, 400)

    @override_settings(BREVO_API_KEY='k', BREVO_SENDER_EMAIL='alerts@example.com', SMS_ENABLED=False)
    def test_email_only_mode_still_alerts(self):
        body = {'mode': 'jogging', 'reason': 'Scream detected', 'contacts': [
            {'name': 'Old phone contact', 'channel': 'number', 'value': '0712345678', 'type': 'kin'},
            {'name': 'Sis', 'channel': 'email', 'value': 'sis@example.com', 'type': 'kin'}]}
        ok = mock.Mock(status_code=201, content=b'{}', json=lambda: {})
        with mock.patch('api.services.notify.requests.post', return_value=ok) as post:
            res = self.c.post('/api/alerts/', body, format='json', **self.auth())
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['sent'], 1)
        self.assertEqual(post.call_count, 1)

    def test_alert_saved_and_home_mode_skips_kin(self):
        body = {
            'mode': 'home', 'reason': 'Safe word heard',
            'location': {'lat': -25.75, 'lng': 28.23, 'accuracy': 12},
            'contacts': [
                {'name': 'Mom', 'channel': 'number', 'value': '0712345678', 'type': 'kin'},
                {'name': 'Armed response', 'channel': 'email', 'value': 'ops@example.com', 'type': 'security'},
            ],
        }
        res = self.c.post('/api/alerts/', body, format='json', **self.auth())
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()['demo'])
        alert = models.Alert.objects.get()
        self.assertEqual([r['name'] for r in alert.recipients], ['Armed response'])

    @override_settings(BREVO_API_KEY='k', BREVO_SENDER_EMAIL='alerts@example.com', SMS_ENABLED=True)
    def test_alert_sends_email_and_sms(self):
        calls = []
        def fake_post(url, json, headers, timeout):
            calls.append((url, json))
            return mock.Mock(status_code=201, content=b'{}', json=lambda: {})
        body = {
            'mode': 'jogging', 'reason': 'Scream detected', 'location': {'lat': -25.75, 'lng': 28.23},
            'contacts': [
                {'name': 'Mom', 'channel': 'number', 'value': '0712345678', 'type': 'kin'},
                {'name': 'Sis', 'channel': 'email', 'value': 'sis@example.com', 'type': 'kin'},
            ],
        }
        with mock.patch('api.services.notify.requests.post', side_effect=fake_post):
            res = self.c.post('/api/alerts/', body, format='json', **self.auth())
        self.assertEqual(res.json()['sent'], 2)
        sms = next(j for u, j in calls if u.endswith('/transactionalSMS/send'))
        self.assertEqual(sms['recipient'], '27712345678')
        self.assertIn('maps.google.com/?q=-25.750000,28.230000', sms['content'])
        email = next(j for u, j in calls if u.endswith('/smtp/email'))
        self.assertIn('Thandi Mokoena', email['subject'])

    def test_msisdn(self):
        self.assertEqual(notify.to_msisdn('+27 71 234 5678'), '27712345678')
        self.assertEqual(notify.to_msisdn('0712345678'), '27712345678')

    def test_anonymous_report(self):
        res = self.c.post('/api/reports/', {'kind': 'Physical abuse', 'area': 'Soshanguve', 'evidence_count': 2}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()['reference'].startswith('LA-R-'))

    def test_ai_returns_503_without_key(self):
        res = self.c.post('/api/ai/friend/', {'messages': [{'role': 'assistant', 'content': 'Hi'}, {'role': 'user', 'content': 'Help'}]}, format='json')
        self.assertEqual(res.status_code, 503)

    def test_referral_final_turn_gives_action(self):
        out = {'reply': 'I recommend a shelter.', 'options': [], 'done': True, 'referral': 'shelter'}
        with mock.patch.object(ai, '_call_tool', return_value=out):
            res = self.c.post('/api/ai/referral/', {'turn': 3, 'max_turns': 3, 'messages': [
                {'role': 'assistant', 'content': 'Are you safe?'}, {'role': 'user', 'content': 'Yes'},
                {'role': 'assistant', 'content': 'What do you need?'}, {'role': 'user', 'content': 'A place to stay'},
                {'role': 'assistant', 'content': 'Anyone with you?'}, {'role': 'user', 'content': 'My kids'},
            ]}, format='json')
        data = res.json()
        self.assertTrue(data['done'])
        self.assertEqual(data['action']['label'], 'Find shelters near me')

    def test_clean_history(self):
        h = ai.clean_history([{'role': 'assistant', 'content': 'Hi'}, {'role': 'user', 'content': 'a'}, {'role': 'user', 'content': 'b'}])
        self.assertEqual([m['role'] for m in h], ['user', 'assistant', 'user'])
        self.assertEqual(h[-1]['content'], 'a\nb')

    def test_lesson(self):
        out = {'title': 'Online safety', 'intro': 'x', 'points': [{'title': 'a', 'body': 'b'}, {'title': 'c', 'body': 'd'}], 'takeaway': 't'}
        with mock.patch.object(ai, '_call_tool', return_value=out):
            res = self.c.post('/api/ai/lesson/', {'topic': 'Online harassment'}, format='json')
        self.assertEqual(res.json()['title'], 'Online safety')

    def test_fund_flow(self):
        apply = {'needs': ['Transport'], 'amount': 400, 'phone': '0712345678', 'password': 'safe-pass-1'}
        self.assertEqual(self.c.post('/api/fund/apply/', apply, format='json', **self.auth()).status_code, 201)
        self.assertEqual(self.c.post('/api/fund/apply/', apply, format='json', **self.auth()).status_code, 400)
        res = self.c.post('/api/fund/donate/', {'amount': 100, 'last4': '0002', 'display_name': 'Thandi M'}, format='json')
        self.assertEqual(res.status_code, 201)
        summary = self.c.get('/api/fund/summary/').json()
        self.assertEqual(summary['total'], 100)
        self.assertEqual(summary['causes'], [{'name': 'Awaiting allocation', 'amount': 100}])
        self.assertEqual(summary['sponsors'][0]['display_name'], 'Thandi M')

    def test_hotspots_and_seed(self):
        from django.core.management import call_command
        call_command('seed_demo', lat=-25.75, lng=28.23, stdout=mock.Mock())
        data = self.c.get('/api/hotspots/?lat=-25.75&lng=28.23').json()
        self.assertEqual(len(data['results']), 6)
        self.assertTrue(data['demo'])
        self.assertEqual(self.c.get('/api/hotspots/?lat=10&lng=10').json()['results'], [])
        self.assertEqual(self.c.get('/api/hotspots/?lat=abc&lng=1').status_code, 400)

    def test_frontend_served(self):
        res = self.c.get('/')
        self.assertEqual(res.status_code, 200)


@override_settings(CLOUDINARY_URL='cloudinary://key:secret@demo')
class VaultTests(TestCase):
    def setUp(self):
        self.c = APIClient()
        res = self.c.post('/api/users/register/', {'name': 'T', 'surname': 'M', 'email': 't@example.com', 'phone': '0712345678', 'password': 'safe-pass-1'}, format='json')
        self.h = {'HTTP_X_LERATO_TOKEN': res.json()['token']}

    def test_upload_list_delete(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake = {'public_id': 'lerato/u/abc', 'resource_type': 'video', 'format': 'webm', 'bytes': 1234}
        audio = SimpleUploadedFile('rec.webm', b'\x1aE\xdf\xa3fake', content_type='audio/webm;codecs=opus')
        body = {'client_id': '1700-abcde', 'kind': 'audio', 'title': 'Auto-recording · alert', 'created': '2026-10-23T20:00:00Z', 'file': audio}
        with mock.patch('api.services.storage.upload', return_value=fake) as up:
            res = self.c.post('/api/vault/', body, format='multipart', **self.h)
            self.assertEqual(res.status_code, 201, res.content)
            again = self.c.post('/api/vault/', dict(body, file=SimpleUploadedFile('rec.webm', b'x', content_type='audio/webm')), format='multipart', **self.h)
        self.assertTrue(again.json()['duplicate'])
        self.assertEqual(up.call_count, 1)

        note = {'client_id': 'n-1', 'kind': 'note', 'title': 'Incident note', 'text': 'He took my phone', 'created': '2026-10-23T20:05:00Z'}
        self.assertEqual(self.c.post('/api/vault/', note, format='json', **self.h).status_code, 201)

        listed = self.c.get('/api/vault/', **self.h).json()['results']
        self.assertEqual(len(listed), 2)
        audio_row = next(r for r in listed if r['kind'] == 'audio')
        self.assertIn('type=authenticated', audio_row['url'])
        self.assertIn('expires_at=', audio_row['url'])

        with mock.patch('api.services.storage.cloudinary.uploader.destroy') as destroy:
            self.assertEqual(self.c.delete(f"/api/vault/{audio_row['id']}/", **self.h).status_code, 204)
        destroy.assert_called_once()
        self.assertEqual(models.VaultItem.objects.count(), 1)

    def test_wrong_type_and_no_token(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        body = {'client_id': 'p1', 'kind': 'photo', 'title': 'Photo', 'created': '2026-10-23T20:00:00Z',
                'file': SimpleUploadedFile('x.exe', b'MZ', content_type='application/octet-stream')}
        self.assertEqual(self.c.post('/api/vault/', body, format='multipart', **self.h).status_code, 400)
        self.assertEqual(self.c.get('/api/vault/').status_code, 403)

    def test_other_member_cannot_delete(self):
        item = models.VaultItem.objects.create(member=models.Member.objects.get(), client_id='a', kind='note',
                                               title='n', text='t', captured='2026-10-23T20:00:00Z')
        other = self.c.post('/api/users/register/', {'name': 'X', 'surname': 'Y', 'email': 'x@example.com', 'phone': '0712345679', 'password': 'safe-pass-1'}, format='json').json()['token']
        self.c.delete(f'/api/vault/{item.id}/', HTTP_X_LERATO_TOKEN=other)
        self.assertTrue(models.VaultItem.objects.filter(pk=item.pk).exists())