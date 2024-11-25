from django.utils.translation import gettext_lazy as _

from netbox.navigation import *
from netbox.navigation.menu import MENUS


INFRA = Menu(
    label=_("Infrastructure"),
    icon_class="mdi mdi-router-network-wireless",
    groups=(
        MenuGroup(
            label=_("Infrastructure"),
            items=(
                MenuItem(
                    link=f"plugins:sop_infra:class_list",
                    link_text=_("Classifications"),
                    permissions=[f"sop_infra.view_sopinfra"],
                    buttons=(
                        MenuItemButton(
                            link=f"plugins:sop_infra:class_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=[f"sop_infra.add_sopinfra"],
                        ),
                    ),
                ),
                MenuItem(
                    link=f"plugins:sop_infra:sizing_list",
                    link_text=_("Sizings"),
                    permissions=[f"sop_infra.view_sopinfra"],
                    buttons=(
                        MenuItemButton(
                            link=f"plugins:sop_infra:sopinfra_refresh",
                            title="Recompute",
                            icon_class="mdi mdi-refresh",
                            permissions=[f"sop_infra.change_sop_infra"],
                        ),
                        MenuItemButton(
                            link=f"plugins:sop_infra:sizing_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=[f"sop_infra.add_sopinfra"],
                        ),
                    ),
                ),
                MenuItem(
                    link=f"plugins:sop_infra:meraki_list",
                    link_text=_("Meraki SDWAN"),
                    permissions=[f"sop_infra.view_sopinfra"],
                    buttons=(
                        MenuItemButton(
                            link=f"plugins:sop_infra:meraki_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=[f"sop_infra.add_sopinfra"],
                        ),
                    ),
                ),
            ),
        ),
        MenuGroup(
            label=_("PRISMA"),
            items=(
                MenuItem(
                    link=f"plugins:sop_infra:prismaendpoint_list",
                    link_text=_("Endpoints"),
                    permissions=["sop_infra.view_prismaendpoint"],
                    buttons=(
                        MenuItemButton(
                            link=f"plugins:sop_infra:prismaendpoint_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=[f"sop_infra.add_prismaendpoint"],
                        ),
                    ),
                ),
                MenuItem(
                    link=f"plugins:sop_infra:prismaaccesslocation_list",
                    link_text=_("Access Locations"),
                    permissions=["sop_infra.view_prismaaccesslocation"],
                    buttons=(
                        MenuItemButton(
                            link=f"plugins:sop_infra:prismaaccesslocation_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=[f"sop_infra.add_prismaaccesslocation"],
                        ),
                    ),
                ),
                MenuItem(
                    link=f"plugins:sop_infra:prismacomputedaccesslocation_list",
                    link_text=_("Computed Access Locations"),
                    permissions=["sop_infra.view_computedaccesslocation"],
                    buttons=(
                        MenuItemButton(
                            link=f"plugins:sop_infra:prismacomputedaccesslocation_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            permissions=[f"sop_infra.add_prismacomputedaccesslocation"],
                        ),
                    ),
                ),
            ),
        ),
    ),
)


MENUS.append(INFRA)
