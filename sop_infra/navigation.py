from django.utils.translation import gettext_lazy as _

from netbox.registry import registry
from netbox.navigation import *
from netbox.navigation.menu import MENUS


INFRA = Menu(
    label=_('Infrastructure'),
    icon_class="mdi mdi-router-network-wireless",
    groups=(
        MenuGroup(
            label=_('Infrastructure'),
            items=(
                MenuItem(
                    link=f'plugins:sop_infra:class_list',
                    link_text=_('Classifications'),
                    permissions=[f'sop_infra.view_sopinfra'],
                    buttons=(
                        MenuItemButton(
                            link=f'plugins:sop_infra:class_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            permissions=[f'sop_infra.add_sopinfra'],
                        ),
                    ),
                ),
                MenuItem(
                    link=f'plugins:sop_infra:sizing_list',
                    link_text=_('Sizings'),
                    permissions=[f'sop_infra.view_sopinfra'],
                    buttons=(
                        MenuItemButton(
                            link=f'plugins:sop_infra:sizing_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            permissions=[f'sop_infra.add_sopinfra'],
                        ),
                    ),
                ),
                MenuItem(
                    link=f'plugins:sop_infra:meraki_list',
                    link_text=_('Meraki SDWAN'),
                    permissions=[f'sop_infra.view_sopinfra'],
                    buttons=(
                        MenuItemButton(
                            link=f'plugins:sop_infra:meraki_add',
                            title='Add',
                            icon_class='mdi mdi-plus-thick',
                            permissions=[f'sop_infra.add_sopinfra']
                        ),
                    ),
                ),
            ),
        ),
    ),
)


MENUS.append(INFRA)

