from django.db import models
import django_tables2 as tables
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, ChoiceFieldColumn
from dcim.models import Site
from dcim.choices import SiteStatusChoices

from .models import SopInfra


__all__ = (
    'SopInfraSizingTable',
    'SopInfraMerakiTable',
    'SopInfraClassificationTable'
)


class SopInfraMerakiTable(NetBoxTable):
    '''
    table for all SopInfra - meraki sdwan related instances
    '''
    site = tables.Column(linkify=True)
    status = tables.Column(accessor='site__status', linkify=True)
    sdwanha = tables.Column(linkify=True)
    hub_order_setting = tables.Column(linkify=True)
    hub_default_route_setting = ChoiceFieldColumn(linkify=True)
    sdwan1_bw = tables.Column(linkify=True)
    sdwan2_bw = tables.Column(linkify=True)
    site_sdwan_master_location = tables.Column(linkify=True)
    master_site = tables.Column(linkify=True)
    migration_sdwan = tables.Column(linkify=True)
    monitor_in_starting = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = SopInfra
        fields = (
            'actions', 'pk', 'id', 'created', 'last_updated', 'site', 'status',
            'sdwanha', 'hub_order_setting', 'hub_default_route_setting',
            'sdwan1_bw', 'sdwan2_bw', 'site_sdwan_master_location',
            'master_site', 'migration_sdwan', 'monitor_in_starting'
        )
        default_columns = (
            'actions', 'site', 'status', 'sdwanha', 'hub_order_setting',
            'hub_default_route_setting', 'sdwan1_bw', 'sdwan2_bw'
        )

    def render_status(self, record):
        if not record.site:
            return None
        
        value = record.site.status
        bg_color = SiteStatusChoices.colors.get(value)
        if not bg_color:
            bg_color = "gray"
        return mark_safe(f'<span class="badge text-bg-{bg_color}">{value.title()}</span>')


class SopInfraSizingTable(NetBoxTable):
    '''
    table for all SopInfra - sizing related instances
    '''
    site = tables.Column(linkify=True)
    status = tables.Column(accessor='site__status', linkify=True)
    ad_cumul_user = tables.Column(linkify=True)
    est_cumulative_users = tables.Column(linkify=True)
    wan_computed_users = tables.Column(linkify=True)
    wan_reco_bw = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = SopInfra
        fields = (
            'actions', 'pk', 'id', 'created', 'last_updated', 'site', 'status',
            'ad_cumul_user', 'est_cumulative_users', 'wan_computed_users', 'wan_reco_bw'
        )
        default_columns = (
            'site', 'status', 'ad_cumul_user', 'est_cumulative_users',
            'wan_computed_users', 'wan_reco_bw'
        )
        order_by = ('-wan_reco_bw',)

    '''
    order_<object> methods order from biggest to lowest positive integer
    and skip every 'None' or 'NULL' data

    returns a tuple of (restricted_queryset, is_descending)
    '''
    def order_wan_reco_bw(self, queryset, is_descending):
        return queryset.order_by(models.F('wan_reco_bw').desc(nulls_last=True)), is_descending

    def order_est_cumulative_users(self, queryset, is_descending):
        return queryset.order_by(models.F('est_cumulative_users').desc(nulls_last=True)), is_descending

    def render_wan_reco_bw(self, record):
        return f'{record.wan_reco_bw} (Mbps)'

    def render_status(self, record):
        if not record.site:
            return None
        value = record.site.status
        bg_color = SiteStatusChoices.colors.get(value)
        if not bg_color:
            bg_color = "gray"
        return mark_safe(f'<span class="badge text-bg-{bg_color}">{value.title()}</span>')

class SopInfraClassificationTable(NetBoxTable):
    '''
    table for all SopInfra - classification related instances
    '''
    site = tables.Column(linkify=True)
    status = tables.Column(accessor='site__status', linkify=True)
    site_infra_sysinfra = tables.Column(linkify=True)
    site_type_indus = tables.Column(linkify=True)
    criticity_stars = tables.Column(linkify=True)
    site_phone_critical = ChoiceFieldColumn(linkify=True)
    site_type_red = ChoiceFieldColumn(linkify=True)
    site_type_vip = ChoiceFieldColumn(linkify=True)
    site_type_wms = ChoiceFieldColumn(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = SopInfra
        fields = (
            'actions', 'pk', 'id', 'created', 'last_updated', 'site', 'status'
            'site_infra_sysinfra', 'site_type_indus', 'site_phone_critical',
            'site_type_red', 'site_type_vip', 'site_type_wms',
        )
        default_columns = (
            'site', 'status', 'site_infra_sysinfra', 'site_type_indus',
            'site_phone_critical',
            'site_type_red', 'site_type_vip', 'site_type_wms',
        )
        order_by = ('site_infra_sysinfra',)

    def render_status(self, record):
        if not record.site:
            return None
        
        value = record.site.status
        bg_color = SiteStatusChoices.colors.get(value)
        if not bg_color:
            bg_color = "gray"
        return mark_safe(f'<span class="badge text-bg-{bg_color}">{value.title()}</span>')

    def render_criticity_stars(self, record):
        if not record.criticity_stars:
            return None

        return record.get_criticity_stars()

