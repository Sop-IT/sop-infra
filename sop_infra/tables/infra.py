
import django_tables2 as tables

from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, ChoiceFieldColumn

from dcim.choices import SiteStatusChoices

from sop_infra.models import *


__all__ = (
    "SopInfraTable",
    "SopInfraSizingTable",
    "SopInfraMerakiTable",
    "SopInfraClassificationTable",
    "SopSwitchTemplateTable",
)


class SopInfraMerakiTable(NetBoxTable):
    """
    table for all SopInfra - meraki sdwan related instances
    """

    site = tables.Column(linkify=True)
    status = tables.Column(accessor="site__status", linkify=True)
    sdwanha = tables.Column(linkify=True)
    hub_order_setting = tables.Column(linkify=True)
    hub_default_route_setting = ChoiceFieldColumn(linkify=True)
    sdwan1_bw = tables.Column(linkify=True)
    sdwan2_bw = tables.Column(linkify=True)
    site_sdwan_master_location = tables.Column(linkify=True)
    master_site = tables.Column(linkify=True)
    migration_sdwan = tables.Column(linkify=True)
    monitor_in_starting = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = SopInfra
        fields = (
            "actions",
            "pk",
            "id",
            "created",
            "last_updated",
            "site",
            "status",
            "sdwanha",
            "hub_order_setting",
            "hub_default_route_setting",
            "sdwan1_bw",
            "sdwan2_bw",
            "site_sdwan_master_location",
            "master_site",
            "migration_sdwan",
            "monitor_in_starting",
        )
        default_columns = (
            "actions",
            "site",
            "status",
            "sdwanha",
            "hub_order_setting",
            "hub_default_route_setting",
            "sdwan1_bw",
            "sdwan2_bw",
        )
        order_by = ("site",)

    def render_status(self, record):
        if not record.site:
            return None

        value = record.site.status
        bg_color = SiteStatusChoices.colors.get(value)
        if not bg_color:
            bg_color = "gray"
        return mark_safe(
            f'<span class="badge text-bg-{bg_color}">{value.title()}</span>'
        )


class SopInfraSizingTable(NetBoxTable):
    """
    table for all SopInfra - sizing related instances
    """

    site = tables.Column(linkify=True)
    status = tables.Column(accessor="site__status")

    class Meta(NetBoxTable.Meta):
        model = SopInfra
        fields = (
            "actions",
            "pk",
            "id",
            "created",
            "last_updated",
            "site",
            "status",
            "est_cumulative_users_wc",
            "est_cumulative_users_bc",
            "est_cumulative_users_ext",
            "est_cumulative_users_nom",
            "wan_computed_users_wc",
            "wan_computed_users_bc",
            "wan_reco_bw",
            "ad_direct_users_wc",
            "ad_direct_users_bc",
            "ad_direct_users_ext",
            "ad_direct_users_nom",
            "site_mx_model",
        )
        default_columns = (
            "site",
            "status",
            "est_cumulative_users_bc",
            "est_cumulative_users_wc",
            "ad_direct_users_wc",
            "ad_direct_users_bc",
            "wan_computed_users_wc",
            "wan_computed_users_bc",
            "wan_reco_bw",
            "site_mx_model",
        )
        order_by = ("site",)

    def render_status(self, record):
        if not record.site:
            return None
        value = record.site.status
        bg_color = SiteStatusChoices.colors.get(value)
        if not bg_color:
            bg_color = "gray"
        return mark_safe(
            f'<span class="badge text-bg-{bg_color}">{value.title()}</span>'
        )


class SopInfraClassificationTable(NetBoxTable):
    """
    table for all SopInfra - classification related instances
    """

    site = tables.Column(linkify=True)
    status = tables.Column(accessor="site__status", linkify=True)
    site_infra_sysinfra = tables.Column(linkify=True)
    site_type_indus = tables.Column(linkify=True)
    criticality_stars = tables.Column(linkify=True)
    site_phone_critical = ChoiceFieldColumn(linkify=True)
    site_type_red = ChoiceFieldColumn(linkify=True)
    site_type_vip = ChoiceFieldColumn(linkify=True)
    site_type_wms = ChoiceFieldColumn(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = SopInfra
        fields = (
            "actions",
            "pk",
            "id",
            "created",
            "last_updated",
            "site",
            "status" "site_infra_sysinfra",
            "site_type_indus",
            "site_phone_critical",
            "site_type_red",
            "site_type_vip",
            "site_type_wms",
        )
        default_columns = (
            "site",
            "status",
            "site_infra_sysinfra",
            "site_type_indus",
            "site_phone_critical",
            "site_type_red",
            "site_type_vip",
            "site_type_wms",
            "criticality_stars",
        )
        order_by = ("site",)

    def render_status(self, record):
        if not record.site:
            return None

        value = record.site.status
        bg_color = SiteStatusChoices.colors.get(value)
        if not bg_color:
            bg_color = "gray"
        return mark_safe(
            f'<span class="badge text-bg-{bg_color}">{value.title()}</span>'
        )

    def render_criticality_stars(self, record):
        if not record.criticality_stars:
            return None

        return record.get_criticality_stars()


class SopInfraTable(NetBoxTable):

    class Meta(NetBoxTable.Meta):
        model = SopInfra
        fields = (
            "actions",
            "pk",
            "id",
            "created",
            "last_updated",
            "site",
            "site__status",
            "site_infra_sysinfra",
            "site_type_indus",
            "site_phone_critical",
            "site_type_red",
            "site_type_vip",
            "site_type_wms",
            "est_cumulative_users_wc",
            "est_cumulative_users_bc",
            "est_cumulative_users_ext",
            "est_cumulative_users_nom",
            "wan_computed_users_wc",
            "wan_computed_users_bc",
            "wan_reco_bw",
            "ad_direct_users_wc",
            "ad_direct_users_bc",
            "ad_direct_users_ext",
            "ad_direct_users_nom",
            "site_mx_model",
            "criticality_stars",
            "sdwanha",
            "hub_order_setting",
            "hub_default_route_setting",
            "sdwan1_bw",
            "sdwan2_bw",
            "site_sdwan_master_location",
            "master_site",
            "migration_sdwan",
            "monitor_in_starting",
            "claim_net_mx",
            "claim_net_ms",
            "claim_net_mr",
        )
        default_columns = (
            "id",
            "site",
            "site__status",
            "criticality_stars",
            "sdwanha",
            "wan_computed_users_wc",
        )

        order_by = ("site",)

    def render_site__status(self, record):
        if not record.site:
            return None

        value = record.site.status
        bg_color = SiteStatusChoices.colors.get(value)
        if not bg_color:
            bg_color = "gray"
        return mark_safe(
            f'<span class="badge text-bg-{bg_color}">{value.title()}</span>'
        )

    def render_criticality_stars(self, record):
        if not record.criticality_stars:
            return None

        return record.get_criticality_stars()



# ======================================================================
#  SWITCH TEMPLATES TABLES

class SopSwitchTemplateTable(NetBoxTable):
    
    class Meta(NetBoxTable.Meta):
        model = SopSwitchTemplate
        fields = (
            "nom",
            "stp_prio",
        )
        default_columns = (
            "nom",
            "stp_prio",
        )
        order_by = ("nom",)




# ======================================================================
#  OTHER

class SopSyslogServerTable(NetBoxTable):
    nom = tables.Column(
        verbose_name=_('Name'),
        linkify=True
    )

    class Meta(NetBoxTable.Meta):
        model = SopSyslogServer
        fields = (
            "pk",
            "id",
            "nom",
            "server_address",
            "server_port",
            "enabled",
        )
        default_columns = (
            "nom",
            "server_address",
            "server_port",
            "enabled",
        )

        order_by = ("nom", "server_address","server_port","enabled",)

