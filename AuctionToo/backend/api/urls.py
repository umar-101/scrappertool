from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoopNetPropertyViewSet, MarketPlacePropertyViewSet, OtherSourcePropertyViewSet

router = DefaultRouter()
router.register(r'loopnet', LoopNetPropertyViewSet)
router.register(r'marketplace', MarketPlacePropertyViewSet)
router.register(r'other', OtherSourcePropertyViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
