from django.utils.translation import gettext_lazy as _

from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem


menu = PluginMenu(
    label="SOPREMA PLUGIN",
    icon_class="mdi mdi-router-network-wireless",
    groups=(
        (
            "SOP MERAKI",
            (
                PluginMenuItem(
                    link="plugins:sop_infra:sopmerakidash_list",
                    link_text="Dashboards",
                    #permissions=["sop_infra.view_merakidashs"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakidash_refresh",
                            title="Refetch dashboards from Meraki",
                            icon_class="mdi mdi-refresh",
                            #permissions=[f"sop_infra.change_sop_infra"],
                        ),
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakidash_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            #permissions=["sop_infra.add_merakidashs"],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:sop_infra:sopmerakiorg_list",
                    link_text="Organizations",
                    #permissions=["sop_infra.view_merakiorgs"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakiorg_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            #permissions=["sop_infra.add_merakiorgs"],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:sop_infra:sopmerakinet_list",
                    link_text="Networks",
                    #permissions=["sop_infra.view_merakinets"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakinet_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            #permissions=["sop_infra.add_merakinets"],
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:sop_infra:sopmerakidevice_list",
                    link_text="Devices",
                    #permissions=["sop_infra.view_merakinets"],
                    buttons=(
                        PluginMenuButton(
                            link="plugins:sop_infra:sopmerakidevice_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            #permissions=["sop_infra.add_merakinets"],
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
            ),
        ),
        (
            "Prisma",
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

