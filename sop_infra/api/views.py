from django.db.models import Count

from netbox.api.viewsets import NetBoxModelViewSet
from netbox.api.metadata import ContentTypeMetadata

from sop_infra.models import *
from sop_infra.filtersets import (
    SopInfraFilterset,
    PrismaEndpointFilterset,
    SopMerakiDashFilterSet,
    SopMerakiDeviceFilterSet,
    SopMerakiNetFilterSet,
    SopMerakiOrgFilterSet,
)
from sop_infra.api.serializers import *


__all__ = (
    "SopInfraViewSet",
    "PrismaEndpointViewSet",
    "PrismaAccessLocationViewSet",
    "PrismaComputedAccessLocationViewSet",
    "SopMerakiDashViewSet",
    "SopMerakiOrgViewSet",
    "SopMerakiNetViewSet",
    "SopMerakiDeviceViewSet",
)


class PrismaEndpointViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = PrismaEndpoint.objects.all()
    serializer_class = PrismaEndpointSerializer
    filterset_class = PrismaEndpointFilterset


class PrismaAccessLocationViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = PrismaAccessLocation.objects.all()
    serializer_class = PrismaAccessLocationSerializer


class PrismaComputedAccessLocationViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = PrismaComputedAccessLocation.objects.all()
    serializer_class = PrismaComputedAccessLocationSerializer


class SopInfraViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = SopInfra.objects.all()
    serializer_class = SopInfraSerializer
    filterset_class = SopInfraFilterset


class SopMerakiDashViewSet(NetBoxModelViewSet):
    queryset = SopMerakiDash.objects.prefetch_related("tags").annotate(
        orgs_count=Count("orgs")
    )
    serializer_class = SopMerakiDashSerializer
    filterset_class = SopMerakiDashFilterSet


class SopMerakiOrgViewSet(NetBoxModelViewSet):
    queryset = SopMerakiOrg.objects.annotate(
        nets_count=Count("nets", distinct=True)
    ).annotate(devices_count=Count("devices", distinct=True))
    serializer_class = SopMerakiOrgSerializer
    filterset_class = SopMerakiOrgFilterSet


class SopMerakiNetViewSet(NetBoxModelViewSet):
    queryset = SopMerakiNet.objects.all()
    serializer_class = SopMerakiNetSerializer
    filterset_class = SopMerakiNetFilterSet


class SopMerakiDeviceViewSet(NetBoxModelViewSet):
    queryset = SopMerakiDevice.objects.all()
    serializer_class = SopMerakiDeviceSerializer
    filterset_class = SopMerakiDeviceFilterSet
