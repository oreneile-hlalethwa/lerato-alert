"""Nearest verified help, using Google Places API (New) Text Search."""
import logging
import math

import requests
from django.conf import settings
from django.core.cache import cache

log = logging.getLogger('api')

QUERIES = {
    'care': 'Thuthuzela Care Centre',
    'police': 'police station',
    'shelter': "women's shelter",
    'hospital': 'hospital',
}
FIELDS = 'places.displayName,places.formattedAddress,places.location,places.currentOpeningHours.openNow'


def distance_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def nearby(kind, lat, lng):
    if not settings.GOOGLE_MAPS_API_KEY:
        return {'results': [], 'configured': False}
    key = f'places:{kind}:{lat:.3f}:{lng:.3f}'
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        res = requests.post(
            'https://places.googleapis.com/v1/places:searchText',
            json={
                'textQuery': QUERIES[kind],
                'locationBias': {'circle': {'center': {'latitude': lat, 'longitude': lng}, 'radius': 15000.0}},
                'pageSize': 6,
                'regionCode': 'ZA',
            },
            headers={'X-Goog-Api-Key': settings.GOOGLE_MAPS_API_KEY, 'X-Goog-FieldMask': FIELDS},
            timeout=8,
        )
        res.raise_for_status()
        places = res.json().get('places', [])
    except Exception as exc:
        log.warning('Places lookup failed: %s', exc)
        return {'results': [], 'configured': True, 'error': True}

    results = []
    for p in places:
        loc = p.get('location') or {}
        if 'latitude' not in loc:
            continue
        results.append({
            'name': (p.get('displayName') or {}).get('text', 'Unnamed'),
            'address': p.get('formattedAddress', ''),
            'lat': loc['latitude'],
            'lng': loc['longitude'],
            'open_now': (p.get('currentOpeningHours') or {}).get('openNow'),
            'distance_km': round(distance_km(lat, lng, loc['latitude'], loc['longitude']), 1),
        })
    results.sort(key=lambda r: r['distance_km'])
    data = {'results': results, 'configured': True}
    cache.set(key, data, 600)
    return data
