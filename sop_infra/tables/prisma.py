import django_tables2 as tables

from netbox.tables import NetBoxTable

from sop_infra.models import (
    PrismaEndpoint,
    PrismaAccessLocation,
    PrismaComputedAccessLocation
)


__all__ = (
    'PrismaEndpointTable',
    'PrismaAccessLocationTable',
    'PrismaComputedAccessLocationTable'
)


class PrismaEndpointTable(NetBoxTable):

    class Meta(NetBoxTable.Meta):
        model = PrismaEndpoint
        fields = (
            'actions', 'pk', 'id', 'created', 'last_updated',
            'name', 'slug', 'ip_address', 'address_location',
        )



class PrismaAccessLocationTable(NetBoxTable):

    class Meta(NetBoxTable.Meta):
        model = PrismaAccessLocation
        fields = (
            'actions', 'pk', 'id', 'created', 'last_updated',
            'name', 'slug', 'physical_address', 'time_zone',
            'latitude', 'longitude', 'compute_location'
        )



class PrismaComputedAccessLocationTable(NetBoxTable):

    class Meta(NetBoxTable.Meta):
        model = PrismaComputedAccessLocation
        fields = (
            'actions', 'pk', 'id', 'created', 'last_updated',
            'name', 'slug', 'strata_id', 'strata_name', 'bandwidth'
        )

