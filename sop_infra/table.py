import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, ChoiceFieldColumn

from .models import SopInfra


__all__ = (
    'SopInfraTable',
)


class SopInfraTable(NetBoxTable):
    '''
    table for all SopInfra instances
    '''
    site = tables.Column(
        verbose_name=_('Site'),
        linkify=True
    )

    class Meta(NetBoxTable.Meta):
        model = SopInfra
        fields = (
            'actions', 'pk', 'id', 'created', 'last_updated', 'site',
            'site_infra_sysinfra', 'site_type_indus', 'site_phone_critical',
            'site_type_red', 'site_type_vip', 'site_type_wms',
            'est_cumulative_users',
            'sdwanha', 'hub_order_setting', 'hub_default_route_setting',
            'sdwan1_bw', 'sdwan2_bw', 'site_sdwan_master_location',
            'sdwan_master_site', 'migration_sdwan', 'monitor_in_starting',
        )

        default_columns = ('actions', 'site', 'site_infra_sysinfra',
                           'site_type_indus')

