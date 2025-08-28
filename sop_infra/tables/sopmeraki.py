import django_tables2 as tables

from netbox.tables import NetBoxTable, columns
from sop_infra.models import (
    SopMerakiOrg,
    SopMerakiDash,
    SopMerakiNet,
    SopMerakiDevice,
    SopMerakiSwitchStack,
)


__all__ = (
    "SopMerakiDashTable",
    "SopMerakiOrgTable",
    "SopMerakiNetTable",
    "SopMerakiSwitchStackTable",
    "SopMerakiDeviceTable",
)


class SopMerakiDashTable(NetBoxTable):

    nom = tables.Column(linkify=True)
    orgs_count = tables.Column()
    nets_count = columns.LinkedCountColumn(
        viewname="plugins:sop_infra:sopmerakinet_list",
        url_params={"org__dash_id": "pk"},
        verbose_name="Nets count",
    )
    devs_count = columns.LinkedCountColumn(
        viewname="plugins:sop_infra:sopmerakidevice_list",
        url_params={"org__dash_id": "pk"},
        verbose_name="Devices count",
    )

    class Meta(NetBoxTable.Meta):
        model = SopMerakiDash
        fields = ("pk", "id", "nom", "api_url", "description", "orgs_count", "nets_count", "devs_count")
        default_columns = ("nom", "description", "api_url", "orgs_count")


class SopMerakiOrgTable(NetBoxTable):

    nom = tables.Column(linkify=True)
    dash = tables.Column(linkify=True)
    nets_count = columns.LinkedCountColumn(
        viewname="plugins:sop_infra:sopmerakinet_list",
        url_params={"org_id": "pk"},
        verbose_name="Nets count",
    )
    devs_count = columns.LinkedCountColumn(
        viewname="plugins:sop_infra:sopmerakidevice_list",
        url_params={"org_id": "pk"},
        verbose_name="Devices count",
    )

    class Meta(NetBoxTable.Meta):
        model = SopMerakiOrg
        fields = (
            "pk",
            "id",
            "nom",
            "dash",
            "description",
            "meraki_id",
            "meraki_url",
            "nets_count",
            "devs_count",
        )
        default_columns = (
            "dash",
            "nom",
            "description",
            "meraki_url",
            "nets_count",
            "devs_count",
        )


class SopMerakiNetTable(NetBoxTable):

    nom = tables.Column(linkify=True)
    org = tables.Column(linkify=True)
    site = tables.Column(linkify=True)
    bound_to_template = tables.Column(verbose_name="Bound")
    devs_count = columns.LinkedCountColumn(
        viewname="plugins:sop_infra:sopmerakidevice_list",
        url_params={"org_id": "pk"},
        verbose_name="Devices count",
    )

    class Meta(NetBoxTable.Meta):
        model = SopMerakiNet
        fields = (
            "pk",
            "id",
            "nom",
            "org",
            "site",
            "meraki_id",
            "meraki_url",
            "meraki_notes",
            "bound_to_template",
            "ptypes",
            "meraki_tags",
            "timezone",
            "devs_count",
        )
        default_columns = (
            "nom",
            "meraki_url",
            "site",
            "org",
            "bound_to_template",
            "meraki_notes",
            "devs_count",
        )


class SopMerakiSwitchStackTable(NetBoxTable):

    nom = tables.Column(linkify=True)
    net = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = SopMerakiSwitchStack
        fields = ("pk", "id", "nom", "net", "meraki_id", "serials", "members")
        default_columns = ("nom", "net")


class SopMerakiDeviceTable(NetBoxTable):

    nom = tables.Column(linkify=True)
    org = tables.Column(linkify=True)
    site = tables.Column(linkify=True)
    meraki_network = tables.Column(linkify=True)
    netbox_device = tables.Column(linkify=True, verbose_name="Netbox Device")
    bound_to_template = tables.Column(verbose_name="Bound")
    has_netbox_device = tables.Column(verbose_name="NB device ?", empty_values=(None, False), order_by="netbox_device_id")
    has_netbox_device_in_same_site = tables.Column(verbose_name="Site match ?", empty_values=(None, False), orderable=False)
    has_netbox_device_of_same_type = tables.Column(verbose_name="Type match ?", empty_values=(None, False), orderable=False)

    class Meta(NetBoxTable.Meta):
        model = SopMerakiDevice
        fields = (
            "pk",
            "id",
            "nom",
            "org",
            "site",
            "serial",
            "meraki_netid",
            "meraki_notes",
            "meraki_network",
            "ptype",
            "meraki_tags",
            "meraki_details",
            "firmware",
            "netbox_device",
            "netbox_dev_type",
            "model",
            "mac",
            "has_netbox_device",
            "has_netbox_device_in_same_site",
            "has_netbox_device_of_same_type",
        )
        default_columns = (
            "nom",
            "serial",
            "site",
            "org",
            "meraki_network",
            "netbox_device",
        )
