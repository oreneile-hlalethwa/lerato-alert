import re

from rest_framework import serializers

SA_PHONE = re.compile(r'^(\+27|27|0)\d{9}$')


def clean_phone(value):
    phone = re.sub(r'[\s\-()]', '', value or '')
    if not SA_PHONE.match(phone):
        raise serializers.ValidationError('Enter a valid South African number.')
    return phone


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60, trim_whitespace=True)
    surname = serializers.CharField(max_length=60, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(min_length=8, max_length=128, trim_whitespace=False, write_only=True)

    def validate_phone(self, v):
        return clean_phone(v)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    channel = serializers.ChoiceField(choices=['number', 'email', 'whatsapp'])
    value = serializers.CharField(max_length=120)
    type = serializers.ChoiceField(choices=['kin', 'security', 'org'])

    def validate(self, data):
        if data['channel'] == 'email':
            serializers.EmailField().run_validation(data['value'])
        else:
            data['value'] = clean_phone(data['value'])
        return data


class LocationSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    accuracy = serializers.IntegerField(required=False, allow_null=True, min_value=0)


class AlertSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=['jogging', 'commute', 'home'])
    reason = serializers.CharField(max_length=120)
    location = LocationSerializer(required=False, allow_null=True)
    contacts = ContactSerializer(many=True)

    def validate_contacts(self, value):
        if len(value) > 5:
            raise serializers.ValidationError('At most 5 contacts per alert.')
        return value


class ReportSerializer(serializers.Serializer):
    kind = serializers.CharField(max_length=60)
    area = serializers.CharField(max_length=80, required=False, allow_blank=True)
    evidence_count = serializers.IntegerField(min_value=0, max_value=1000, default=0)


class MessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'assistant'])
    content = serializers.CharField(max_length=4000, allow_blank=True)


class ChatSerializer(serializers.Serializer):
    messages = MessageSerializer(many=True)
    turn = serializers.IntegerField(min_value=0, max_value=50, required=False, default=0)
    max_turns = serializers.IntegerField(min_value=1, max_value=10, required=False, allow_null=True)

    def validate_messages(self, value):
        if not value or len(value) > 40:
            raise serializers.ValidationError('Send between 1 and 40 messages.')
        return value


class TopicSerializer(serializers.Serializer):
    topic = serializers.CharField(min_length=3, max_length=80)
    id = serializers.CharField(max_length=40, required=False, allow_null=True, allow_blank=True)


class FundApplySerializer(serializers.Serializer):
    needs = serializers.ListField(
        child=serializers.ChoiceField(choices=['Transport', 'Shelter', 'Essentials', 'Legal']),
        min_length=1, max_length=4,
    )
    amount = serializers.IntegerField(min_value=50, max_value=5000)
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, v):
        return clean_phone(v)


class DonateSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=10, max_value=100000)
    last4 = serializers.RegexField(r'^\d{4}$')
    bank = serializers.CharField(max_length=20, required=False, default='FNB')
    display_name = serializers.CharField(max_length=60, required=False, allow_blank=True)


class VaultItemSerializer(serializers.Serializer):
    client_id = serializers.RegexField(r'^[A-Za-z0-9\-_.]{1,64}$')
    kind = serializers.ChoiceField(choices=['audio', 'photo', 'video', 'note'])
    title = serializers.CharField(max_length=80)
    text = serializers.CharField(max_length=10000, required=False, allow_blank=True)
    created = serializers.DateTimeField()


class LockSerializer(serializers.Serializer):
    """A salted PBKDF2 hash made on the phone. The plain secret never reaches the server."""
    salt = serializers.RegexField(r'^[0-9a-f]{16,64}$')
    hash = serializers.RegexField(r'^[0-9a-f]{64}$')
    iter = serializers.IntegerField(min_value=100000, max_value=1000000)


class SettingsSerializer(serializers.Serializer):
    safe_word = serializers.CharField(max_length=40, allow_blank=True, required=False)
    disguise_type = serializers.ChoiceField(choices=['calculator', 'messages', 'browser'], required=False)
    secret_lock = LockSerializer(required=False)
    vault_pin = LockSerializer(required=False)