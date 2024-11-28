from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from timezone_field.rest_framework import TimeZoneSerializerField

from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer
from dcim.api.serializers import SiteSerializer, LocationSerializer

from sop_infra.models import *


__all__ = (
    "SopInfraSerializer",
    "PrismaEndpointSerializer",
    "PrismaAccessLocationSerializer",
    "PrismaComputedAccessLocationSerializer",
)


class PrismaEndpointSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:prismaendpoint-detail"
    )
    access_location = serializers.SerializerMethodField()

    class Meta:
        model = PrismaEndpoint
        fields = (
            "id",
            "url",
            "display",
            "name",
            "slug",
            "ip_address",
            "access_location",
        )
        brief_fields = (
            "id",
            "url",
            "display",
            "name",
            "slug",
            "ip_address",
            "access_location",
        )

    def get_access_location(self, obj):
        if obj.access_location is None:
            return None
        return PrismaAccessLocationSerializer(
            obj.access_location, nested=True, many=False, context=self.context
        ).data


class PrismaAccessLocationSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:prismaaccesslocation-detail"
    )
    time_zone = TimeZoneSerializerField(required=False, allow_null=True)
    compute_location = serializers.SerializerMethodField()

    class Meta:
        model = PrismaAccessLocation
        fields = (
            "id",
            "url",
            "display",
            "name",
            "slug",
            "physical_address",
            "time_zone",
            "latitude",
            "longitude",
            "compute_location",
        )
        brief_fields = ("id", "url", "display", "name", "slug", "compute_location")

    def get_compute_location(self, obj):
        if obj.compute_location is None:
            return None
        return PrismaComputedAccessLocationSerializer(
            obj.compute_location, nested=True, many=False, context=self.context
        ).data


class PrismaComputedAccessLocationSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:prismacomputedaccesslocation-detail"
    )

    class Meta:
        model = PrismaComputedAccessLocation
        fields = (
            "id",
            "url",
            "display",
            "name",
            "slug",
            "strata_id",
            "strata_name",
            "bandwidth",
        )
        brief_fields = (
            "id",
            "url",
            "display",
            "name",
            "slug",
            "bandwidth",
        )


class SopInfraSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:sopinfra-detail"
    )
    site = serializers.SerializerMethodField()
    sdwanha = ChoiceField(choices=InfraSdwanhaChoices)
    hub_order_setting = ChoiceField(InfraHubOrderChoices)
    site_sdwan_master_location = serializers.SerializerMethodField()
    master_site = serializers.SerializerMethodField()
    site_infra_sysinfra = ChoiceField(choices=InfraTypeChoices)
    site_type_indus = ChoiceField(choices=InfraTypeIndusChoices)
    endpoint = serializers.SerializerMethodField()
    enabled = ChoiceField(choices=InfraTypeIndusChoices)
    valid = ChoiceField(choices=InfraTypeIndusChoices)

    class Meta:
        model = SopInfra
        fields = (
            "id",
            "url",
            "display",
            "site",
            "endpoint",
            "enabled",
            "valid",
            "site_infra_sysinfra",
            "site_type_indus",
            "site_phone_critical",
            "site_type_red",
            "site_type_vip",
            "site_type_wms",
            "criticity_stars",
            "ad_direct_users",
            "est_cumulative_users",
            "wan_reco_bw",
            "wan_computed_users",
            "site_mx_model",
            "sdwanha",
            "hub_order_setting",
            "hub_default_route_setting",
            "sdwan1_bw",
            "sdwan2_bw",
            "site_sdwan_master_location",
            "master_site",
            "migration_sdwan",
            "monitor_in_starting",
            "endpoint",
            "enabled",
            "valid",
            "created",
            "last_updated",
        )
        brief_fields = (
            "id",
            "url",
            "display",
            "site_infra_sysinfra",
            "criticity_stars",
            "site_type_indus",
            "sdwanha",
            "site_sdwan_master_location",
            "master_site",
        )

    def get_site(self, obj):
        if not obj.site:
            return None
        return SiteSerializer(
            obj.site, nested=True, many=False, context=self.context
        ).data

    def get_site_sdwan_master_location(self, obj):
        if not obj.site_sdwan_master_location:
            return None
        return LocationSerializer(
            obj.site_sdwan_master_location,
            nested=True,
            many=False,
            context=self.context,
        ).data

    def get_master_site(self, obj):
        if not obj.master_site:
            return None
        return SiteSerializer(
            obj.master_site, nested=True, many=False, context=self.context
        ).data

    def get_endpoint(self, obj):
        if obj.endpoint is None:
            return None
        return PrismaEndpointSerializer(
            obj.endpoint, nested=True, many=False, context=self.context
        ).data
