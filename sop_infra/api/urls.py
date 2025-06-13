from netbox.api.routers import NetBoxRouter

from .views import *


router = NetBoxRouter()

router.register("infrastructures", SopInfraViewSet)
router.register("prisma-endpoints", PrismaEndpointViewSet)
router.register("prisma-access-locations", PrismaAccessLocationViewSet)
router.register("prisma-computed-access-locations", PrismaComputedAccessLocationViewSet)

router.register("merakidashs", SopMerakiDashViewSet)
router.register("merakiorgs", SopMerakiOrgViewSet)
router.register("merakinets", SopMerakiNetViewSet)
router.register("merakidevs", SopMerakiDeviceViewSet)

urlpatterns = router.urls
