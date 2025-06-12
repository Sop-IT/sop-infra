import django_tables2 as tables

from netbox.tables import NetBoxTable, columns
from sop_infra.models import SopMerakiOrg, SopMerakiDash, SopMerakiNet

__all__ = (
    'SopMerakiDashTable',
    'SopMerakiOrgTable',
    'SopMerakiNetTable',
)


class SopMerakiDashTable(NetBoxTable):

    nom = tables.Column(linkify=True)
    orgs_count = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = SopMerakiDash
        fields = ('pk', 'id', 'nom', 'api_url', 'description', 'orgs_count')
        default_columns = ('nom', 'description', 'api_url', 'orgs_count')


class SopMerakiOrgTable(NetBoxTable):

    nom = tables.Column(linkify=True)
    dash = tables.Column(linkify=True)
    nets_count = columns.LinkedCountColumn(
        viewname='plugins:sop_infra:sopmerakinet_list',
        url_params={'org_id': 'pk'},
        verbose_name='Nets count'
    )
    
    class Meta(NetBoxTable.Meta):
        model = SopMerakiOrg
        fields = ('pk', 'id', 'nom', 'dash', 'description', 'meraki_id', 'meraki_url', 'nets_count')
        default_columns = ('dash', 'nom', 'description',  'meraki_url', 'nets_count' )


class SopMerakiNetTable(NetBoxTable):

    nom = tables.Column(linkify=True)
    org = tables.Column(linkify=True)
    site = tables.Column(linkify=True)
    bound_to_template=tables.Column(verbose_name="Bound")
    
    class Meta(NetBoxTable.Meta):
        model = SopMerakiNet
        fields = ('pk', 'id', 'nom', 'org', 'site',  'meraki_id', 'meraki_url', 'meraki_notes', 'bound_to_template', 'ptypes', 'meraki_tags')
        default_columns = ('nom',  'meraki_url',  'site', 'org', 'bound_to_template', 'meraki_notes')



