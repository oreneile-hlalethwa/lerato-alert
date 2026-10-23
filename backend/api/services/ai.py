import copy
import hashlib
import json
import logging

import anthropic
from django.conf import settings
from django.core.cache import cache

log = logging.getLogger('api')


class AIUnavailable(Exception):
    pass


SA_RESOURCES = """Only use these South African numbers. Never invent phone numbers, statistics, laws or organisations:
- GBV Command Centre: 0800 428 428 (free, 24/7), or SMS "HELP" to 31531
- SAPS emergency: 10111
- Legal Aid SA advice line: 0800 110 110
- Childline: 116
- SADAG Suicide Crisis Helpline: 0800 567 567
Other help: Thuthuzela Care Centres (rape care: medical, counselling and police in one place), women's shelters,
and free protection orders at any magistrate's court."""

STYLE = """Write in warm, plain South African English a stressed person can read on a phone: short sentences, no jargon,
no markdown, no emoji. Never blame the person. Never tell them to confront an abuser. Respect their choices.
If anyone is in immediate danger, tell them to call SAPS on 10111 first. If they mention suicide or self-harm,
gently give the SADAG Suicide Crisis Helpline, 0800 567 567."""

_client = None


def client():
    global _client
    if not settings.ANTHROPIC_API_KEY:
        raise AIUnavailable('ANTHROPIC_API_KEY is not set')
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=45.0, max_retries=1)
    return _client


def _strict(schema):
    schema = copy.deepcopy(schema)

    def walk(node):
        if isinstance(node, dict):
            if node.get('type') == 'object':
                node['additionalProperties'] = False
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)
    return schema


def _call_tool(system, messages, tool, max_tokens):
    try:
        res = client().messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_config={'format': {'type': 'json_schema', 'schema': _strict(tool['input_schema'])}},
        )
    except anthropic.APIError as exc:
        log.warning('Anthropic API error: %s', exc)
        raise AIUnavailable(str(exc)) from exc
    if res.stop_reason in ('refusal', 'max_tokens'):
        raise AIUnavailable(f'Stopped early: {res.stop_reason}')
    text = ''.join(b.text for b in res.content if b.type == 'text').strip()
    try:
        return json.loads(text)
    except ValueError as exc:
        raise AIUnavailable('Reply was not valid JSON') from exc


def clean_history(messages):
    out = []
    for m in messages[-16:]:
        role = m.get('role')
        text = str(m.get('content', '')).strip()[:1500]
        if role not in ('user', 'assistant') or not text:
            continue
        if out and out[-1]['role'] == role:
            out[-1]['content'] += '\n' + text
        else:
            out.append({'role': role, 'content': text})
    if out and out[0]['role'] == 'assistant':
        out.insert(0, {'role': 'user', 'content': '(I opened the chat.)'})
    if not out or out[-1]['role'] != 'user':
        raise ValueError('The last message must be from the user.')
    return out


def _options(value, limit, length=60):
    return [str(o).strip()[:length] for o in (value or []) if str(o).strip()][:limit]


REFERRAL_TOOL = {
    'name': 'respond',
    'description': 'Send the next chat message.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'reply': {'type': 'string', 'description': 'Your message, 1 to 4 short sentences.'},
            'options': {'type': 'array', 'items': {'type': 'string'}, 'description': '2 to 4 short tap-to-answer replies for your question. Empty when done.'},
            'done': {'type': 'boolean', 'description': 'True only when this message is your final recommendation.'},
            'referral': {'type': 'string', 'enum': ['shelter', 'care_centre', 'police', 'counsellor', 'legal', 'none']},
        },
        'required': ['reply', 'options', 'done', 'referral'],
    },
}
REFERRAL_ACTIONS = {
    'shelter': {'href': 'index.html', 'label': 'Find shelters near me'},
    'care_centre': {'href': 'index.html', 'label': 'Find the nearest care centre'},
    'police': {'href': 'index.html', 'label': 'Find a police station'},
    'counsellor': {'href': 'tel:0800428428', 'label': 'Call 0800 428 428'},
    'legal': {'href': 'tel:0800110110', 'label': 'Call Legal Aid SA'},
}


def referral(messages, turn, max_turns=3):
    history = clean_history(messages)
    max_turns = max_turns or 3
    if turn >= max_turns:
        step = ('You have asked enough questions. Now give your final recommendation: name the one best service for them, '
                'say why in one sentence and what to expect there. Set done=true and choose the matching referral.')
    else:
        step = (f'Briefly acknowledge their answer, then ask question {turn + 1} of {max_turns}. One question only. '
                'Useful things to learn: whether they are safe right now, what they need most (a safe place, medical care, '
                'reporting to police, legal help, someone to talk to), and whether children are with them. '
                'Set done=false and referral="none".')
    system = ('You are the private referral helper inside Lerato Alert, a South African gender-based violence safety app. '
              'Your job is to find the single best service for the person in a few short questions.\n'
              f'{STYLE}\n{SA_RESOURCES}\n\n{step}')
    out = _call_tool(system, history, REFERRAL_TOOL, 600)
    done = bool(out.get('done')) or turn >= max_turns
    data = {'reply': str(out.get('reply', '')).strip()[:900], 'done': done}
    if done:
        action = REFERRAL_ACTIONS.get(out.get('referral'))
        if action:
            data['action'] = action
    else:
        data['options'] = _options(out.get('options'), 4)
    if not data['reply']:
        raise AIUnavailable('Empty reply')
    return data


FRIEND_TOOL = {
    'name': 'respond',
    'description': 'Send the next chat message.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'reply': {'type': 'string', 'description': 'A practical, specific answer in 2 to 5 short sentences.'},
            'options': {'type': 'array', 'items': {'type': 'string'}, 'description': '2 short follow-up questions the user might ask next, written in their voice.'},
        },
        'required': ['reply', 'options'],
    },
}


def friend(messages):
    history = clean_history(messages)
    system = ('You are the "Help a friend" guide inside Lerato Alert, a South African gender-based violence safety app. '
              'The user wants to support a friend or family member who may be experiencing abuse. Give concrete, '
              'trauma-informed advice: believe them, listen, do not judge, let them lead, help them stay safe, and share '
              'professional help. Explain that reporting without the person\'s agreement can raise their risk, unless '
              'someone is in immediate danger. Answer the actual question, and vary your wording so it never sounds scripted. '
              'If the question is not about supporting someone or staying safe, kindly steer back to that.\n'
              f'{STYLE}\n{SA_RESOURCES}')
    out = _call_tool(system, history, FRIEND_TOOL, 700)
    reply = str(out.get('reply', '')).strip()[:1200]
    if not reply:
        raise AIUnavailable('Empty reply')
    return {'reply': reply, 'options': _options(out.get('options'), 2, 80)}


LESSON_TOOL = {
    'name': 'lesson',
    'description': 'Return a short mobile lesson.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'title': {'type': 'string', 'description': 'Under 40 characters.'},
            'intro': {'type': 'string', 'description': 'One or two sentences.'},
            'points': {
                'type': 'array',
                'description': '3 to 5 key points.',
                'items': {
                    'type': 'object',
                    'properties': {
                        'title': {'type': 'string', 'description': 'Under 45 characters.'},
                        'body': {'type': 'string', 'description': 'One or two sentences.'},
                    },
                    'required': ['title', 'body'],
                },
            },
            'takeaway': {'type': 'string', 'description': 'One sentence to remember, with a helpline if useful.'},
        },
        'required': ['title', 'intro', 'points', 'takeaway'],
    },
}


def lesson(topic):
    topic = ' '.join(str(topic).split())[:80]
    key = 'lesson:' + hashlib.sha256(topic.lower().encode()).hexdigest()[:32]
    cached = cache.get(key)
    if cached:
        return cached
    system = ('You write short, accurate prevention lessons for Lerato Alert, a South African gender-based violence safety app. '
              'Lessons are read on a phone in about 4 minutes. Be practical and specific to South Africa. '
              'If the topic is not about safety, relationships, consent, abuse, gender-based violence, wellbeing or getting help, '
              'write a lesson called "Staying safe and getting help" instead.\n'
              f'{STYLE}\n{SA_RESOURCES}')
    out = _call_tool(system, [{'role': 'user', 'content': f'Write a lesson on: {topic}'}], LESSON_TOOL, 1200)
    points = [
        {'title': str(p.get('title', ''))[:60], 'body': str(p.get('body', ''))[:300]}
        for p in (out.get('points') or []) if isinstance(p, dict) and p.get('title')
    ][:5]
    if not out.get('title') or len(points) < 2:
        raise AIUnavailable('Incomplete lesson')
    data = {
        'title': str(out['title'])[:60],
        'intro': str(out.get('intro', ''))[:400],
        'points': points,
        'takeaway': str(out.get('takeaway', ''))[:300],
    }
    cache.set(key, data, 3600)
    return data