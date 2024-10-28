from netbox.api.routers import NetBoxRouter

from .views import SopInfraViewSet


router = NetBoxRouter()

router.register('infrastructures', SopInfraViewSet)

urlpatterns = router.urls

