from netbox.api.viewsets import NetBoxModelViewSet
from netbox.api.metadata import ContentTypeMetadata

from ..models import SopInfra
from ..filtersets import SopInfraFilterset
from .serializers import SopInfraSerializer


__all__ = (
    'SopInfraViewSet',
)


class SopInfraViewSet(NetBoxModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = SopInfra.objects.all()
    serializer_class = SopInfraSerializer
    filterset_class = SopInfraFilterset

