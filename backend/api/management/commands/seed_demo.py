"""Load clearly-marked sample data for the hackathon demo.

    python manage.py seed_demo                      # around Pretoria CBD
    python manage.py seed_demo --lat -25.54 --lng 28.10
    python manage.py seed_demo --clear              # remove all demo rows
"""
from django.core.management.base import BaseCommand

from api.models import Donation, FundAllocation, Hotspot, new_reference

SPOTS = [
    (0.006, 0.004, 'red', 'robbery', True, 'Taxi rank', 'Robbery reports after 18:00', 260),
    (-0.008, -0.006, 'heads', 'assault', True, 'Park footpath', 'Assault reports, poorly lit', 200),
    (0.011, -0.010, 'aware', 'robbery', False, 'Shopping centre parking', 'Occasional bag snatching', 200),
    (-0.012, 0.011, 'red', 'murder', True, 'Open field near rail line', 'Serious violent incidents reported', 260),
    (0.002, -0.013, 'heads', 'robbery', False, 'Main road bridge', 'Phone theft at traffic lights', 200),
    (-0.003, 0.008, 'clear', 'none', False, 'Community patrol area', 'Regular patrols, few reports', 200),
]
DONATIONS = [('Thabo M.', 500), ('Anonymous', 100), ('Naledi K.', 250), ('Sample CSI Partner', 10000),
             ('Anonymous', 50), ('Lebo S.', 300)]
ALLOCATIONS = [('Emergency transport', 3400), ('Safe shelter stays', 2900), ('Legal support', 1950), ('Food & essentials', 1450)]


class Command(BaseCommand):
    help = 'Add or remove clearly-marked demo data (hotspots, donations, allocations).'

    def add_arguments(self, parser):
        parser.add_argument('--lat', type=float, default=-25.7479)
        parser.add_argument('--lng', type=float, default=28.2293)
        parser.add_argument('--clear', action='store_true')

    def handle(self, *args, **opts):
        removed = sum(m.objects.filter(is_demo=True).delete()[0] for m in (Hotspot, Donation, FundAllocation))
        if opts['clear']:
            self.stdout.write(self.style.SUCCESS(f'Removed {removed} demo rows.'))
            return
        lat, lng = opts['lat'], opts['lng']
        for dlat, dlng, level, cat, night, label, note, radius in SPOTS:
            Hotspot.objects.create(lat=lat + dlat, lng=lng + dlng, level=level, category=cat, night=night,
                                   label=label, note=note, radius=radius, is_demo=True)
        for name, amount in DONATIONS:
            Donation.objects.create(reference=new_reference('LA-DEMO'), amount=amount, display_name=name,
                                    last4='0000', status='sandbox', is_demo=True)
        for cause, amount in ALLOCATIONS:
            FundAllocation.objects.create(cause=cause, amount=amount, is_demo=True)
        self.stdout.write(self.style.SUCCESS(f'Seeded demo data around {lat:.4f}, {lng:.4f}.'))
