from rest_framework import viewsets
from .models import LoopNetProperty, MarketPlaceProperty, OtherSourceProperty
from .serializers import (
    LoopNetPropertySerializer,
    MarketPlacePropertySerializer,
    OtherSourcePropertySerializer,
)


class LoopNetPropertyViewSet(viewsets.ModelViewSet):
    queryset = LoopNetProperty.objects.all()
    serializer_class = LoopNetPropertySerializer


class MarketPlacePropertyViewSet(viewsets.ModelViewSet):
    queryset = MarketPlaceProperty.objects.all()
    serializer_class = MarketPlacePropertySerializer


class OtherSourcePropertyViewSet(viewsets.ModelViewSet):
    queryset = OtherSourceProperty.objects.all()
    serializer_class = OtherSourcePropertySerializer
