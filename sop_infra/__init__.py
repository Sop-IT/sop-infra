from netbox.plugins import PluginConfig


class SopInfraConfig(PluginConfig):
    name = "sop_infra"
    verbose_name = "SOP Infra"
    description = "Manage infrastructure informations of each site"
    version = "0.4.27"
    author = "Soprema NOC team"
    author_email = "noc@soprema.com"
    base_url = "sop-infra"
    min_version = "4.3.0"

    def ready(self):
        super().ready()
        from .jobs import SopMerakiDashRefreshJob

config = SopInfraConfig
