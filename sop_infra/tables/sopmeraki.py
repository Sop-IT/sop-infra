import django_tables2 as tables

from netbox.tables import NetBoxTable
from sop_infra.models import SopMerakiOrg, SopMerakiDash, SopMerakiNet

__all__ = (
    'SopMerakiDashTable',
    'SopMerakiOrgTable',
    'SopMerakiNetTable',
)


class SopMerakiDashTable(NetBoxTable):

    nom = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = SopMerakiDash
        fields = ('pk', 'id', 'nom', 'api_url', 'description')
        default_columns = ('nom', 'description')


class SopMerakiOrgTable(NetBoxTable):

    nom = tables.Column(linkify=True)
    dash = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = SopMerakiOrg
        fields = ('pk', 'id', 'nom', 'dash', 'description')
        default_columns = ('nom', 'description',  'dash')


class SopMerakiNetTable(NetBoxTable):

    nom = tables.Column(linkify=True)
    org = tables.Column(linkify=True)
    site = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = SopMerakiNet
        fields = ('pk', 'id', 'nom', 'org', 'site', 'description')
        default_columns = ('nom', 'description',  'site', 'org')



