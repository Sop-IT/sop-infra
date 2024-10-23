from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer
from dcim.api.serializers import SiteSerializer, LocationSerializer
from dcim.models import Site, Location

from ..models import *


__all__ = (
    'SopInfraSerializer',
)


class SopInfraSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:sop_infra-api:sopinfra-detail'
    )
    site = serializers.SerializerMethodField()

    class Meta:
        model = SopInfra
        fields = (
            'id', 'url', 'display', 'site', 'created',' last_updated'
        )

    def get_site(self, obj):
        if not obj.site:
            return None
        Site.objects.get(site=obj.site)
        return SiteSerializer(site, nested=True, many=False, context=self.context).data



