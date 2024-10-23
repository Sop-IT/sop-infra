from netbox.api.routers import NetBoxRouter

from .views import *


router = NetBoxRouter()

router.register('sop-infras', SopInfraViewSet)

urlpatterns = router.urls
