from netbox.plugins import PluginConfig


class SopInfraConfig(PluginConfig):
    name = "sop_infra"
    verbose_name = "SOP Infra"
    description = "Manage infrastructure informations of each site."
    version = "1.0.5"
    author = "Leorevoir"
    author_email = "leoquinzler@epitech.eu"
    base_url = "sop-infra"

config = SopInfraConfig
