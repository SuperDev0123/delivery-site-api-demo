from rest_framework import serializers
from .models import BOK_0_BookingKeys, BOK_1_headers, BOK_2_lines, BOK_3_lines_data


class BOK_0_BookingKeysSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_0_BookingKeys
        fields = "__all__"


class BOK_1_headersSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_1_headers
        fields = "__all__"


class BOK_2_linesSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_2_lines
        fields = "__all__"


class BOK_3_lines_dataSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_3_lines_data
        fields = "__all__"
