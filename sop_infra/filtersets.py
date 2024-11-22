import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from ipam.models import Prefix
from dcim.choices import SiteStatusChoices
from netbox.filtersets import NetBoxModelFilterSet
from dcim.models import Site, Region, SiteGroup, Location
from utilities.filters import TreeNodeMultipleChoiceFilter, MultiValueCharFilter

from .models import (
    SopInfra,
    PrismaEndpoint, PrismaAccessLocation, PrismaComputedAccessLocation
)


__all__ = (
    'SopInfraFilterset',
    'PrismaEndpointFilterset',
    'PrismaAccessLocationFilterset',
    'PrismaComputedAccessLocationFilterset'
)


class PrismaComputedAccessLocationFilterset(NetBoxModelFilterSet):

    class Meta:
        model = PrismaComputedAccessLocation
        fields = ('name', 'slug',
                  'strata_id', 'strata_name',
                  'bandwidth',)

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.objects.filter(
            Q(name__icontains=value) |
            Q(slug__icontains=value) |
            Q(strata_id__icontains=value) |
            Q(strata_name__icontains=value) |
            Q(bandwidth__icontains=value)
        )



class PrismaAccessLocationFilterset(NetBoxModelFilterSet):

    time_zone = MultiValueCharFilter()
    compute_location = django_filters.ModelMultipleChoiceFilter(
        queryset=PrismaComputedAccessLocation.objects.all(),
        field_name='compute_location'
    )

    class Meta:
        model = PrismaAccessLocation
        fields = ('name', 'slug',
                  'physical_address', 'time_zone', 'latitude', 'longitude',
                  'compute_location')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(slug__icontains=value) |
            Q(physical_address__icontains=value) |
            Q(time_zone__icontains=value) |
            Q(latitude__icontains=value) |
            Q(longitude__icontains=value) |
            Q(compute_location__name__icontains=value)
        )



class PrismaEndpointFilterset(NetBoxModelFilterSet):

    ip_address = django_filters.ModelMultipleChoiceFilter(
        queryset=Prefix.objects.all(),
        field_name='ip_address'
    )
    access_location = django_filters.ModelMultipleChoiceFilter(
        queryset=PrismaAccessLocation.objects.all(),
        field_name='access_location'
    )

    class Meta:
        model = PrismaEndpoint
        fields = ('id', 'name', 'slug',
                  'ip_address', 'access_location',)

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(slug__icontains=value) |
            Q(ip_address__icontains=value) |
            Q(access_location__name__icontains=value)
        )


#________
# SopInfra


class SopInfraFilterset(NetBoxModelFilterSet):
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        field_name='site'
    )
    site_name = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        field_name='site__name',
    )
    status = django_filters.MultipleChoiceFilter(
        choices=SiteStatusChoices,
        field_name='site__status',
    )
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name='site__region',
        lookup_expr='in'
    )
    group_id = TreeNodeMultipleChoiceFilter(
        queryset=SiteGroup.objects.all(),
        field_name='site__group',
        lookup_expr='in'
    )

    class Meta:
        model = SopInfra
        fields = ('id', 'site', 'site_id', 'site_name', 'status', 
                  'site_infra_sysinfra', 'site_type_indus',
                  'criticity_stars', 'site_phone_critical',
                  'site_type_red', 'site_type_vip', 'site_type_wms', 
                  'est_cumulative_users', 'site_user_count', 'wan_reco_bw',
                  'site_mx_model', 'wan_computed_users', 'ad_direct_users',
                  'sdwanha', 'hub_order_setting', 'hub_default_route_setting',
                  'sdwan1_bw', 'sdwan2_bw', 'site_sdwan_master_location',
                  'master_site', 'migration_sdwan',
                  'endpoint', 'enabled', 'valid')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(site__name__icontains=value) |
            Q(site__status__icontains=value) |
            Q(site_infra_sysinfra__icontains=value) |
            Q(site_type_indus__icontains=value) |
            Q(criticity_stars__icontains=value) |
            Q(est_cumulative_users__icontains=value) |
            Q(site_user_count__icontains=value) |
            Q(wan_reco_bw__icontains=value) |
            Q(site_mx_model__icontains=value) |
            Q(wan_computed_users__icontains=value) |
            Q(ad_direct_users__icontains=value) |
            Q(sdwanha__icontains=value) |
            Q(hub_order_setting__icontains=value) |
            Q(hub_default_route_setting__icontains=value) |
            Q(sdwan1_bw__icontains=value) |
            Q(sdwan2_bw__icontains=value) |
            Q(site_sdwan_master_location__name__icontains=value) |
            Q(master_site__name__icontains=value) |
            Q(migration_sdwan__icontains=value) |
            Q(endpoint__name__icontains=value) |
            Q(enabled__icontains=value) |
            Q(valid__icontains=value)
        )

