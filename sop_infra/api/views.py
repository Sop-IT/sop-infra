from netbox.api.viewsets import NetBoxModelViewSet
from netbox.api.metadata import ContentTypeMetadata

from ..models import *
from .serializers import *


__all__ = (
    'InfraClassificationViewSet',
    'InfraSizingViewSet',
    'InfraMerakiSDWANViewSet',
)


class InfraMerakiSDWANViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = InfraMerakiSDWAN.objects.all()
    serializer_class = InfraMerakiSDWANSerializer


class InfraSizingViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = InfraSizing.objects.all()
    serializer_class = InfraSizingSerializer


class InfraClassificationViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = InfraClassification.objects.all()
    serializer_class = InfraClassificationSerializer
