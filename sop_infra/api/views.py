from netbox.api.viewsets import NetBoxModelViewSet
from netbox.api.metadata import ContentTypeMetadata

from sop_infra.models import *
from sop_infra.filtersets import SopInfraFilterset
from sop_infra.api.serializers import *


__all__ = (
    'SopInfraViewSet',
    'PrismaEndpointViewSet',
    'PrismaAccessLocationViewSet',
    'PrismaComputedAccessLocationViewSet',
)


class PrismaEndpointViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = PrismaEndpoint.objects.all()
    serializer_class = PrismaEndpointSerializer



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

