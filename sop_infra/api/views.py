from netbox.api.viewsets import NetBoxModelViewSet
from netbox.api.metadata import ContentTypeMetadata

from ..models import *
from .serializers import *


__all__ = (
    'SopInfraViewSet',
)


class SopInfraViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = SopInfra.objects.all()
    serializer_class = SopInfraSerializer


