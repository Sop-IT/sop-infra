from netbox.api.routers import NetBoxRouter

from .views import *

router = NetBoxRouter()

router.register("infrastructures", SopInfraViewSet)
router.register("prisma-endpoints", PrismaEndpointViewSet)
router.register("prisma-access-locations", PrismaAccessLocationViewSet)
router.register("prisma-computed-access-locations", PrismaComputedAccessLocationViewSet)

router.register("sopmerakidash", SopMerakiDashViewSet)
router.register("sopmerakiorg", SopMerakiOrgViewSet)
router.register("sopmerakinet", SopMerakiNetViewSet)
router.register("sopmerakidevice", SopMerakiDeviceViewSet)
router.register("sopmerakiswitchstack", SopMerakiSwitchStackViewSet)

router.register("sopdevicesetting", SopDeviceSettingViewSet)
router.register("sopswitchtemplate", SopSwitchTemplateViewSet)


urlpatterns = router.urls
