from netbox.search import SearchIndex, register_search

from sop_infra.models import *


__all__ = (
    "SopInfraSearchIndex",
    "PrismaEndpointSearchIndex",
    "PrismaAccessLocationSearchIndex",
    "PrismaComputedAccessLocationSearchIndex",
)


@register_search
class SopInfraSearchIndex(SearchIndex):

    model = SopInfra
    fields = (
        ("site", 100),
        ("site_infra_sysinfra", 100),
        ("site_type_indus", 100),
        ("site_phone_critical", 1000),
        ("site_type_red", 1000),
        ("site_type_vip", 1000),
        ("site_type_wms", 1000),
        ("criticity_stars", 100),
        ("est_cumulative_users", 500),
        ("site_user_count", 500),
        ("wan_reco_bw", 500),
        ("site_mx_model", 100),
        ("wan_computed_users", 500),
        ("ad_direct_users", 500),
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
