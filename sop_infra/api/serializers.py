from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from timezone_field.rest_framework import TimeZoneSerializerField

from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer
from dcim.api.serializers import SiteSerializer, LocationSerializer

from sop_infra.models import *
from sop_infra.models.sopmeraki import SopMerakiSwitchStack


class PrismaEndpointSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:prismaendpoint-detail"
    )
    # access_location = serializers.SerializerMethodField()

    class Meta:
        model = PrismaEndpoint
        fields = (
            "id",
            "url",
            "display",
            "name",
            "slug",
            "prisma_org_id",
            "psk",
            "local_id",
            "remote_id",
            "peer_ip",
        )
        brief_fields = (
            "id",
            "url",
            "display",
            "name",
            "slug",
            "prisma_org_id",
            "psk",
            "local_id",
            "remote_id",
            "peer_ip",
        )

    # def get_access_location(self, obj):
    #     if obj.access_location is None:
    #         return None
    #     return PrismaAccessLocationSerializer(
    #         obj.access_location, nested=True, many=False, context=self.context
    #     ).data


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
            "isilog_code",
            "ad_direct_users_wc",
            "ad_direct_users_bc",
            "ad_direct_users_ext",
            "ad_direct_users_nom",
            "est_cumulative_users_wc",
            "est_cumulative_users_bc",
            "est_cumulative_users_ext",
            "est_cumulative_users_nom",
            "wan_reco_bw",
            "wan_computed_users_wc",
            "wan_computed_users_bc",
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
            "isilog_code",
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


class SopMerakiDashSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:sopmerakidash-detail"
    )
    orgs_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SopMerakiDash
        fields = (
            "id",
            "display",
            "nom",
            "url", 
            "description",
            "api_url",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "orgs_count",
        )


class SopMerakiOrgSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:sopmerakiorg-detail"
    )
    nets_count = serializers.IntegerField(read_only=True)
    devs_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SopMerakiOrg
        fields = (
            "id",
            "display",
            "url",
            "nom",
            "dash",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "nets_count",
            "devs_count",
        )


class SopMerakiNetSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:sopmerakinet-detail"
    )
    devs_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = SopMerakiNet
        fields = (
            "id",
            "display",
            "url",
            "nom",
            "site",
            "org",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "devs_count"
        )


class SopMerakiSwitchStackSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:sopmerakiswitchstack-detail"
    )

    class Meta:
        model = SopMerakiSwitchStack
        fields = (
            "id",
            "display",
            "url",
            "meraki_id",
            "nom",
            "net",
            "serials",
            "members",
        )
        brief_fields = ("id", "display", "url")


class SopMerakiDeviceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:sopmerakidevice-detail"
    )

    class Meta:
        model = SopMerakiDevice
        fields = (
            "id",
            "display",
            "url",
            "serial",
            "org",
            "org_id",
            "model_name",
            "meraki_netid",
            "firmware",
            "meraki_details",
            "meraki_notes",
            "ptype",
            "meraki_tags",
            "site",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        )


class SopSwitchTemplateSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:sopswitchtemplate-detail"
    )

    class Meta:
        model = SopSwitchTemplate
        fields = (
            "id",
            "display",
            "url",
            "nom",
            "stp_prio",
        )
        brief_fields = (
            "id",
            "display",
            "url",
            "nom",
            "stp_prio",
        )


class SopDeviceSettingSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:sop_infra-api:sopdevicesetting-detail"
    )

    class Meta:
        model = SopDeviceSetting
        fields = (
            "id",
            "display",
            "url",
            "device",
            "switch_template",
        )
