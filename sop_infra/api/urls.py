from netbox.api.routers import NetBoxRouter

from .views import *


router = NetBoxRouter()

router.register('classifications', InfraClassificationViewSet)
router.register('sizing', InfraSizingViewSet)
router.register('meraki_sdwan', InfraMerakiSDWANViewSet)

urlpatterns = router.urls
