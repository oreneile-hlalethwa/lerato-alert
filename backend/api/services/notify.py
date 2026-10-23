"""Emergency alerts through Brevo (email + SMS)."""
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from html import escape

import requests
from django.conf import settings
from django.utils import timezone

log = logging.getLogger('api')
BREVO = 'https://api.brevo.com/v3'


def configured():
    return bool(settings.BREVO_API_KEY and settings.BREVO_SENDER_EMAIL)


def to_msisdn(phone):
    """'071 234 5678' or '+27712345678' -> '27712345678' (digits only, as Brevo wants)."""
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('0') and len(digits) == 10:
        digits = '27' + digits[1:]
    return digits


def _post(path, body):
    res = requests.post(
        BREVO + path,
        json=body,
        headers={'api-key': settings.BREVO_API_KEY, 'accept': 'application/json', 'content-type': 'application/json'},
        timeout=10,
    )
    if res.status_code >= 300:
        raise RuntimeError(f'Brevo {res.status_code}: {res.text[:200]}')
    return res.json() if res.content else {}


def _alert_text(member, alert, maps_link):
    who = f'{member.name} {member.surname}'.strip()
    return who, (
        f'LERATO ALERT: {who} may be in danger ({alert.reason}). '
        + (f'Live location: {maps_link} ' if maps_link else 'Location unavailable. ')
        + f'Call them: {member.phone}. If you cannot reach them, call SAPS 10111.'
    )


def _email_html(member, alert, maps_link, when):
    who = escape(f'{member.name} {member.surname}'.strip())
    loc = (f'<p><a href="{escape(maps_link)}" style="display:inline-block;background:#C2502F;color:#fff;'
           f'padding:12px 20px;border-radius:24px;text-decoration:none;font-weight:700">Open live location</a></p>'
           if maps_link else '<p>Their location could not be found.</p>')
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#1A1A1A">
      <h2 style="color:#C2502F;margin-bottom:4px">{who} may be in danger</h2>
      <p style="margin-top:0;color:#5F5E5B">Sent by Lerato Alert at {escape(when)}</p>
      <p><strong>What happened:</strong> {escape(alert.reason)}<br>
         <strong>Mode:</strong> {escape(alert.get_mode_display())}</p>
      {loc}
      <p><strong>Call them:</strong> {escape(member.phone)}</p>
      <p>If you can't reach them, call <strong>SAPS 10111</strong>. Please don't call or message them
         about this alert if someone else might see it.</p>
      <p style="font-size:12px;color:#5F5E5B">You received this because {who} added you as a trusted contact on Lerato Alert.</p>
    </div>"""


def _send_one(contact, member, alert, maps_link, when):
    who, sms = _alert_text(member, alert, maps_link)
    result = {'name': contact['name'], 'channel': contact['channel']}
    try:
        if contact['channel'] == 'email':
            _post('/smtp/email', {
                'sender': {'name': settings.BREVO_SENDER_NAME, 'email': settings.BREVO_SENDER_EMAIL},
                'to': [{'email': contact['value'], 'name': contact['name']}],
                'subject': f'URGENT: {who} may be in danger',
                'htmlContent': _email_html(member, alert, maps_link, when),
                'textContent': sms,
                'tags': ['lerato-alert'],
            })
            result['status'] = 'sent'
        else:
            # WhatsApp needs a paid Brevo plan, so WhatsApp contacts get an SMS for now.
            if not settings.SMS_ENABLED:
                result['status'] = 'skipped: SMS disabled'
            else:
                _post('/transactionalSMS/send', {
                    'sender': settings.BREVO_SMS_SENDER,
                    'recipient': to_msisdn(contact['value']),
                    'content': sms,
                    'type': 'transactional',
                    'tag': 'lerato-alert',
                })
                result['status'] = 'sent' if contact['channel'] == 'number' else 'sent as SMS'
    except Exception as exc:  # one failed contact must never stop the others
        log.warning('Alert delivery failed for %s: %s', contact['channel'], exc)
        result['status'] = 'failed'
    return result


def send_alert(member, alert, contacts, maps_link):
    """Notify every contact in parallel. Returns a list of per-contact results."""
    if not configured():
        return [{'name': c['name'], 'channel': c['channel'], 'status': 'skipped: Brevo not configured'} for c in contacts]
    when = timezone.localtime(alert.created).strftime('%d %b %Y, %H:%M')
    with ThreadPoolExecutor(max_workers=5) as pool:
        return list(pool.map(lambda c: _send_one(c, member, alert, maps_link, when), contacts))
