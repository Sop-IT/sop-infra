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
    site = tables.Column(
        verbose_name=_('Site'),
        linkify=True
    )
    status = tables.Column(
        accessor='site__status',
        linkify=True
    )
    sdwanha = tables.Column(
        verbose_name=_('HA(S) / NHA Target'),
        linkify=True
    )
    hub_order_setting = tables.Column(
        verbose_name=_('HUB Order Settings'),
        linkify=True
    )
    hub_default_route_setting = ChoiceFieldColumn(
        verbose_name=_('HUB Default Route Settings'),
        linkify=True
    )
    sdwan1_bw = tables.Column(
        verbose_name=_('WAN1 BW'),
        linkify=True
    )
    sdwan2_bw = tables.Column(
        verbose_name=_('WAN2 BW'),
        linkify=True
    )
    site_sdwan_master_location = tables.Column(
        verbose_name=_('MASTER Location'),
        linkify=True
    )
    master_site = tables.Column(
        verbose_name=_('MASTER Site'),
        linkify=True
    )
    migration_sdwan = tables.Column(
        verbose_name=_('Migration Date'),
        linkify=True
    )
    monitor_in_starting = tables.Column(
        verbose_name=_('Monitor in Starting'),
        linkify=True
    )

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
        return mark_safe(f'<span class="badge text-bg-{bg_color}">{value.title()}</span>')


class SopInfraSizingTable(NetBoxTable):
    '''
    table for all SopInfra - sizing related instances
    '''
    site = tables.Column(
        verbose_name=_('Site'),
        linkify=True
    )
    status = tables.Column(
        accessor='site__status',
        linkify=True
    )
    ad_cumul_user = tables.Column(
        verbose_name=_('AD cumul. users'),
        linkify=True
    )
    est_cumulative_users = tables.Column(
        verbose_name=_('EST cumul. users'),
        linkify=True
    )
    wan_reco_bw = tables.Column(
        verbose_name=_('Reco. BW (Mbps)'),
        linkify=True
    )
    wan_computed_users = tables.Column(
        verbose_name=_('Wan users'),
        linkify=True
    )

    class Meta(NetBoxTable.Meta):
        model = SopInfra
        fields = (
            'actions', 'pk', 'id', 'created', 'last_updated', 'site', 'status',
            'ad_cumul_user', 'est_cumulative_users',
            'wan_reco_bw', 'wan_computed_users'
        )
        default_columns = (
            'site', 'status', 'ad_cumul_user', 'est_cumulative_users',
            'wan_reco_bw', 'wan_computed_users'
        )

    def render_status(self, record):
        if not record.site:
            return None
        
        value = record.site.status
        bg_color = SiteStatusChoices.colors.get(value)
        return mark_safe(f'<span class="badge text-bg-{bg_color}">{value.title()}</span>')


class SopInfraClassificationTable(NetBoxTable):
    '''
    table for all SopInfra - classification related instances
    '''
    site = tables.Column(
        verbose_name=_('Site'),
        linkify=True
    )
    status = tables.Column(
        accessor="site__status",
        linkify=True
    )
    site_infra_sysinfra = tables.Column(
        verbose_name=_('System Infrastructure'),
        linkify=True
    )
    site_type_indus = tables.Column(
        verbose_name=_('Industrial'),
        linkify=True
    )
    site_phone_critical = ChoiceFieldColumn(
        verbose_name=_('PHONE Critical ?'),
        linkify=True
    )
    site_type_red = ChoiceFieldColumn(
        verbose_name=_('R&D ?'),
        linkify=True
    )
    site_type_vip = ChoiceFieldColumn(
        verbose_name=_('VIP ?'),
        linkify=True
    )
    site_type_wms = ChoiceFieldColumn(
        verbose_name=_('WMS ?'),
        linkify=True
    )

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

    def render_status(self, record):
        if not record.site:
            return None
        
        value = record.site.status
        bg_color = SiteStatusChoices.colors.get(value)
        if not bg_color:
            bg_color = "gray"
        return mark_safe(f'<span class="badge text-bg-{bg_color}">{value.title()}</span>')

