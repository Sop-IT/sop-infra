from django.utils.translation import gettext_lazy as _

from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem


menu = PluginMenu(
    label="SOPREMA PLUGIN",
    icon_class="mdi mdi-router-network-wireless",
    groups=(
        (
            "MERAKI INTEGRATION",
            (
                PluginMenuItem(
                    link="plugins:sop_infra:sopmerakidash_list",
                    link_text="Dashboards",
                    permissions=["sop_infra.view_sopmerakidash"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakidash_refresh_choose",
                            title="Refetch dashboards from Meraki",
                            icon_class="mdi mdi-refresh",
                            permissions=[f"sop_infra.refresh_sopmerakidash"],
                        ),
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakidash_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=["sop_infra.add_sopmerakidash"],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:sop_infra:sopmerakiorg_list",
                    link_text="Organizations",
                    permissions=["sop_infra.view_sopmerakiorg"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakiorg_refresh_choose",
                            title="Refetch organizations from Meraki",
                            icon_class="mdi mdi-refresh",
                            permissions=[f"sop_infra.refresh_sopmerakiorg"],
                        ),
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakiorg_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=["sop_infra.add_sopmerakiorg"],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:sop_infra:sopmerakinet_list",
                    link_text="Networks",
                    permissions=["sop_infra.view_sopmerakinet"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakinet_refresh_choose",
                            title="Refetch networks from Meraki",
                            icon_class="mdi mdi-refresh",
                            permissions=[f"sop_infra.refresh_sopmerakinet"],
                        ),
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakinet_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=["sop_infra.add_sopmerakinet"],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:sop_infra:sopmerakidevice_list",
                    link_text="Devices",
                    permissions=["sop_infra.view_sopmerakidevice"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakidevice_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=["sop_infra.add_sopmerakidevice"],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:sop_infra:sopmerakiswitchstack_list",
                    link_text="Switch Stacks",
                    permissions=["sop_infra.view_sopmerakiswitchstack"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakiswitchstack_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=["sop_infra.add_sopmerakiswitchstack"],
                        ),
                    ),
                ),
            ),
        ),
        (
            "SOP INFRA",
            (
                PluginMenuItem(
                    link=f"plugins:sop_infra:sopinfra_list",
                    link_text=_("Infrastructures"),
                    permissions=[f"sop_infra.view_sopinfra"],
                    buttons=(
                        PluginMenuButton(
                            link=f"plugins:sop_infra:sopinfra_refresh",
                            title="Recompute",
                            icon_class="mdi mdi-refresh",
                            permissions=[f"sop_infra.change_sop_infra"],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:sop_infra:sopswitchtemplate_list",
                    link_text="Switch templates",
                    permissions=["sop_infra.view_sopswitchtemplate"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:sop_infra:sopswitchtemplate_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=["sop_infra.add_sopswitchtemplate"],
                        ),
                    ),
                ),
            ),
        ),
        (
            "PRISMA INTEGRATION",
            (
                PluginMenuItem(
                    link=f"plugins:sop_infra:prismaendpoint_list",
                    link_text=_("Endpoints"),
                    permissions=["sop_infra.view_prismaendpoint"],
                    buttons=(
                        PluginMenuButton(
                            link=f"plugins:sop_infra:prismaendpoint_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=[f"sop_infra.add_prismaendpoint"],
                        ),
                    ),
                ),
                # PluginMenuItem(
                #     link=f"plugins:sop_infra:prismaaccesslocation_list",
                #     link_text=_("Access Locations"),
                #     permissions=["sop_infra.view_prismaaccesslocation"],
                #     buttons=(
                #         PluginMenuButton(
                #             link=f"plugins:sop_infra:prismaaccesslocation_add",
                #             title="Add",
                #             icon_class="mdi mdi-plus-thick",
                #             permissions=[f"sop_infra.add_prismaaccesslocation"],
                #         ),
                #     ),
                # ),
                # PluginMenuItem(
                #     link=f"plugins:sop_infra:prismacomputedaccesslocation_list",
                #     link_text=_("Computed Access Locations"),
                #     permissions=["sop_infra.view_computedaccesslocation"],
                #     buttons=(
                #         PluginMenuButton(
                #             link=f"plugins:sop_infra:prismacomputedaccesslocation_add",
                #             title="Add",
                #             icon_class="mdi mdi-plus-thick",
                #             permissions=[f"sop_infra.add_prismacomputedaccesslocation"],
                #         ),
                #     ),
                # ),
            ),
        ),
    ),
)

