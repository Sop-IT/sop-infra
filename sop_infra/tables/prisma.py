from collections import defaultdict
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

    slug = tables.Column(linkify=True)
    name = tables.Column(linkify=True)

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
        default_columns = ("actions", "name", "slug", "ip_address", "address_location")


class PrismaAccessLocationTable(NetBoxTable):

    slug = tables.Column(linkify=True)
    name = tables.Column(linkify=True)
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
        default_columns = (
            "actions",
            "name",
            "slug",
            "physical_address",
            "time_zone",
            "latitude",
            "longitude",
            "compute_location",
        )


class PrismaComputedAccessLocationTable(NetBoxTable):

    slug = tables.Column(linkify=True)
    name = tables.Column(linkify=True)

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
        default_columns = (
            "actions",
            "name",
            "slug",
            "strata_id",
            "strata_name",
            "bandwidth",
        )
