from netbox.plugins import PluginConfig


class SopInfraConfig(PluginConfig):
    name = "sop_infra"
    verbose_name = "SOP Infra"
    description = "Manage infrastructure informations of each site"
    version = "0.4.16"
    author = "Leorevoir"
    author_email = "leo.quinzler@epitech.eu"
    base_url = "sop-infra"
    min_version = "4.2.0"

    def ready(self):
        super().ready()
        from .jobs import SopMerakiDashRefreshJob

config = SopInfraConfig
