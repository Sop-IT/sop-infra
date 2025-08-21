from netbox.search import SearchIndex, register_search

from sop_infra.models import *


__all__ = (
    "SopInfraSearchIndex",
    "SopMerakiDashSearchIndex",
    "SopMerakiOrgSearchIndex",
    "SopMerakiNetSearchIndex",
    "SopMerakiSwitchStackSearchIndex",
    "SopMerakiDeviceSearchIndex",
    "PrismaEndpointSearchIndex",
    "PrismaAccessLocationSearchIndex",
    "PrismaComputedAccessLocationSearchIndex",
)


@register_search
class SopInfraSearchIndex(SearchIndex):

    model = SopInfra
    fields = (
        ("site", 100),
        ("isilog_code", 10),
        ("site_infra_sysinfra", 100),
        ("site_type_indus", 100),
        ("site_phone_critical", 1000),
        ("site_type_red", 1000),
        ("site_type_vip", 1000),
        ("site_type_wms", 1000),
        ("criticity_stars", 100),
        ("est_cumulative_users_wc", 500),
        ("est_cumulative_users_bc", 500),
        ("est_cumulative_users_ext", 500),
        ("est_cumulative_users_nom", 500),
        ("site_user_count", 500),
        ("wan_reco_bw", 500),
        ("site_mx_model", 100),
        ("wan_computed_users_wc", 500),
        ("wan_computed_users_bc", 500),
        ("ad_direct_users_wc", 500),
        ("ad_direct_users_bc", 500),
        ("ad_direct_users_ext", 500),
        ("ad_direct_users_nom", 500),
        ("sdwanha", 100),
        ("hub_order_setting", 500),
        ("hub_default_route_setting", 1000),
        ("sdwan1_bw", 500),
        ("sdwan2_bw", 500),
        ("site_sdwan_master_location", 100),
        ("master_site", 100),
        ("migration_sdwan", 500),
        ("monitor_in_starting", 1000),
        ("endpoint", 100),
        ("enabled", 1000),
        ("valid", 1000),
    )


@register_search
class SopMerakiDashSearchIndex(SearchIndex):

    model = SopMerakiDash
    fields = (
        ("nom", 100),
        ("description", 500),
        ("api_url", 1000),
    )


@register_search
class SopMerakiOrgSearchIndex(SearchIndex):

    model = SopMerakiOrg
    fields = (
        ("nom", 100),
        ("meraki_id", 100),
        ("meraki_url", 1000),
        ("meraki_api", 1000),
        ("meraki_cloud", 1000),
        ("meraki_licensing", 1000),
    )
    display_attrs = ("dash",)


@register_search
class SopMerakiNetSearchIndex(SearchIndex):

    model = SopMerakiNet
    fields = (
        ("nom", 100),
        ("meraki_id", 100),
        ("meraki_tags", 200),
        ("meraki_url", 1000),
        ("meraki_notes", 1700),
    )
    display_attrs = (
        "site",
        "org",
        "ptypes",
        "timezone",
    )


@register_search
class SopMerakiSwitchStackSearchIndex(SearchIndex):

    model = SopMerakiSwitchStack
    fields = (
        ("nom", 100),
        ("meraki_id", 100),
        ("members", 700),
        ("serials", 600),
    )
    display_attrs = (
        "net",
        "site",
    )


@register_search
class SopMerakiDeviceSearchIndex(SearchIndex):

    model = SopMerakiDevice
    fields = (
        ("nom", 100),
        ("serial", 100),
        ("mac", 100),
        ("meraki_notes", 500),
        ("meraki_tags", 400),
        ("meraki_details", 600),
        ("meraki_url", 1000),
        ("firmware", 300),
    )
    display_attrs = (
        "model_name",
        "meraki_network",
        "ptype",
        "site",
        "org",
        "netbox_dev_type",
        "netbox_device",
    )


@register_search
class PrismaEndpointSearchIndex(SearchIndex):

    model = PrismaEndpoint
    fields = (
        ("name", 100),
        ("slug", 100),
        ("ip_address", 100),
        ("access_location", 500),
    )


@register_search
class PrismaAccessLocationSearchIndex(SearchIndex):

    model = PrismaAccessLocation
    fields = (
        ("name", 100),
        ("slug", 100),
        ("physical_address", 100),
        ("time_zone", 500),
        ("latitude", 100),
        ("longitude", 100),
        ("compute_location", 500),
    )


@register_search
class PrismaComputedAccessLocationSearchIndex(SearchIndex):

    model = PrismaComputedAccessLocation
    fields = (
        ("name", 100),
        ("slug", 100),
        ("strata_id", 100),
        ("strata_name", 100),
        ("bandwidth", 100),
    )


# indexes = [
#     SopMerakiDashSearchIndex,
#     SopMerakiOrgSearchIndex,
#     SopMerakiNetSearchIndex,
#     SopMerakiSwitchStackSearchIndex,
#     SopMerakiDeviceSearchIndex,
# ]
