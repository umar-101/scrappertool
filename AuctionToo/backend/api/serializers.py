from rest_framework import serializers
from .models import LoopNetProperty, MarketPlaceProperty, OtherSourceProperty


class LoopNetPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoopNetProperty
        fields = "__all__"


class MarketPlacePropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketPlaceProperty
        fields = "__all__"


class OtherSourcePropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherSourceProperty
        fields = "__all__"
