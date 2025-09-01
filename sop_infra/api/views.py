from django.db.models import Count

from netbox.api.viewsets import NetBoxModelViewSet
from netbox.api.metadata import ContentTypeMetadata

from sop_infra.api.serializers import SopDeviceSettingSerializer
from sop_infra.models import *
from sop_infra.filtersets import *
from sop_infra.api.serializers import *


__all__ = (
    "SopInfraViewSet",
    "PrismaEndpointViewSet",
    "PrismaAccessLocationViewSet",
    "PrismaComputedAccessLocationViewSet",
    "SopMerakiDashViewSet",
    "SopMerakiOrgViewSet",
    "SopMerakiNetViewSet",
    "SopMerakiSwitchStackViewSet",
    "SopMerakiDeviceViewSet",
    "SopSwitchTemplateViewSet",
    "SopDeviceSettingViewSet",
)


class PrismaEndpointViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = PrismaEndpoint.objects.all().order_by("pk")
    serializer_class = PrismaEndpointSerializer
    filterset_class = PrismaEndpointFilterset


class PrismaAccessLocationViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = PrismaAccessLocation.objects.all().order_by("pk")
    serializer_class = PrismaAccessLocationSerializer


class PrismaComputedAccessLocationViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = PrismaComputedAccessLocation.objects.all().order_by("pk")
    serializer_class = PrismaComputedAccessLocationSerializer


class SopInfraViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = SopInfra.objects.all().order_by("pk")
    serializer_class = SopInfraSerializer
    filterset_class = SopInfraFilterset


class SopMerakiDashViewSet(NetBoxModelViewSet):
    queryset = SopMerakiDash.objects.prefetch_related("tags")\
        .annotate(orgs_count=Count("orgs"))\
        .annotate(nets_count=Count("orgs__nets", distinct=True))\
        .annotate(devs_count=Count("orgs__devices", distinct=True)).order_by("pk")
    serializer_class = SopMerakiDashSerializer
    filterset_class = SopMerakiDashFilterSet


class SopMerakiOrgViewSet(NetBoxModelViewSet):
    queryset = SopMerakiOrg.objects\
        .annotate(nets_count=Count("nets", distinct=True))\
        .annotate(devs_count=Count("devices", distinct=True)).order_by("pk")
    serializer_class = SopMerakiOrgSerializer
    filterset_class = SopMerakiOrgFilterSet


class SopMerakiNetViewSet(NetBoxModelViewSet):
    queryset = SopMerakiNet.objects.all()\
        .annotate(devs_count=Count("devices", distinct=True)).order_by("pk")
    serializer_class = SopMerakiNetSerializer
    filterset_class = SopMerakiNetFilterSet


class SopMerakiSwitchStackViewSet(NetBoxModelViewSet):
    queryset = SopMerakiSwitchStack.objects.all().order_by("pk")
    serializer_class = SopMerakiSwitchStackSerializer
    filterset_class = SopMerakiSwitchStackFilterSet


class SopMerakiDeviceViewSet(NetBoxModelViewSet):
    queryset = SopMerakiDevice.objects.all().order_by("pk")
    serializer_class = SopMerakiDeviceSerializer
    filterset_class = SopMerakiDeviceFilterSet


class SopSwitchTemplateViewSet(NetBoxModelViewSet):
    queryset = SopSwitchTemplate.objects.all().order_by("pk")
    serializer_class = SopSwitchTemplateSerializer
    filterset_class = SopSwitchTemplateFilterset


class SopDeviceSettingViewSet(NetBoxModelViewSet):
    queryset = SopDeviceSetting.objects.all().order_by("pk")
    serializer_class = SopDeviceSettingSerializer
    filterset_class = SopDeviceSettingFilterset
