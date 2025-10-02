from netbox.plugins import PluginConfig


class SopInfraConfig(PluginConfig):
    name = "sop_infra"
    verbose_name = "SOP Infra"
    description = "Manage infrastructure informations of each site"
    version = "0.4.51"
    author = "Soprema NOC team"
    author_email = "noc@soprema.com"
    base_url = "sop-infra"
    min_version = "4.3.0"

    def ready(self):
        super().ready()
        from .auto_jobs.dash_ref_job import SopMerakiDashAutoRefreshJob
        from .auto_jobs.sync_ad_users import SopAutoSyncAdUsers

config = SopInfraConfig
