from django.db.models import Count

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
    'SopMerakiDashViewSet',
    'SopMerakiOrgViewSet',
    'SopMerakiNetViewSet',
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


class SopMerakiDashViewSet(NetBoxModelViewSet):
    queryset = SopMerakiDash.objects.prefetch_related('tags').annotate(
        orgs_count=Count('orgs')
    )
    serializer_class = SopMerakiDashSerializer


class SopMerakiOrgViewSet(NetBoxModelViewSet):
    queryset = SopMerakiOrg.objects.prefetch_related('tags').annotate(
        nets_count=Count('nets')
    )
    serializer_class = SopMerakiOrgSerializer


class SopMerakiNetViewSet(NetBoxModelViewSet):
    queryset = SopMerakiNet.objects.all()
    serializer_class = SopMerakiNetSerializer
