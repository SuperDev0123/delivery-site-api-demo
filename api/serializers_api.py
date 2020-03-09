from rest_framework import serializers
from .models import BOK_0_BookingKeys, BOK_1_headers, BOK_2_lines, BOK_3_lines_data, DME_Files


class BOK_0_Serializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_0_BookingKeys
        fields = "__all__"


class BOK_1_Serializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_1_headers
        fields = "__all__"


class BOK_2_Serializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_2_lines
        fields = "__all__"


class BOK_3_Serializer(serializers.ModelSerializer):
    class Meta:
        model = BOK_3_lines_data
        fields = "__all__"

class DME_Files_Serializer(serializers.ModelSerializer):
    class Meta:
        model = DME_Files
        fields = "__all__"
