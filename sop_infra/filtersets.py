import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dcim.models import Site, Region, SiteGroup, Location
from netbox.filtersets import NetBoxModelFilterSet
from utilities.filters import TreeNodeMultipleChoiceFilter

from .models import SopInfra


__all__ = (
    'SopInfraFilterset',
)


class SopInfraFilterset(NetBoxModelFilterSet):
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        field_name='site__id'
    )
    site_name = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        field_name='site__name',
    )
    status = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
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
        fields = ('id', 'site', 'ad_cumulative_users', 'est_cumulative_users',
                  'wan_reco_bw', 'wan_computed_users')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(site__name__icontains=value) |
            Q(ad_cumulative_users__icontains=value) |
            Q(est_cumulative_users__icontains=value) |
            Q(wan_reco_bw__icontains=value) |
            Q(wan_computed_users__icontains=value)
        )

