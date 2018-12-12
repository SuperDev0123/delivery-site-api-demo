from pages.models import BOK_0_BookingKeys, BOK_1_headers, BOK_2_lines
from rest_framework import serializers

class BOK_0_BookingKeysSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_0_BookingKeys
        fields = '__all__'

class BOK_1_headersSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_1_headers
        fields = '__all__'

class BOK_2_linesSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_2_lines
        fields = '__all__'