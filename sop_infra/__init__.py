from netbox.plugins import PluginConfig


class SopInfraConfig(PluginConfig):
    name = "sop_infra"
    verbose_name = "SOP Infra"
    description = "Manage infrastructure informations of each site"
    version = "0.5.10"
    author = "Soprema NOC team"
    author_email = "noc@soprema.com"
    base_url = "sop-infra"
    min_version = "4.5.8"

    def ready(self):
        super().ready()
        from sop_infra.auto_jobs.dash_ref_job import SopMerakiDashAutoRefreshJob
        from sop_infra.auto_jobs.dash_vpnstatuses_job import SopMerakiDashAutoVpnStatusesJob
        from sop_infra.auto_jobs.sync_ad_users import SopAutoSyncAdUsers

config = SopInfraConfig
