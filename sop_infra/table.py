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
        )
        default_columns = ('actions', 'site',)


