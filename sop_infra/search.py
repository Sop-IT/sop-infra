from netbox.search import SearchIndex, register_search

from sop_infra.models import SopInfra


@register_search
class SopInfraSearchIndex(SearchIndex):

    model = SopInfra
    fields = (
        ('site', 100),
        ('site_infra_sysinfra', 100),
        ('site_type_indus', 100),
        ('site_phone_critical', 1000),
        ('site_type_red', 1000),
        ('site_type_vip', 1000),
        ('site_type_wms', 1000),
        ('criticity_stars', 100),
        ('est_cumulative_users', 500),
        ('site_user_count', 500),
        ('wan_reco_bw', 500),
        ('site_mx_model', 100),
        ('wan_computed_users', 500),
        ('ad_direct_users', 500),
        ('sdwanha', 100),
        ('hub_order_setting', 500),
        ('hub_default_route_setting', 1000),
        ('sdwan1_bw', 500),
        ('sdwan2_bw', 500),
        ('site_sdwan_master_location', 100),
        ('master_site', 100),
        ('migration_sdwan', 500),
        ('monitor_in_starting', 1000)
    )

