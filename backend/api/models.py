import secrets
import uuid

from django.db import models


def new_token():
    return secrets.token_urlsafe(32)


def new_reference(prefix):
    return f'{prefix}-{secrets.token_hex(3).upper()}'


class Member(models.Model):
    """A registered app user. Identified by a random token stored on their phone."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=60)
    surname = models.CharField(max_length=60)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    token = models.CharField(max_length=64, unique=True, default=new_token, editable=False)
    password = models.CharField(max_length=128, blank=True)  # Django hash, never the plain password
    # Safe word, disguise type, and salted PBKDF2 hashes of the secret sum and vault PIN (never the plain values).
    settings = models.JSONField(default=dict, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} {self.surname}'


class Contact(models.Model):
    CHANNELS = [('number', 'SMS'), ('email', 'Email'), ('whatsapp', 'WhatsApp')]
    TYPES = [('kin', 'Next of kin'), ('security', 'Security company'), ('org', 'Organisation')]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=60)
    channel = models.CharField(max_length=10, choices=CHANNELS)
    value = models.CharField(max_length=120)
    type = models.CharField(max_length=10, choices=TYPES)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.get_type_display()})'


class Alert(models.Model):
    MODES = [('jogging', 'Jogging'), ('commute', 'Commute'), ('home', 'At home')]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='alerts')
    mode = models.CharField(max_length=10, choices=MODES)
    reason = models.CharField(max_length=120)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    accuracy = models.IntegerField(null=True, blank=True)
    recipients = models.JSONField(default=list)     # who we tried to notify
    delivery = models.JSONField(default=list)       # per-recipient result
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'{self.member} · {self.reason} · {self.created:%Y-%m-%d %H:%M}'


class Report(models.Model):
    """Anonymous incident report: no member link on purpose."""
    reference = models.CharField(max_length=20, unique=True)
    kind = models.CharField(max_length=60)
    area = models.CharField(max_length=80, blank=True)
    evidence_count = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'{self.reference} · {self.kind}'


class LessonSuggestion(models.Model):
    topic = models.CharField(max_length=80)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.topic


class FundApplication(models.Model):
    STATUS = [('review', 'In review'), ('approved', 'Approved'), ('paid', 'Paid'), ('declined', 'Declined')]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='fund_applications')
    needs = models.JSONField(default=list)
    amount = models.PositiveIntegerField()
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS, default='review')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'R{self.amount} · {", ".join(self.needs)} · {self.get_status_display()}'


class Donation(models.Model):
    reference = models.CharField(max_length=24, unique=True)
    amount = models.PositiveIntegerField()
    display_name = models.CharField(max_length=60, default='Anonymous')
    bank = models.CharField(max_length=20, default='FNB')
    last4 = models.CharField(max_length=4)
    status = models.CharField(max_length=12, default='sandbox')
    is_demo = models.BooleanField(default=False, help_text='Seeded sample data, shown with a DEMO tag.')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'{self.reference} · R{self.amount} · {self.display_name}'


class FundAllocation(models.Model):
    """Money paid out from the fund, by cause only. Never names a survivor."""
    CAUSES = [
        ('Emergency transport', 'Emergency transport'),
        ('Safe shelter stays', 'Safe shelter stays'),
        ('Legal support', 'Legal support'),
        ('Food & essentials', 'Food & essentials'),
        ('Counselling', 'Counselling'),
    ]
    cause = models.CharField(max_length=40, choices=CAUSES)
    amount = models.PositiveIntegerField()
    is_demo = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.cause} · R{self.amount}'


class Hotspot(models.Model):
    LEVELS = [('clear', 'All clear'), ('aware', 'Stay aware'), ('heads', 'Heads up'), ('red', 'Red zone')]
    CATEGORIES = [('robbery', 'Robbery'), ('assault', 'Assault'), ('murder', 'Murder'), ('none', 'None')]
    label = models.CharField(max_length=80)
    note = models.CharField(max_length=120)
    lat = models.FloatField()
    lng = models.FloatField()
    radius = models.PositiveIntegerField(default=200, help_text='Metres')
    level = models.CharField(max_length=6, choices=LEVELS)
    category = models.CharField(max_length=10, choices=CATEGORIES, default='none')
    night = models.BooleanField(default=False, help_text='Mostly after dark')
    active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.label} ({self.get_level_display()})'


class VaultItem(models.Model):
    """Evidence backed up from a member's vault. Files live privately on Cloudinary."""
    KINDS = [('audio', 'Audio'), ('photo', 'Photo'), ('video', 'Video'), ('note', 'Note')]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='vault_items')
    client_id = models.CharField(max_length=64, help_text='ID of the item on the phone, to avoid duplicates')
    kind = models.CharField(max_length=5, choices=KINDS)
    title = models.CharField(max_length=80)
    text = models.TextField(blank=True)                  # notes only
    public_id = models.CharField(max_length=255, blank=True)
    resource_type = models.CharField(max_length=10, blank=True)
    format = models.CharField(max_length=10, blank=True)
    bytes = models.PositiveBigIntegerField(default=0)
    captured = models.DateTimeField(help_text='When it was recorded on the phone')
    uploaded = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-captured']
        constraints = [models.UniqueConstraint(fields=['member', 'client_id'], name='unique_vault_item_per_member')]

    def __str__(self):
        return f'{self.get_kind_display()} · {self.member} · {self.captured:%Y-%m-%d %H:%M}'