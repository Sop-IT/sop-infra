import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, ChoiceFieldColumn

from .models import SopInfra


__all__ = (
    'SopInfraClassificationTable'
)


class SopInfraClassificationTable(NetBoxTable):
    '''
    table for all SopInfra - classification related instances
    '''
    site = tables.Column(
        verbose_name=_('Site'),
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
    site_phone_critical = tables.Column(
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
            'actions', 'pk', 'id', 'created', 'last_updated', 'site',
            'site_infra_sysinfra', 'site_type_indus', 'site_phone_critical',
            'site_type_red', 'site_type_vip', 'site_type_wms',
        )
        default_columns = (
            'site', 'site_infra_sysinfra', 'site_type_indus',
            'site_phone_critical',
            'site_type_red', 'site_type_vip', 'site_type_wms',
        )

