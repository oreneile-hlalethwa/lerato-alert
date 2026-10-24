import logging

from django.contrib.auth.hashers import check_password, make_password

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Sum
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import models, serializers as s
from .services import ai, notify, places, storage

log = logging.getLogger('api')


def member_from(request):
    token = request.headers.get('X-Lerato-Token', '').strip()
    if not token:
        raise AuthenticationFailed('Missing app token.')
    member = models.Member.objects.filter(token=token).first()
    if not member:
        raise AuthenticationFailed('Unknown app token. Please register again.')
    return member


def valid(serializer_class, data):
    ser = serializer_class(data=data)
    ser.is_valid(raise_exception=True)
    return ser.validated_data


def query_float(request, name, lo, hi):
    try:
        v = float(request.query_params.get(name, ''))
    except ValueError:
        raise ValidationError({name: 'Must be a number.'})
    if not lo <= v <= hi:
        raise ValidationError({name: 'Out of range.'})
    return v


class Health(APIView):
    def get(self, request):
        return Response({
            'ok': True,
            'ai': bool(settings.ANTHROPIC_API_KEY),
            'alerts': notify.configured(),
            'places': bool(settings.GOOGLE_MAPS_API_KEY),
            'vault_backup': storage.configured(),
            'model': settings.ANTHROPIC_MODEL,
        })


# ---------- Users & contacts ----------
class Register(APIView):
    throttle_scope = 'register'

    def post(self, request):
        data = valid(s.RegisterSerializer, request.data)
        if models.Member.objects.filter(email__iexact=data['email']).exists():
            raise ValidationError({'email': 'An account with this email already exists. Please sign in.'})
        data['password'] = make_password(data['password'])
        member = models.Member.objects.create(**data)
        return Response({'id': str(member.id), 'token': member.token}, status=status.HTTP_201_CREATED)


class Login(APIView):
    throttle_scope = 'login'

    def post(self, request):
        data = valid(s.LoginSerializer, request.data)
        member = models.Member.objects.filter(email__iexact=data['email']).exclude(password='').order_by('-created').first()
        # Same message either way, so nobody can test which emails have accounts.
        if not member or not check_password(data['password'], member.password):
            raise AuthenticationFailed('Wrong email or password.')
        contacts = [{'id': c.id, 'name': c.name, 'channel': c.channel, 'value': c.value, 'type': c.type}
                    for c in member.contacts.order_by('created')]
        return Response({
            'id': str(member.id), 'token': member.token,
            'name': member.name, 'surname': member.surname, 'email': member.email, 'phone': member.phone,
            'contacts': contacts,
            'settings': member.settings or {},
        })


class Settings(APIView):
    throttle_scope = 'writes'

    def get(self, request):
        return Response(member_from(request).settings or {})

    def put(self, request):
        member = member_from(request)
        data = valid(s.SettingsSerializer, request.data)
        merged = dict(member.settings or {})
        merged.update({k: (dict(v) if isinstance(v, dict) else v) for k, v in data.items()})
        member.settings = merged
        member.save(update_fields=['settings'])
        return Response(merged)


class Contacts(APIView):
    throttle_scope = 'writes'

    def post(self, request):
        member = member_from(request)
        data = valid(s.ContactSerializer, request.data)
        if data['channel'] != 'email' and not settings.SMS_ENABLED:
            raise ValidationError('Only email alerts are available for now.')
        if member.contacts.count() >= 20:
            raise ValidationError('You can save up to 20 contacts.')
        contact = member.contacts.create(**data)
        return Response({'id': contact.id}, status=status.HTTP_201_CREATED)


class ContactDetail(APIView):
    throttle_scope = 'writes'

    def delete(self, request, pk):
        member = member_from(request)
        member.contacts.filter(pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------- Emergency alerts ----------
class Alerts(APIView):
    throttle_scope = 'alerts'

    def post(self, request):
        member = member_from(request)
        data = valid(s.AlertSerializer, request.data)
        loc = data.get('location') or {}
        contacts = [dict(c) for c in data['contacts']]
        if data['mode'] == 'home':
            # At home the abuser may know the family, so prefer security companies and organisations.
            outside = [c for c in contacts if c['type'] != 'kin']
            contacts = outside or contacts

        alert = models.Alert.objects.create(
            member=member, mode=data['mode'], reason=data['reason'],
            lat=loc.get('lat'), lng=loc.get('lng'), accuracy=loc.get('accuracy'),
            recipients=[{'name': c['name'], 'channel': c['channel'], 'type': c['type']} for c in contacts],
        )
        maps_link = f"https://maps.google.com/?q={loc['lat']:.6f},{loc['lng']:.6f}" if loc else None
        delivery = notify.send_alert(member, alert, contacts, maps_link)
        alert.delivery = delivery
        alert.save(update_fields=['delivery'])

        sent = sum(1 for d in delivery if d['status'].startswith('sent'))
        body = {'ok': True, 'alert_id': alert.id, 'sent': sent, 'total': len(contacts)}
        if not notify.configured():
            body.update(demo=True, note='(Alert saved. Messages will send once Brevo is set up.)')
        elif contacts and sent < len(contacts):
            body['note'] = f'({len(contacts) - sent} message(s) could not be delivered. Please also call for help.)'
        return Response(body, status=status.HTTP_201_CREATED)


class Reports(APIView):
    throttle_scope = 'writes'

    def post(self, request):
        data = valid(s.ReportSerializer, request.data)
        for _ in range(5):
            try:
                report = models.Report.objects.create(reference=models.new_reference('LA-R'), **data)
                break
            except IntegrityError:
                continue
        else:
            raise ValidationError('Please try again.')
        return Response({'reference': report.reference}, status=status.HTTP_201_CREATED)


# ---------- Help ----------
class ServicesNearby(APIView):
    def get(self, request):
        kind = request.query_params.get('type', 'care')
        if kind not in places.QUERIES:
            raise ValidationError({'type': 'Unknown service type.'})
        lat = query_float(request, 'lat', -90, 90)
        lng = query_float(request, 'lng', -180, 180)
        return Response(places.nearby(kind, lat, lng))


# ---------- AI ----------
class AIView(APIView):
    throttle_scope = 'ai'

    def run(self, fn):
        try:
            return Response(fn())
        except ValueError as exc:
            raise ValidationError(str(exc))
        except ai.AIUnavailable:
            return Response({'error': 'AI is unavailable right now.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class AIReferral(AIView):
    def post(self, request):
        data = valid(s.ChatSerializer, request.data)
        msgs = [dict(m) for m in data['messages']]
        return self.run(lambda: ai.referral(msgs, data['turn'], data.get('max_turns') or 3))


class AIFriend(AIView):
    def post(self, request):
        data = valid(s.ChatSerializer, request.data)
        msgs = [dict(m) for m in data['messages']]
        return self.run(lambda: ai.friend(msgs))


class AILesson(AIView):
    def post(self, request):
        data = valid(s.TopicSerializer, request.data)
        return self.run(lambda: ai.lesson(data['topic']))


class LessonSuggest(APIView):
    throttle_scope = 'writes'

    def post(self, request):
        data = valid(s.TopicSerializer, request.data)
        models.LessonSuggestion.objects.create(topic=data['topic'].strip())
        return Response({'ok': True}, status=status.HTTP_201_CREATED)


# ---------- Fund ----------
class FundApply(APIView):
    throttle_scope = 'writes'

    def post(self, request):
        member = member_from(request)
        data = valid(s.FundApplySerializer, request.data)
        if member.fund_applications.filter(status='review').exists():
            raise ValidationError('You already have a request in review.')
        app = member.fund_applications.create(**data)
        return Response({'id': app.id, 'status': app.status}, status=status.HTTP_201_CREATED)


class FundDonate(APIView):
    throttle_scope = 'writes'

    def post(self, request):
        data = valid(s.DonateSerializer, request.data)
        name = (data.get('display_name') or '').strip() or 'Anonymous'
        for _ in range(5):
            try:
                donation = models.Donation.objects.create(
                    reference=models.new_reference('LA-SBX'), amount=data['amount'], last4=data['last4'],
                    bank=data.get('bank') or 'FNB', display_name=name, status='sandbox',
                )
                break
            except IntegrityError:
                continue
        else:
            raise ValidationError('Please try again.')
        return Response({'reference': donation.reference, 'status': donation.status}, status=status.HTTP_201_CREATED)


class FundSummary(APIView):
    def get(self, request):
        donations = models.Donation.objects.all()
        total = donations.aggregate(t=Sum('amount'))['t'] or 0
        by_cause = (models.FundAllocation.objects.values('cause').annotate(amount=Sum('amount')).order_by('-amount'))
        causes = [{'name': c['cause'], 'amount': c['amount']} for c in by_cause]
        allocated = sum(c['amount'] for c in causes)
        if total > allocated:
            causes.append({'name': 'Awaiting allocation', 'amount': total - allocated})
        sponsors = [
            {'display_name': d.display_name, 'amount': d.amount, 'created': d.created.isoformat()}
            for d in donations[:50]
        ]
        demo_data = donations.filter(is_demo=True).exists() or models.FundAllocation.objects.filter(is_demo=True).exists()
        return Response({
            'total': total, 'sponsor_count': donations.count(),
            'causes': causes, 'sponsors': sponsors, 'demo': False, 'demo_data': demo_data,
        })


# ---------- Safety map ----------
class Hotspots(APIView):
    def get(self, request):
        lat = query_float(request, 'lat', -90, 90)
        lng = query_float(request, 'lng', -180, 180)
        box = 0.15  # roughly 15 km
        qs = models.Hotspot.objects.filter(
            active=True, lat__range=(lat - box, lat + box), lng__range=(lng - box, lng + box),
        )[:100]
        results = [{
            'label': h.label, 'note': h.note, 'lat': h.lat, 'lng': h.lng, 'radius': h.radius,
            'level': h.level, 'category': h.category, 'night': h.night,
        } for h in qs]
        return Response({'results': results, 'demo': any(h.is_demo for h in qs)})


# ---------- Evidence vault backup (Cloudinary) ----------
class Vault(APIView):
    throttle_scope = 'vault'
    KIND_TYPES = {'audio': ('audio/', 'video/webm', 'video/mp4'), 'photo': ('image/',), 'video': ('video/',)}

    def get(self, request):
        member = member_from(request)
        items = []
        for it in member.vault_items.all()[:100]:
            row = {'id': it.id, 'client_id': it.client_id, 'kind': it.kind, 'title': it.title,
                   'created': it.captured.isoformat(), 'text': it.text}
            if it.public_id and storage.configured():
                row['url'] = storage.signed_url(it)
            items.append(row)
        return Response({'results': items})

    def post(self, request):
        member = member_from(request)
        data = valid(s.VaultItemSerializer, request.data)
        existing = member.vault_items.filter(client_id=data['client_id']).first()
        if existing:
            return Response({'id': existing.id, 'duplicate': True})
        if member.vault_items.count() >= 500:
            raise ValidationError('Vault is full.')

        kind = data['kind']
        fields = {'client_id': data['client_id'], 'kind': kind, 'title': data['title'], 'captured': data['created']}
        if kind == 'note':
            if not data.get('text'):
                raise ValidationError({'text': 'A note needs text.'})
            fields['text'] = data['text']
        else:
            f = request.FILES.get('file')
            if not f:
                raise ValidationError({'file': 'Attach the file.'})
            if f.size > settings.VAULT_MAX_MB * 1024 * 1024:
                raise ValidationError({'file': f'Files must be under {settings.VAULT_MAX_MB} MB.'})
            if not (f.content_type or '').startswith(self.KIND_TYPES[kind]):
                raise ValidationError({'file': 'That file type does not match.'})
            if not storage.configured():
                return Response({'error': 'Cloud backup is not set up yet.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            try:
                fields.update(storage.upload(f, kind, member.id))
            except storage.StorageUnavailable:
                return Response({'error': 'Upload failed. It will retry.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            item = member.vault_items.create(**fields)
        except IntegrityError:  # the same item arrived twice at once
            item = member.vault_items.get(client_id=data['client_id'])
        return Response({'id': item.id}, status=status.HTTP_201_CREATED)


class VaultItemDetail(APIView):
    throttle_scope = 'vault'

    def delete(self, request, pk):
        member = member_from(request)
        item = member.vault_items.filter(pk=pk).first()
        if item:
            storage.delete(item)
            item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)