from netbox.api.routers import NetBoxRouter

from .views import *


router = NetBoxRouter()

router.register("infrastructures", SopInfraViewSet)
router.register("prisma-endpoints", PrismaEndpointViewSet)
router.register("prisma-access-locations", PrismaAccessLocationViewSet)
router.register("prisma-computed-access-locations", PrismaComputedAccessLocationViewSet)

urlpatterns = router.urls
