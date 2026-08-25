from django.forms.fields import MultipleChoiceField
import django_filters
from django.db import models
from django.db.models import Q, F, IntegerField

from dcim.models.devices import DeviceType
from utilities.filters import TreeNodeMultipleChoiceFilter, MultiValueCharFilter

from netbox.filtersets import NetBoxModelFilterSet
from utilities.filtersets import register_filterset

from ipam.models import Prefix
from dcim.choices import SiteStatusChoices
from dcim.models import Site, Region, SiteGroup

from sop_infra.models import *


# ==========================================================================
# SOPMERAKI


@register_filterset
class SopMerakiDashFilterSet(NetBoxModelFilterSet):

    class Meta:
        model = SopMerakiDash
        fields = (
            "id",
            "api_url",
            "description",
            "nom",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(nom__icontains=value) | Q(description__icontains=value)
        )


@register_filterset
class SopMerakiOrgFilterSet(NetBoxModelFilterSet):

    class Meta:
        model = SopMerakiOrg
        fields = (
            "id",
            "dash",
            "dash_id",
            "nom",
            "meraki_id",
            "meraki_url",
            "syslog_servers",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(nom__icontains=value)
            | Q(meraki_url__icontains=value)
            | Q(meraki_id__icontains=value)
        )


@register_filterset
class SopMerakiNetFilterSet(NetBoxModelFilterSet):

    supports_ptype = django_filters.CharFilter(method="filter_custom")
    has_meraki_tag = django_filters.CharFilter(method="filter_custom")

    def filter_custom(self, queryset, name, value):
        print(f"filter_custom {queryset=} {name=} {value=}")
        if value is None:
            return queryset
        q: Q
        if name == "supports_ptype":
            q = Q(ptypes__icontains=value)
            print(f"{q=}")
            return queryset.filter(q)
        if name == "has_meraki_tag":
            q = Q(meraki_tags__icontains=value)
            return queryset.filter(q)
        raise Exception(f"unknown field name {name}")

 
    class Meta:
        model = SopMerakiNet
        fields = (
            "id",
            "site",
            "site_id",
            "org",
            "org_id",
            "nom",
            "meraki_id",
            "bound_to_template",
            "meraki_url",
            "meraki_notes",
            "ptypes",
            "meraki_tags",
            "org__dash",
            "org__dash_id",
            "vpn_mode",
            "appliance_status",
            "meraki_peers_reachability",
            "exp_subnets_count",
            "last_stats_change",
            "primary_mx",
            "secondary_mx",
        )
        filter_overrides = {
            models.JSONField: {
                "filter_class": django_filters.CharFilter,
                "extra": lambda f: {
                    "lookup_expr": "icontains",
                },
            }
        }


    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(nom__icontains=value)
            | Q(meraki_id__icontains=value)
            | Q(meraki_tags__icontains=value)
        )


@register_filterset
class SopMerakiSwitchStackFilterSet(NetBoxModelFilterSet):

    class Meta:
        model = SopMerakiSwitchStack
        fields = (
            "id",
            "nom",
            "meraki_id",
            "net",
            "net_id",
            "site",
            "site_id",
        )
        filter_overrides = {
            models.JSONField: {
                "filter_class": django_filters.CharFilter,
                "extra": lambda f: {
                    "lookup_expr": "icontains",
                },
            }
        }

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(nom__icontains=value) | Q(meraki_id__icontains=value))

# from django.forms.fields import MultipleChoiceField

# class MultipleValueField(MultipleChoiceField):
#     def __init__(self, *args, field_class, **kwargs):
#         self.inner_field = field_class()
#         super().__init__(*args, **kwargs)

#     def valid_value(self, value):
#         return self.inner_field.validate(value)

#     def clean(self, values):
#         return values and [self.inner_field.clean(value, None) for value in values]
    
# from django_filters.filters import Filter

# class MultipleValueFilter(Filter):

#     field_class = MultipleValueField

#     def __init__(self, *args, **kwargs):
#         kwargs.setdefault('lookup_expr', 'in')
#         super().__init__(*args, field_class=IntegerField, **kwargs)

#     def filter(self, qs, values):
#         raise NotImplementedError(_('{class_name} must implement filter(self, qs, values)').format(
#             class_name=self.__class__.__name__
#         ))
    
# from django.db.models.functions import Lower

# class NetboxDeviceTypeFilter(MultipleValueFilter):
    
#     def filter(self, qs, values):
#         if values is None or len(values)==0:
#             return qs
#         dts=DeviceType.objects.filter(manufacturer__slug__exact="cisco").filter(pk__in=values).values_list("slug", flat=True)
#         # slug=f"cisco-{self.model_name}".lower()
#         shorts:list[str]=list()
#         for sl in dts:
#             shorts.append(sl[6:].lower())
#         #print(f"netbox_dev_type {self=} {dts=} {values=} {shorts=} ")
#         return qs.annotate(lower_model=Lower('model_name')).filter(lower_model__in=shorts)
    
@register_filterset
class SopMerakiDeviceFilterSet(NetBoxModelFilterSet):

    has_netbox_device = django_filters.BooleanFilter(method="filter_custom")
    has_netbox_device_in_same_site = django_filters.BooleanFilter(
        method="filter_custom"
    )
    has_netbox_device_of_same_type = django_filters.BooleanFilter(
        method="filter_custom"
    )
    meraki_network=django_filters.CharFilter(method="filter_custom")
    ptype=django_filters.CharFilter(method="filter_custom")
    has_compliant_management_dns = django_filters.BooleanFilter(
        method="filter_custom"
    )

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     custom_field_filters = {}
    #     filter_name = f'netbox_device_type'
    #     custom_field_filters[filter_name] = NetboxDeviceTypeFilter(field_name=filter_name)
    #     self.filters.update(custom_field_filters)


    def filter_custom(self, queryset, name, value):
        if value is None:
            return queryset
        q: Q
        if name == "has_netbox_device":
            q = Q(netbox_device_id=None)
            if value:
                return queryset.exclude(q)
            return queryset.filter(q)
        if name == "has_netbox_device_in_same_site":
            q = Q(netbox_device__site=F("site"))
            if value:
                return queryset.filter(q)
            return queryset.exclude(q)
        if name == "has_netbox_device_of_same_type":
            q = Q(netbox_device__device_type__part_number=F("model_name"))
            if value:
                return queryset.filter(q)
            return queryset.exclude(q)
        if name == "meraki_network":
            #print(f"merakicsustom {value}")
            q = Q(meraki_network__id=value)
            return queryset.filter(q)
        if name == "ptype":
            print(f"ptype {value}")
            q = Q(ptype__iexact=value)
            return queryset.filter(q)
        if name == "has_compliant_management_dns":
            # TODO CHINE AND WAN2
            qw1:Q = Q(Q(wan1__staticDns__isnull=True) | Q(wan1__staticDns=["8.8.8.8","8.8.4.4"]))
            qw2:Q = Q(Q(wan2__staticDns__isnull=True) | Q(wan2__staticDns=["8.8.8.8","8.8.4.4"]))
            q:Q=qw1 | qw2
            if value:
                return queryset.filter(q)
            return queryset.exclude(q)
        
        raise Exception("unknown field name")
        

    class Meta:
        model = SopMerakiDevice
        fields = (
            "id",
            "nom",
            "serial",
            "model_name",
            "mac",
            "meraki_netid",
            "meraki_notes",
            "ptype",
            "meraki_tags",
            "meraki_details",
            "meraki_url",
            "firmware",
            "site",
            "site_id",
            "org",
            "org_id",
            "stack",
            "stack_id",
            "org__dash",
            "org__dash_id",
            "netbox_device",
            "netbox_device_id",
            "lan_ip",
            "cfg_updated_at",
            "latitude",
            "longitude",
            "wan1ip",
            "wan2ip",
            "wan1status",
            "wan2status",
            "last_reported_at",
            "sku",
            "claimed_at", 
            "license_expiration_at",
            "country_code",
            "eox_status",
            "eox_end_of_sale",
            "eox_end_of_support",
        )
        filter_overrides = {
            models.JSONField: {
                "filter_class": django_filters.CharFilter,
                "extra": lambda f: {
                    "lookup_expr": "icontains",
                },
            }
        }

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(nom__icontains=value)
            | Q(serial__icontains=value)
            | Q(firmware__icontains=value)
            | Q(meraki_notes__icontains=value)
        )


# ==========================================================================
# PRISMA


@register_filterset
class PrismaComputedAccessLocationFilterset(NetBoxModelFilterSet):

    class Meta:
        model = PrismaComputedAccessLocation
        fields = (
            "name",
            "slug",
            "strata_id",
            "strata_name",
            "bandwidth",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.objects.filter(
            Q(name__icontains=value)
            | Q(slug__icontains=value)
            | Q(strata_id__icontains=value)
            | Q(strata_name__icontains=value)
            | Q(bandwidth__icontains=value)
        )


@register_filterset
class PrismaAccessLocationFilterset(NetBoxModelFilterSet):

    time_zone = MultiValueCharFilter()
    compute_location = django_filters.ModelMultipleChoiceFilter(
        queryset=PrismaComputedAccessLocation.objects.all(),
        field_name="compute_location",
    )

    class Meta:
        model = PrismaAccessLocation
        fields = (
            "name",
            "slug",
            "physical_address",
            "time_zone",
            "latitude",
            "longitude",
            "compute_location",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(slug__icontains=value)
            | Q(physical_address__icontains=value)
            | Q(time_zone__icontains=value)
            | Q(latitude__icontains=value)
            | Q(longitude__icontains=value)
            | Q(compute_location__name__icontains=value)
        )


@register_filterset
class PrismaEndpointFilterset(NetBoxModelFilterSet):

    ip_address = django_filters.ModelMultipleChoiceFilter(
        queryset=Prefix.objects.all(), field_name="ip_address"
    )
    access_location = django_filters.ModelMultipleChoiceFilter(
        queryset=PrismaAccessLocation.objects.all(), field_name="access_location"
    )

    class Meta:
        model = PrismaEndpoint
        fields = (
            "id",
            "name",
            "slug",
            "ip_address",
            "access_location",
            "prisma_org_id",
            "psk",
            "local_id",
            "remote_id",
            "peer_ip",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(slug__icontains=value)
            | Q(local_id__icontains=value)
            | Q(remote_id__icontains=value)
            | Q(peer_ip__icontains=value)
        )


# ==========================================================================
# SopInfra


@register_filterset
class SopInfraFilterset(NetBoxModelFilterSet):
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(), field_name="site"
    )
    site_name = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        field_name="site__name",
    )
    status = django_filters.MultipleChoiceFilter(
        choices=SiteStatusChoices,
        field_name="site__status",
    )
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(), field_name="site__region", lookup_expr="in"
    )
    group_id = TreeNodeMultipleChoiceFilter(
        queryset=SiteGroup.objects.all(), field_name="site__group", lookup_expr="in"
    )

    class Meta:
        model = SopInfra
        fields = (
            "id",
            "site",
            "site_id",
            "site_name",
            "status",
            "master_site_id",
            "site_infra_sysinfra",
            "site_type_indus",
            "criticality_stars",
            "site_phone_critical",
            "site_type_red",
            "site_type_vip",
            "site_type_wms",
            "est_cumulative_users_wc",
            "est_cumulative_users_bc",
            "est_cumulative_users_ext",
            "est_cumulative_users_nom",
            "site_user_count",
            "wan_reco_bw",
            "site_mx_model",
            "wan_computed_users_wc",
            "wan_computed_users_bc",
            "ad_direct_users_wc",
            "ad_direct_users_bc",
            "ad_direct_users_ext",
            "ad_direct_users_nom",
            "sdwanha",
            "hub_order_setting",
            "hub_default_route_setting",
            "sdwan1_bw",
            "sdwan2_bw",
            "site_sdwan_master_location",
            "master_site",
            "migration_sdwan",
            "endpoint",
            "endpoint_id",
            "enabled",
            "valid",
            "syslog_servers",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(site__name__icontains=value)
            | Q(site__status__icontains=value)
            | Q(site_infra_sysinfra__icontains=value)
            | Q(site_type_indus__icontains=value)
            | Q(criticality_stars__icontains=value)
            | Q(est_cumulative_users_wc__icontains=value)
            | Q(est_cumulative_users_bc__icontains=value)
            | Q(est_cumulative_users_ext__icontains=value)
            | Q(est_cumulative_users_nom__icontains=value)
            | Q(site_user_count__icontains=value)
            | Q(wan_reco_bw__icontains=value)
            | Q(site_mx_model__icontains=value)
            | Q(wan_computed_users_wc__icontains=value)
            | Q(wan_computed_users_bc__icontains=value)
            | Q(ad_direct_users_wc__icontains=value)
            | Q(ad_direct_users_bc__icontains=value)
            | Q(ad_direct_users_ext__icontains=value)
            | Q(ad_direct_users_nom__icontains=value)
            | Q(sdwanha__icontains=value)
            | Q(hub_order_setting__icontains=value)
            | Q(hub_default_route_setting__icontains=value)
            | Q(sdwan1_bw__icontains=value)
            | Q(sdwan2_bw__icontains=value)
            | Q(site_sdwan_master_location__name__icontains=value)
            | Q(master_site__name__icontains=value)
            | Q(endpoint__name__icontains=value)
            | Q(enabled__icontains=value)
            | Q(valid__icontains=value)
        )


@register_filterset
class SopSwitchTemplateFilterset(NetBoxModelFilterSet):

    class Meta:
        model = SopSwitchTemplate
        fields = (
            "id",
            "nom",
            "stp_prio",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(nom__icontains=value) | Q(stp_prio__icontains=value))



@register_filterset
class SopDeviceSettingFilterset(NetBoxModelFilterSet):

    class Meta:
        model = SopDeviceSetting
        fields = (
            "id",
            "device",
            "switch_template",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(device__icontains=value) | Q(switch_template__icontains=value)
        )



@register_filterset
class SopSyslogServerFilterset(NetBoxModelFilterSet):

    class Meta:
        model = SopSyslogServer
        fields = (
            "id",
            "nom",
            "server_address",
            "server_port",
            "enabled",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(nom__icontains=value) | Q(server_address__icontains=value) | Q(server_port__icontains=value))