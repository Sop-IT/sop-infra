from netbox.api.routers import NetBoxRouter

from .views import *


router = NetBoxRouter()

router.register('infrastructures', SopInfraViewSet)
router.register('endpoints', PrismaEndpointViewSet)
router.register('access-locations', PrismaAccessLocationViewSet)
router.register('computed-access-locations', PrismaComputedAccessLocationViewSet)

urlpatterns = router.urls

