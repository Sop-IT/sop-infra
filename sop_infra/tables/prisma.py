import django_tables2 as tables

from netbox.tables import NetBoxTable

from sop_infra.models import (
    PrismaEndpoint,
    PrismaAccessLocation,
    PrismaComputedAccessLocation,
)


__all__ = (
    "PrismaEndpointTable",
    "PrismaAccessLocationTable",
    "PrismaComputedAccessLocationTable",
)


class PrismaEndpointTable(NetBoxTable):

    class Meta(NetBoxTable.Meta):
        model = PrismaEndpoint
        fields = (
            "actions",
            "pk",
            "id",
            "created",
            "last_updated",
            "name",
            "slug",
            "ip_address",
            "address_location",
        )


class PrismaAccessLocationTable(NetBoxTable):

    compute_location = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = PrismaAccessLocation
        fields = (
            "actions",
            "pk",
            "id",
            "created",
            "last_updated",
            "name",
            "slug",
            "physical_address",
            "time_zone",
            "latitude",
            "longitude",
            "compute_location",
        )

    def render_compute_location(self, record):
        if not record.compute_location:
            return None

        value = record.compute_location.name
        return value.title()


class PrismaComputedAccessLocationTable(NetBoxTable):

    class Meta(NetBoxTable.Meta):
        model = PrismaComputedAccessLocation
        fields = (
            "actions",
            "pk",
            "id",
            "created",
            "last_updated",
            "name",
            "slug",
            "strata_id",
            "strata_name",
            "bandwidth",
        )
