
from scripts.DHCPUtils import TargetNetwork

from django.utils.text import slugify
from django.db.models import Q
from django.db.models import Min
from django.db.models.functions.math import Mod
from django.core.exceptions import ValidationError

from extras.scripts import BooleanVar, ObjectVar, Script
from utilities.exceptions import AbortScript



import meraki  # type: ignore
import dcim.models

import netaddr

import json
from ipam.models import Prefix
from dcim.models import Site, Device, DeviceType

from sop_infra.utils.meraki_objects import *
from sop_infra.models import SopMerakiNet, SopSwitchTemplate, SopDeviceSetting
from sop_utils.misc import SopUtils
from sop_infra.utils.mixins import SopBaseScriptMixin
from sop_infra.models.sopmeraki import SopMerakiUtils, SopRegExps

# =======================================================================


class MerakiSiteUpdater:

    stub_vlan_id: int = 3998

    def __init__(
        self,
        dash: meraki.DashboardAPI,
        tgt_nets: list[TargetNetwork],
        siteName,
        net: MerakiNetwork,
        logger,
        details: bool = False,
    ):
        self.__merakiDashboard = dash
        self.logger = logger
        self.siteName = siteName
        self.net = net
        self.details = details
        self.tgt_nets: list[TargetNetwork] = tgt_nets
        self.site_vlans: list[dict] = []
        self.site_routes: list[dict] = []
        self.site_gps: list[dict] = []

    def get_dashboard(self):
        if self.__merakiDashboard is not None:
            return self.__merakiDashboard
        raise Exception("Not connected")

    def _refresh_cache(self):
        # ANALYZE VLANS/ROUTES/POLICIES AND CACHE THEM
        self.logger.log_debug(
            f"----- ANALYZING MERAKI NETWORK {self.net.name} - {self.net.id}"
        )
        for v in self.get_dashboard().appliance.getNetworkApplianceVlans(self.net.id):
            self.site_vlans.append(v)
        for v in self.get_dashboard().appliance.getNetworkApplianceStaticRoutes(
            self.net.id
        ):
            self.site_routes.append(v)
        self.site_gps = self.get_dashboard().networks.getNetworkGroupPolicies(
            self.net.id
        )
        self.logger.log_debug(
            f"   Analyze done --> found {len(self.site_vlans)} vlans, {len(self.site_routes)} routes and {len(self.site_gps)} group policies "
        )

    # ---------------------------------------
    # VLANS
    def _create_meraki_vlan(self, vlan, log_inf: str):
        try:
            self.get_dashboard().appliance.createNetworkApplianceVlan(
                **prepare_create_vlan(vlan)
            )  # APIError
            self.site_vlans.append(vlan)
        except Exception as err:
            self.logger.log_failure(
                f"   {log_inf} ;  VLAN : {vlan} \n {err=}, {type(err)=}"
            )
            raise err
        else:
            self.logger.log_success(f"   {log_inf}")
            if self.details:
                self.logger.log_success(f"   Added VLAN {vlan}")

    def _update_meraki_vlan(self, vlan, log_inf: str):
        try:
            self.get_dashboard().appliance.updateNetworkApplianceVlan(
                **prepare_put_vlan(vlan)
            )  # APIError
            self.__remove_meraki_vlan(vlan.get(id, 0))
            self.site_vlans.append(vlan)
        except Exception as err:
            self.logger.log_failure(
                f"   {log_inf} ;  VLAN : {vlan} \n {err=}, {type(err)=}"
            )
            raise err
        else:
            self.logger.log_success(f"   {log_inf}")
            if self.details:
                self.logger.log_success(f"   Updated VLAN {vlan}")

    def _del_meraki_vlan(self, vlan, log_inf: str):
        if (
            len(self.site_vlans) == 1
            and vlan.get("id") == MerakiSiteUpdater.stub_vlan_id
        ):
            self.logger.log_debug(
                f"   Do NOT delete the stub VLAN when it's the last VLAN"
            )
            return
        if self.__about_to_del_last_vlan(vlan):
            self._push_temp_stub_vlan()
        try:
            self.get_dashboard().appliance.deleteNetworkApplianceVlan(
                self.net.id, vlan.get("id")
            )
            self.__remove_meraki_vlan(vlan.get("id", -1))
        except Exception as err:
            self.logger.log_failure(
                f"   {log_inf} ;  VLAN : {vlan} \n {err=}, {type(err)=}"
            )
            raise err
        else:
            self.logger.log_success(f"   {log_inf}")
            if self.details:
                self.logger.log_success(f"   Removed VLAN {vlan}")

    def __find_meraki_vlan(self, vid: int):
        for index in range(len(self.site_vlans)):
            if vid == self.site_vlans[index].get("id"):
                return index
        return -1

    def __remove_meraki_vlan(self, vid: int):
        index = self.__find_meraki_vlan(vid)
        if index >= 0:
            self.site_vlans.pop(index)

    def __about_to_del_last_vlan(self, vlan) -> bool:
        l = len(self.site_vlans)
        if l > 1:
            return False
        if l == 0:
            return True
        vid = vlan.get("id", MerakiSiteUpdater.stub_vlan_id)
        return vid == self.site_vlans[0].get("id")

    def _push_temp_stub_vlan(self):
        self._create_meraki_vlan(
            self.__build_stub_vlan(), "CREATE STUB AS A WORKAROUND"
        )

    def _remove_temp_stub_vlan(self):
        index = self.__find_meraki_vlan(MerakiSiteUpdater.stub_vlan_id)
        if index >= 0 and len(self.site_vlans) > 1:
            self._del_meraki_vlan(self.__build_stub_vlan(), "REMOVE WORKAROUND STUB")

    def __build_stub_vlan(self):
        return {
            "id": MerakiSiteUpdater.stub_vlan_id,
            "networkId": self.net.id,
            "subnet": "127.98.0.0/24",
            "name": "netbox_stub",
            "applianceIp": f"127.98.0.254",
        }

    # ---------------------------------------
    # ROUTES
    def _create_meraki_route(self, route, log_inf: str):
        try:
            self.get_dashboard().appliance.createNetworkApplianceStaticRoute(
                **prepare_create_route(route)
            )  # APIError
            self.site_routes.append(route)
        except Exception as err:
            self.logger.log_failure(
                f"   {log_inf} ;  ROUTE : {route} \n {err=}, {type(err)=}"
            )
            raise err
        else:
            self.logger.log_success(f"   {log_inf}")
            if self.details:
                self.logger.log_success(f"   Added ROUTE {route}")

    def _update_meraki_route(self, route, log_inf: str):
        try:
            self.get_dashboard().appliance.updateNetworkApplianceStaticRoute(
                **prepare_put_route(route)
            )  # APIError
            self.__remove_meraki_route(route.get("subnet", ""))
            self.site_routes.append(route)
        except Exception as err:
            self.logger.log_failure(
                f"   {log_inf} ;  ROUTE : {route} \n {err=}, {type(err)=}"
            )
            raise err
        else:
            self.logger.log_success(f"   {log_inf}")
            if self.details:
                self.logger.log_success(f"   Updated ROUTE {route}")

    def _del_meraki_route(self, route, log_inf: str):
        try:
            self.get_dashboard().appliance.deleteNetworkApplianceStaticRoute(
                self.net.id, route.get("id")
            )
            self.__remove_meraki_route(route.get("subnet", ""))
        except Exception as err:
            self.logger.log_failure(
                f"   {log_inf}; Route : {route} \n {err=}, {type(err)=}"
            )
            self.raiseError = True
        else:
            self.logger.log_success(f"   {log_inf}")
            if self.details:
                self.logger.log_success(f"   Removed route : {route}")

    def __remove_meraki_route(self, subnet: str):
        for index in range(len(self.site_routes)):
            if subnet == self.site_routes[index].get("subnet"):
                self.site_routes.pop(index)
                break

    def _update_or_create_meraki_network(
        self,
        tgt_net: TargetNetwork,
        site_gps,
        site_vlans,
        site_routes,
        siteName: str,
        net: MerakiNetwork,
        details: bool,
    ):
        if details:
            self.logger.log_debug(f"handling {tgt_net} ")
        if tgt_net.get_nb_prefix().status in ["retired", "reserved"]:
            self.logger.log_debug(
                f"skipping {tgt_net} because of its {tgt_net.get_nb_prefix().status} status "
            )
            return
        # PUSH/UPDATE VLAN
        if tgt_net.is_vlan():
            # Correspondance NetBox prefix == Meraki vlan/staticroute (ex: 10.170.11.0/24)
            vlans = list(
                filter(
                    lambda v: tgt_net.prefix_str == v["subnet"]
                    and tgt_net.vlan_id == v["id"],
                    site_vlans,
                )
            )
            # Check logique
            if len(vlans) > 1:
                # Problem here : we cannot have twice the same vlan subnet on the same MX device !
                self.logger.log_failure(
                    f"   Several VLANs found on Meraki site {net.name}/{net.id} for prefix '{tgt_net.prefix_str}'"
                )
                return
            # Check besoin de creation
            if do_create := (len(vlans) == 0):
                # Not found -> need to create it
                vlan = {
                    "id": tgt_net.nb_prefix.vlan.vid,
                    "networkId": net.id,
                    "subnet": tgt_net.prefix_str,
                    "name": tgt_net.get_net_name(),
                    "applianceIp": f"{netaddr.IPAddress(tgt_net.nb_prefix.prefix.last-1)}",
                }
            else:
                # Found a single one, let's update
                vlan = vlans[0]
            # Clear potential failure causes
            if "ipv6" in vlan:
                del vlan["ipv6"]
            # Build target
            tgt = tgt_net.build_target_meraki_vlan(vlan, net, self.logger)
            # Create or update ?
            if do_create:
                self._create_meraki_vlan(
                    tgt,
                    f"   Meraki createNetworkApplianceVlan on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'",
                )
                # workaround for  https://community.meraki.com/t5/Developers-APIs/Create-VLAN-using-API-on-MX/m-p/250984#M11413
                self._update_meraki_vlan(
                    tgt,
                    f"   Meraki updateNetworkApplianceVlan on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'",
                )
            else:
                # ranges are not sorted -> need to be sorted before being serialized
                if tgt.get("reservedIpRanges") is not None:
                    tgt["reservedIpRanges"].sort(key=(lambda x: x.get("start")))
                if vlan.get("reservedIpRanges") is not None:
                    vlan["reservedIpRanges"].sort(key=(lambda x: x.get("start")))
                if details:
                    import json

                    deep1 = json.dumps(tgt, sort_keys=True, indent=2)
                    deep2 = json.dumps(vlan, sort_keys=True, indent=2)
                    self.logger.log_debug(
                        f"Compare {deep1==deep2}vs{SopUtils.deep_equals_json(tgt, vlan)} -> { deep1} to {deep2}"
                    )
                if SopUtils.deep_equals_json(tgt, vlan):
                    self.logger.log_info(
                        f"   no change on site '{siteName}' for prefix: '{tgt_net.prefix_str}'"
                    )
                else:
                    self._update_meraki_vlan(
                        tgt,
                        f"   Meraki updateNetworkApplianceVlan on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'",
                    )
        elif tgt_net.is_route():
            # Correspondance NetBox prefix == Meraki vlan/staticroute (ex: 10.170.11.0/24)
            routes = list(
                filter(lambda v: tgt_net.prefix_str == v["subnet"], site_routes)
            )
            # Check logique
            if len(routes) > 1:
                # Problem here : we cannot have twice the same route on the same MX device !
                self.logger.log_failure(
                    f"   Several ROUTES found on Meraki site {net.name}/{net.id} for prefix '{tgt_net.prefix_str}'"
                )
                return
            # Check besoin de creation
            if do_create := (len(routes) == 0):
                # Not found -> need to create it
                route = {
                    "networkId": net.id,
                    "enabled": bool(
                        tgt_net.get_nb_prefix().status
                        in MerakiConstants.active_route_statuses
                    ),
                    "subnet": tgt_net.prefix_str,
                    "name": tgt_net.get_net_name(),
                    "gatewayIp": f"{tgt_net.dhcp_settings.sdw_routed_via.address.ip}",
                }
            else:
                # Found a single one, let's update
                route = routes[0]
            # Clear potential failure causes
            if "gatewayVlanId" in route:
                del route["gatewayVlanId"]
            # Build target
            tgt = tgt_net.build_target_meraki_route(route, self.logger)
            # Create or update ?
            if do_create:
                self._create_meraki_route(
                    tgt,
                    f"   Meraki createNetworkApplianceStaticRoute on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'",
                )
            else:
                # ranges are not sorted -> need to be sorted before being serialized
                if tgt.get("reservedIpRanges") is not None:
                    tgt["reservedIpRanges"].sort(key=(lambda x: x.get("start")))
                if route.get("reservedIpRanges") is not None:
                    route["reservedIpRanges"].sort(key=(lambda x: x.get("start")))
                if details:
                    import json

                    deep1 = json.dumps(tgt, sort_keys=True, indent=2)
                    deep2 = json.dumps(route, sort_keys=True, indent=2)
                    self.logger.log_debug(
                        f"Compare {deep1==deep2}vs{SopUtils.deep_equals_json(tgt, route)} -> { deep1} to {deep2}"
                    )
                if SopUtils.deep_equals_json(tgt, route):
                    self.logger.log_info(
                        f"   no change on site '{siteName}' for prefix: '{tgt_net.prefix_str}'"
                    )
                else:
                    # site_to_sites=self.get_dashboard().appliance.getNetworkApplianceVpnSiteToSiteVpn(route['networkId'])
                    self._update_meraki_route(
                        tgt,
                        f"   Meraki updateNetworkApplianceStaticRoute on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'",
                    )
                    # self.get_dashboard().appliance.updateNetworkApplianceVpnSiteToSiteVpn(networkId=route['networkId'], **site_to_sites)
        else:
            self.logger.log_failure(
                f"UPDATE/CREATE CODE ERROR : tgt_net is neither VLAN nor ROUTE {tgt_net}"
            )

    def purge_l3_fw_rules(self, nbp: Prefix, tgt_net: TargetNetwork) -> None:
        # Nothing to purge if the prefix needs rules
        if tgt_net.gp.has_rules():
            return
        # Build our rule name
        rule_name = f"VLAN_{slugify(nbp.vlan.name,False).upper()}_NETB_L3RULES"
        # DO we have existing rules ?
        r: dict = {}
        if found := (self.site_gps is not None and len(self.site_gps) > 0):
            # We have something, try to find the rule
            for r in self.site_gps:
                if found := SopUtils.safe_equals(rule_name, r.get("name")):
                    break
        if found:
            # no rules at the target -> we need to delete that
            try:
                self.logger.log_info(
                    f"   Delete ruleset '{rule_name}' on '{self.siteName}'"
                )
                self.get_dashboard().networks.deleteNetworkGroupPolicy(
                    self.net.id, r.get("groupPolicyId")
                )
                self.site_gps.remove(r)
            except Exception as err:
                self.logger.log_failure(f"Failure detected : {err}")
                self.logger.log_failure(
                    f"Current object :  {self.siteName}/{tgt_net.prefix_str} "
                )
                raise err

    def push_l3_fw_rules(self, nbp: Prefix, tgt_net: TargetNetwork) -> None:
        if self.details:
            self.logger.log_debug(f"handling {tgt_net} ")
        if tgt_net.get_nb_prefix().status in ["retired", "reserved"]:
            if self.details:
                self.logger.log_debug(
                    f"skipping {tgt_net} because of its {tgt_net.get_nb_prefix().status} status "
                )
            return
        # Nothing to push if the prefix doesn't need rules
        if not (tgt_net.gp.has_rules()):
            return
        # Build our rule name
        rule_name = f"VLAN_{slugify(nbp.vlan.name,False).upper()}_NETB_L3RULES"
        # DO we have existing rules ?
        r: dict = {}
        if found := (self.site_gps is not None and len(self.site_gps) > 0):
            # We have something, try to find the rule
            for r in self.site_gps:
                if found := SopUtils.safe_equals(rule_name, r.get("name")):
                    break
        if found:
            # We found the rule : it's in r
            # now check if they match or need an update
            upd = False
            fas = r.get("firewallAndTrafficShaping")
            if fas is None:
                upd = True
                # self.log_info(f" fas is none for {rule_name}")
            else:
                ol3r = fas.get("l3FirewallRules")
                if ol3r is None:
                    upd = True
                    # self.log_info(f" ol3r is none for {rule_name}")
                elif not (
                    SopUtils.deep_equals_json_ic(ol3r, tgt_net.gp.group_policy_list)
                ):
                    upd = True
                    if self.details:
                        self.logger.log_debug(f" conf distincte :")
                        self.logger.log_debug(
                            f" OLD : {json.dumps(ol3r, sort_keys=True, indent=2)}"
                        )
                        self.logger.log_debug(
                            f" NEW : {json.dumps(tgt_net.gp.group_policy_list, sort_keys=True, indent=2)}"
                        )
            if upd:
                # PROBLEM IF WE HAVE TO UPDATE IN THE TEMPLATE -> HAS TO BE DONE MANUALY
                if self.net.bound:
                    self.logger.log_failure(
                        f"CANNOT UPDATE L3 RULES ON TEMPLATIZED NETWORK '{self.siteName}' (for prefix: '{tgt_net.prefix_str}') ===> THIS MUST BE DONE MANUALY"
                    )
                    return
                # Update !
                try:
                    self.logger.log_success(
                        f"   Update ruleset '{rule_name}' on '{self.siteName}'"
                    )
                    self.get_dashboard().networks.updateNetworkGroupPolicy(
                        self.net.id,
                        r.get("groupPolicyId"),
                        firewallAndTrafficShaping={
                            "settings": "custom",
                            "l3FirewallRules": tgt_net.gp.group_policy_list,
                        },
                    )
                except Exception as err:
                    self.logger.log_failure(f"Failure detected : {err}")
                    self.logger.log_failure(
                        f"Current object :  {self.siteName}/{tgt_net.prefix_str}\n -> {tgt_net.gp.group_policy_list}"
                    )
                    raise err
            # Pas sûr si c'est cause des templates ou du non commit ou ....
            if r.get("groupPolicyId") is not None:
                if self.details:
                    self.logger.log_debug(
                        f"setting groupPolicyId to {r.get('groupPolicyId')} for {rule_name} on network {self.net.name}/{self.net.id}"
                    )
                tgt_net.gp.group_policy_id[self.net.id] = f"{r.get('groupPolicyId')}"

        else:
            # We did not find the rule ->  let's create it
            # PROBLEM WITH TEMPLATES -> HAS TO BE DONE MANUALY
            if self.net.bound:
                self.logger.log_failure(
                    f"CANNOT CREATE L3 RULES ON TEMPLATIZED NETWORK '{self.siteName}' (for prefix: '{tgt_net.prefix_str}') ===> THIS MUST BE DONE MANUALY"
                )
                return
            # No FW rule or rule not found by name
            self.logger.log_info(
                f"   Create ruleset '{rule_name}' on '{self.siteName}'"
            )
            try:
                r = self.get_dashboard().networks.createNetworkGroupPolicy(
                    self.net.id,
                    rule_name,
                    firewallAndTrafficShaping={
                        "settings": "custom",
                        "l3FirewallRules": tgt_net.gp.group_policy_list,
                    },
                )
            except Exception as err:
                self.logger.log_failure(f"Failure detected : {err}")
                self.logger.log_failure(
                    f"Current object :  {self.siteName}/{tgt_net.prefix_str}\n -> {tgt_net.gp.group_policy_list}"
                )
                raise err
            # Check creation return
            if r is None or r.get("groupPolicyId") is None:
                self.logger.log_failure(
                    f"PROBLEM WITH L3RULES CREATION ON NETWORK '{self.siteName}' (for prefix: '{tgt_net.prefix_str}') ===> THIS MUST BE LOOKED MANUALY"
                )
            else:
                if self.details:
                    self.logger.log_debug(
                        f"setting groupPolicyId to {r.get('groupPolicyId')} for {rule_name} on network {self.net.name}/{self.net.id}"
                    )
                tgt_net.gp.group_policy_id[self.net.id] = f"{r.get('groupPolicyId')}"

    def patch_one_meraki_site_network(self):

        tgt_net: TargetNetwork

        # HANDLE THE CASE OF ROUTED VLAN 1
        self.logger.log_debug(
            f"----- CHECKING FOR ROUTED VLAN 1 ON MERAKI NETWORK {self.net.name} - {self.net.id}"
        )
        rtone = False
        for tgt in self.tgt_nets:
            if tgt.vlan_id == 1 and tgt.is_route():
                if self.details:
                    self.logger.log_debug(f" rtone for net {self.net.id} : {tgt}")
                rtone = True
                break
        lports = self.get_dashboard().appliance.getNetworkAppliancePorts(self.net.id)
        if self.details:
            self.logger.log_debug(
                f" netork appliance ports for net {self.net.id} : {lports}"
            )
        if rtone:
            for lport in lports:
                if not (lport["enabled"] == True):
                    continue
                if not (lport["vlan"] == 1):
                    continue
                if lport["type"] == "access":
                    raise AbortScript(
                        f"Cannot deploy routed vlan 1 to this site as port {lport['number']} is enabled and configured as access vlan 1.  \nYOU NEED TO RESOLVE THIS SITUATION MANUALLY BY ADJUSTING THE MX PORT AND SWITCH CONFIGURATION"
                    )
                if lport["type"] == "trunk":
                    stg = {
                        "enabled": True,
                        "type": "trunk",
                        "dropUntaggedTraffic": lport["dropUntaggedTraffic"],
                        "vlan": 3999,
                        "allowedVlans": "all",
                    }
                    num = lport.get("number")
                    del lport["number"]
                    if not SopUtils.deep_equals_json(lport, stg, True):
                        if self.details:
                            self.logger.log_debug(
                                f" found diff on port {num} between existing port {lport} and computed target {stg}"
                            )
                        self.get_dashboard().appliance.updateNetworkAppliancePort(
                            self.net.id, num, **stg
                        )
                        self.logger.log_success(f"Updated appliance port {num} ")
                else:
                    raise AbortScript(
                        f"Meraki API changed and we have a MX port type that we didn't expect : {lport['type']} on port {lport['number']}"
                    )
        else:
            for lport in lports:
                if not (lport["enabled"] == True):
                    continue
                if lport["type"] == "access":
                    continue
                if lport["dropUntaggedTraffic"]:
                    continue
                if not (lport["vlan"] == 3999):
                    continue
                if lport["type"] == "trunk":
                    stg = {
                        "enabled": True,
                        "type": "trunk",
                        "dropUntaggedTraffic": lport["dropUntaggedTraffic"],
                        "vlan": 1,
                        "allowedVlans": "all",
                    }
                    num = lport.get("number")
                    del lport["number"]
                    if not SopUtils.deep_equals_json(lport, stg, True):
                        if self.details:
                            self.logger.log_debug(
                                f" found diff on port {num} between existing port {lport} and computed target {stg}"
                            )
                        self.get_dashboard().appliance.updateNetworkAppliancePort(
                            self.net.id, num, **stg
                        )
                        self.logger.log_success(f"Updated appliance port {num} ")
                else:
                    raise AbortScript(
                        f"Meraki API changed and we have a MX port type that we didn't expect : {lport['type']} on port {lport['number']}"
                    )

        # ANALYZE VLANS/ROUTES/POLICIES AND CACHE THEM
        self._refresh_cache()

        # DELETE NETWORKS OF THE WRONG TYPE (ROUTES VS VLANS)
        self.logger.log_debug(f'----- DELETING "WRONG" NETWORKS ')
        for tgt_net in self.tgt_nets:
            if self.details:
                self.logger.log_debug(f"handling {tgt_net} ")
            if tgt_net.is_vlan():
                # Find the Meraki routes that exist for this subnet instead of vlans
                routes = list(
                    filter(
                        lambda v: tgt_net.prefix_str == v["subnet"], self.site_routes
                    )
                )
                # self.log_debug(f' is vlan {tgt_net} -> routes to remove = {routes}')
                for route in routes:
                    self._del_meraki_route(
                        route,
                        f"   Meraki deleteNetworkApplianceStaticRoute on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}' (Route={route})",
                    )
            elif tgt_net.is_route():
                # Find the Meraki vlans that exist for this subnet instead of routes
                vlans = list(
                    filter(lambda v: tgt_net.prefix_str == v["subnet"], self.site_vlans)
                )
                # self.log_debug(f' is route {tgt_net} -> vlans to remove = {vlans}')
                for vlan in vlans:
                    self._del_meraki_vlan(
                        vlan,
                        f"   Meraki deleteNetworkApplianceVlan on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'",
                    )
            else:
                self.logger.log_failure(
                    f"DELETE WRONG NETWORKS CODE ERROR : tgt_net is either VLAN or ROUTE {tgt_net}"
                )

        # DELETE NETWORK THAT WERE RETIRED OR DO NOT EXIST IN NETBOX
        self.logger.log_debug(
            f"----- DELETING RETIRED , RESERVED OR NON-EXISTENT NETWORKS "
        )
        for v in self.site_vlans:
            found = None
            for tgt_net in self.tgt_nets:
                if tgt_net.is_vlan():
                    if tgt_net.prefix_str == v["subnet"] and tgt_net.vlan_id == v["id"]:
                        found = tgt_net
                        break
            if found is None or found.get_nb_prefix().status in ["retired", "reserved"]:
                self._del_meraki_vlan(
                    v,
                    f"   Meraki deleteNetworkApplianceVlan on site '{self.siteName}' for prefix: '{v['subnet']}'",
                )
        for r in self.site_routes:
            found = None
            for tgt_net in self.tgt_nets:
                if tgt_net.is_route():
                    if tgt_net.prefix_str == r["subnet"]:
                        found = tgt_net
                        break
            if found is None or found.get_nb_prefix().status in ["retired", "reserved"]:
                self._del_meraki_route(
                    r,
                    f"   Meraki deleteNetworkApplianceStaticRoute on site '{self.siteName}' for prefix: '{r['subnet']}'",
                )

        # TODO : CALCULATE DEFERRED RULES BASE ON CONTEXT
        # TODO : ALSO INCLUDES COMBINATION FOR ROUTED NETWORKS ?

        # MAKE SURE WE HAVE THE POLICY IDS NEEDED AFTERWARDS
        self.logger.log_debug(
            f"----- PUSHING L3 RULES ON NETWORK {self.net.name} - {self.net.id}"
        )
        for tgt_net in self.tgt_nets:
            if tgt_net.is_vlan:
                self.push_l3_fw_rules(tgt_net.nb_prefix, tgt_net)

        # UPDATE EXISTING NETWORKS / CREATE NON-EXISTING ONES
        self.logger.log_debug(f"----- UPDATING/CREATING NETWORKS ")
        tgt_net: TargetNetwork|None = None
        for tgt_net in self.tgt_nets:
            self._update_or_create_meraki_network(
                tgt_net,
                self.site_gps,
                self.site_vlans,
                self.site_routes,
                self.siteName,
                self.net,
                self.details,
            )

        # DELETE L3RULES THAT HAVE AREN'T NEEDED ANYMORE ON THE EXISTING NETWORKS (RULES EMPTIED)
        self.logger.log_debug(
            f"----- PURGING L3 RULES ON NETWORK {self.net.name} - {self.net.id}"
        )
        for tgt_net in self.tgt_nets:
            if tgt_net.is_vlan():
                self.purge_l3_fw_rules(tgt_net.nb_prefix, tgt_net)

        # TODO : DELETE L3RULES THAT MATCH OUR RULES NAMES CONVENTION AND AREN'T NEEDED ANYMORE

        # PURGE STUB
        self.logger.log_debug(f"----- REMOVE STUB ")
        self._remove_temp_stub_vlan()


# =======================================================================


class MerakiUpdater():

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__merakiDashboard = None
        self.__merakiDashboard_name = None

    def meraki_connect_to_dashboard(self, simulate: bool = False) -> None:
        self.meraki_connect_to_dashboard_by_name("GLOBAL", simulate)

    def meraki_connect_to_dashboard_by_name(
        self, name: str, simulate: bool = False
    ) -> None:
        self.__merakiDashboard = SopMerakiUtils.connect_by_name(name, simulate
        )
        self.__merakiDashboard_name = name
        self.log_info(f"Meraki connection established to dashboard {name}")

    def get_dashboard(self):
        if self.__merakiDashboard is not None:
            return self.__merakiDashboard
        raise Exception("Not connected")

    def get_dashboard_name(self):
        if self.__merakiDashboard_name is not None:
            return self.__merakiDashboard_name
        raise Exception("Not connected")

    def only_netbox_tags(self, tags: list[str]) -> list[str]:
        ret: list[str] = []
        for x in tags:
            if x.startswith("NETBOX_"):
                ret.append(x)
        ret.sort()
        return ret

    def only_non_netbox_tags(self, tags: list[str]) -> list[str]:
        ret: list[str] = []
        for x in tags:
            if not (x.startswith("NETBOX_")):
                ret.append(x)
        ret.sort()
        return ret

    def _vpn_enable_disable_prefix(
        self, nbp: Prefix, mvh: MerakiVPNHubs, details: bool = False
    ):
        """Enables or disables the AutoVPN SDWAN participation for a prefix

        Warning :
        - only active/noncompliant/decomissionning prefixes will be pushed
        - other prefixes will be VPN disabled forcibly
        """

        if details:
            self.log_debug(f"__vpn_enable_disable_prefix '{nbp.prefix}' =========")
        meraki_visible = SopUtils.default_if_none(
            nbp.custom_field_data.get("meraki_visible"), True
        )
        if not meraki_visible:
            if details:
                self.log_debug(
                    f"__vpn_enable_disable_prefix skipping '{nbp.prefix}' : NOT MERAKI VISIBLE ========="
                )
            return
        forced_off = False
        mand = nbp.custom_field_data.get("sdw_vpn_enable")
        if nbp.status not in ["active", "noncompliant", "decommissioning"]:
            forced_off = True
            mand = "vpnoff"
        if details:
            self.log_debug(
                f"__vpn_enable_disable_prefix '{nbp.prefix}' computed state : {mand} ========="
            )
        if mand is None:
            return
        if mand == "leave":
            return
        nets = mvh.get_site_to_site_nets()
        if details:
            self.log_debug(
                f"__vpn_enable_disable_prefix '{nbp.prefix}' nets = {nets} ========="
            )
        # Prepare storage for our info, if found
        n: MerakiS2SInfo = None
        z: MerakiS2SSubnet = None
        # Loop on potentially several meraki networks with appliances
        for net in nets:
            if net.mode == "none":
                # can happen when we have multiple networks with appliances
                continue
            if details:
                self.log_debug(
                    f"__vpn_enable_disable_prefix '{nbp.prefix}' nets loop for {net} ========="
                )
            if net.bound:
                if details:
                    self.log_warning(
                        f"========= CANNOT ENABLE/DISABLE VLANS ON TEMPLATIZED NETWORK (for prefix: '{nbp.prefix}') ========="
                    )
                continue
            # Loop on their subnets to find the one we're looking for
            for y in net._subnets:
                if y.cidr == f"{nbp.prefix}":
                    z = y
                    n = net
                    break
            if z is not None:
                break
        if z is None:
            if nbp.status not in ["retired", "reserved"]:
                self.log_warning(
                    f"Prefix {nbp.prefix} not found on site {nbp.scope.name}."
                )
            return
        upd = False
        # print(f"OLD mand:{mand} - z.vpn:{z.vpn}")
        if mand == "vpnon" and not (z.vpn):
            z.vpn = True
            upd = True
            self.log_success(f"Enabling VPN for {nbp.prefix} on site {nbp.scope.name}")
        elif mand == "vpnoff" and z.vpn:
            z.vpn = False
            upd = True
            self.log_success(f"Disabling VPN for {nbp.prefix} on site {nbp.scope.name}")
            if forced_off:
                self.log_warning(
                    f"==== FORCIBLY DISABLING PREVIOUSLY ENABLED VPN for {nbp.prefix} on site {nbp.scope.name}"
                )
        if upd:
            self.get_dashboard().appliance.updateNetworkApplianceVpnSiteToSiteVpn(
                n.id,
                mode=n.mode,
                hubs=n.get_meraki_hubs_list(),
                subnets=n.get_meraki_subnets_list(),
            )

    def _vpn_enable_disable_site(
        self, nbs: Site, mvh: MerakiVPNHubs, details: bool = False
    ):
        for nbp in Prefix.objects.filter(site=nbs):
            self._vpn_enable_disable_prefix(nbp, mvh, details)

    def _vpnhub_enforce_site(
        self, nbs: Site, mvh: MerakiVPNHubs, details: bool = False
    ):
        """Pushes the hub settings (order+default route) for a site"""

        # Extract values from netbox
        dflt: bool = False
        sho: str = ""
        try:
            si = nbs.sopinfra
            d = si.hub_default_route_setting
            dflt = d is not None and d.strip() == "true"
            sho = si.hub_order_setting
        except dcim.models.sites.Site.sopinfra.RelatedObjectDoesNotExist:
            si = None
        # Sanitize before use
        if sho is None:
            sho = ""

        # Build target
        target = []
        for x in sho.split(","):
            target.append({"hubId": x, "useDefaultRoute": dflt})
        # See if the target is good
        nets = mvh.get_all_nets()
        for net in nets:
            if net.bound:
                if details:
                    self.log_info(
                        f"========= CANNOT VPN ENABLE/DISABLE VLANS ON TEMPLATIZED NETWORK {net.name} ========="
                    )
                continue
            # we can have several meraki nets on a netbox net -> we need to build a target for each of those
            hasnets = len(net.get_meraki_subnets_list()) > 0
            if net.mode == "none":
                if hasnets:
                    # SHould never happen !
                    self.log_failure(
                        f"Appliance in org {net.orgId} and net {net.id} (in netbox net {nbs.name}) has nets but mode is NONE !"
                    )
                continue
            elif net.mode == "hub":
                self.log_warning(
                    f"Ignoring -> HUB MODE <- appliance in org {net.orgId} and net {net.id} (in netbox net {nbs.name})."
                )
                continue
            upd = False
            if hasnets:
                hl = net.get_meraki_hubs_list()
                if not (SopUtils.deep_equals_json(hl, target)):
                    self.log_success(
                        f"Changing hub list for {nbs.name} (org:{net.orgId}/net:{net.id})."
                    )
                    net._hubs = []
                    for y in target:
                        net._hubs.append(MerakiS2SHub(y))
                    upd = True
            else:
                if not ("none" == net.mode):
                    self.log_success(
                        f"Clearing hub list for {nbs.name} (org:{net.orgId}/net:{net.id})."
                    )
                    net.mode = "none"
                    net._hubs = []
                    net._subnets = []
                    upd = True
            if upd:
                self.get_dashboard().appliance.updateNetworkApplianceVpnSiteToSiteVpn(
                    net.id,
                    mode=net.mode,
                    hubs=net.get_meraki_hubs_list(),
                    subnets=net.get_meraki_subnets_list(),
                )

    def vpnhub_enforce_all_sites(self, refresh: bool = True):
        """Enforces the HUB order and default routes for all sites

        Only ['staging','starting','active','decommissioning'] will be handled !
        Parameters
        ----------
            expiry
        """
        if refresh:
            self._update_netbox_sites_hubs()
        flt = Q(status__in=["staging", "starting", "active", "decommissioning"])
        lst = Site.objects.filter(flt)
        for s in lst:
            self.vpnhub_enforce_site(s, -1)

    def patch_meraki_site_networks(
        self,
        tgt_nets: list[TargetNetwork],
        siteName,
        all_net_mer: list[MerakiNetwork],
        details: bool = False,
    ):
        for net in all_net_mer:
            msu = MerakiSiteUpdater(
                self.get_dashboard(), tgt_nets, siteName, net, self, details
            )
            msu.patch_one_meraki_site_network()

    def _switches_push_stp(self, nbs: Site, details: bool = False):

        if details:
            self.log_debug(f"_switches_push_stp '{nbs}' =========")

        # préparer une liste des networks meraki
        nets: set[str] = set()

        # préparer une liste des prios
        net_prios: dict[str, set[int]] = dict()

        # lister les switches du site
        net_switchs_upd: dict[str, dict[int, list[str]]] = dict()
        sws = (
            nbs.devices.exclude(sopdevicesetting=None)
            .exclude(sopdevicesetting__switch_template=None)
            .exclude(meraki_device=None)
            .filter(meraki_device__stack=None)
            .exclude(meraki_device__meraki_network__bound_to_template=True)
            .annotate(
                modul=Mod("sopdevicesetting__switch_template__stp_prio", 4096)
            )
            .filter(modul=0)
        )
        for sw in sws:
            prio = sw.sopdevicesetting.switch_template.stp_prio
            mnet = sw.meraki_device.meraki_network.meraki_id
            nets.add(mnet)
            prios = net_prios.get(mnet, set())
            prios.add(prio)
            net_prios[mnet] = prios
            switchs_upd = net_switchs_upd.get(mnet, dict())
            ex = switchs_upd.get(prio, list())
            ex.append(sw.serial)
            switchs_upd[prio] = ex
            net_switchs_upd[mnet] = switchs_upd

        # lister les stacks du site
        net_stacks_upd: dict[str, dict[int, list[str]]] = dict()
        stsnets = nbs.meraki_nets.exclude(switch_stacks=None).exclude(
            bound_to_template=True
        )
        for stsnet in stsnets:
            mnet = stsnet.meraki_id
            for sts in stsnet.switch_stacks.all():
                lst = sts.meraki_devices.exclude(netbox_device=None).values_list(
                    "netbox_device__id", flat=True
                )
                if len(lst)==0:
                    self.log_failure(f"Cannot configure stack {sts.nom} on network {stsnet.nom} without related netbox devices")
                    return False
                nets.add(mnet)
                req_prio = (
                    Device.objects.filter(pk__in=lst)
                    .exclude(sopdevicesetting=None)
                    .exclude(sopdevicesetting__switch_template=None)
                    .annotate(
                        modul=Mod("sopdevicesetting__switch_template__stp_prio", 4096)
                    )
                    .filter(modul=0)
                    .annotate(
                        min_prio=Min("sopdevicesetting__switch_template__stp_prio")
                    )
                    .values_list("min_prio", flat=True)
                )
                if not req_prio.exists():
                    self.log_failure(f"Cannot configure stack {sts.nom} on network {stsnet.nom} without STP configuration")
                    return False
                prio=req_prio[0]
                prios = net_prios.get(mnet, set())
                prios.add(prio)
                net_prios[mnet] = prios
                stacks_upd = net_stacks_upd.get(mnet, dict())
                ex = stacks_upd.get(prio, list())
                ex.append(sts.meraki_id)
                stacks_upd[prio] = ex
                net_stacks_upd[mnet] = stacks_upd
                
        # boucler sur les networks meraki
        for mnet in nets:
            # grouper par prio dans un dict
            stpbp = list()
            for p in net_prios[mnet]:
                pd = dict()
                if mnet in net_switchs_upd.keys():
                    switchs_upd = net_switchs_upd[mnet]
                    if p in switchs_upd.keys():
                        pd["switches"] = switchs_upd.get(p)
                if mnet in net_stacks_upd.keys():
                    stacks_upd = net_stacks_upd[mnet]
                    if p in stacks_upd.keys():
                        pd["stacks"] = stacks_upd.get(p)
                pd["stpPriority"] = p
                stpbp.append(pd)

            # Récup params actuels et comparer
            curr = self.get_dashboard().switch.getNetworkSwitchStp(mnet)
            tgt = {"rstpEnabled": True, "stpBridgePriority": stpbp}
            if SopUtils.deep_equals_json_ic(tgt, curr):
                self.log_info(
                    f"Spanning settings for [{mnet}] are correct {tgt=}, skipping update."
                )
            else:
                if details: 
                    self.log_debug(
                        f"Spanning settings for [{mnet}] are different {curr=} VS {tgt=}"
                    )
                # passer l'appel
                self.get_dashboard().switch.updateNetworkSwitchStp(
                    mnet, rstpEnabled=True, stpBridgePriority=stpbp
                )
                self.log_success(f"Updated spanning tree for [{mnet}] : {tgt=}")

    def _switches_push_igmp(self, nbs: Site, details: bool = False):
        if details:
            self.log_debug(f"_switches_push_igmp '{nbs}' =========")
        # Boucler sur les networks meraki non liés à des templates
        defaultSettings = {
            "igmpSnoopingEnabled": True,
            "floodUnknownMulticastTrafficEnabled": True,
        }
        overrides = []
        mnets = SopMerakiNet.objects.filter(site=nbs, bound_to_template=False, devices__ptype="switch").distinct()
        for mnet in mnets:
            mid = mnet.meraki_id
            # Récup params actuels et comparer
            curr = self.get_dashboard().switch.getNetworkSwitchRoutingMulticast(mid)
            tgt = {"defaultSettings": defaultSettings, "overrides": overrides}
            if SopUtils.deep_equals_json_ic(tgt, curr):
                self.log_info(
                    f"IGMP settings for [{mnet}] are correct, skipping update."
                )
            else:
                if details: 
                    self.log_debug(
                        f"IGMP settings for [{mnet}] are different {curr=} VS {tgt=}"
                    )
                # Procéder à l'update
                self.get_dashboard().switch.updateNetworkSwitchRoutingMulticast(
                    mid, defaultSettings=defaultSettings, overrides=overrides
                )
                self.log_success(
                    f"Updated IGMP settings for [{mnet}] to {defaultSettings=} and {overrides=}"
                )

    def _switches_push_qos_rules(self, nbs: Site, details: bool = False):
        if details:
            self.log_debug(f"_switches_push_qos_rules '{nbs}' =========")
        tgt: list[dict] = [
            {
                "vlan": 300,
                "protocol": "ANY",
                "srcPort": None,
                "dstPort": None,
                "dscp": -1,
            },
            {
                "vlan": 56,
                "protocol": "ANY",
                "srcPort": None,
                "dstPort": None,
                "dscp": 34,
            },
        ]
        # Boucler sur les networks meraki non liés
        mnets = SopMerakiNet.objects.filter(site=nbs, bound_to_template=False, devices__ptype="switch").distinct()
        for mnet in mnets:
            mid = mnet.meraki_id
            changed = False
            # Récup params actuels et comparer
            curr = self.get_dashboard().switch.getNetworkSwitchQosRules(mid)
            lst_rem = list()
            for x in curr:
                curr_id = x.pop("id")
                found = False
                for y in tgt:
                    if SopUtils.deep_equals_json_ic(y, x):
                        # Found the current settings in our target settings
                        found = True
                        # won't need to create it afterwards
                        tgt.remove(y)
                        # no need to continue searching for it
                        break
                if found:
                    # Keep this setting and move to the next
                    continue
                # This setting wasn't found in our settings
                # Add it for removal
                if details:
                    self.log_debug(f"could not find {x=} in {tgt=}")
                lst_rem.append(curr_id)
            # Now add all the settings that weren't found
            for y in tgt:
                changed = True
                if details:
                    self.log_debug(f"Adding QOS Rules in [{mnet}] : {y}")
                self.get_dashboard().switch.createNetworkSwitchQosRule(mid, **y)
            # Now remove all those that we didn't want
            for x in lst_rem:
                changed = True
                if details:
                    self.log_debug(f"Deleting QOS Rules in [{mnet}] : {x}")
                self.get_dashboard().switch.deleteNetworkSwitchQosRule(mid, x)
            if changed:
                self.log_success(f"Updated QOS Rules for [{mnet}] !")
            elif details:
                self.log_debug(f"No change in QOS Rules for [{mnet}]")

    # ============================================================================================

    def _get_all_mer_nets_for_site(
        self, site: Site, device_types: list[str], *args, **kwargs
    ) -> MerakiNets:
        mns = MerakiNets()
        # Currently supported device types filter+fetch_hubs
        devtypes: list[str] = []
        for t in [
            MerakiConstants.dev_type_appliance,
            MerakiConstants.dev_type_wireless,
        ]:
            if t in device_types and t not in devtypes:
                devtypes.append(t)

        # Meraki org/net loop
        # TODO : refactor : on est sur un seul site, ça ne sert plus à rien
        self.log_debug(f"_get_all_mer_nets_for_site - Meraki net loop")
        net: SopMerakiNet
        for net in site.meraki_nets.all():
            self.log_debug(f"_get_all_mer_nets_for_site - handling {net.nom}")
            # Fetch network info from Meraki
            mn: MerakiNetwork = MerakiNetwork(
                net.org.meraki_id,
                net.meraki_id,
                net.nom,
                net.bound_to_template,
                net.timezone,
                net.meraki_tags,
            )
            mns.add_net(mn, site.slug)
            

        # TODO : quand le claim sera dans netbox, on pourra éliminer l'appel à getOrganizationDevices
        if devtypes is not None and len(devtypes) > 0:
            # ["appliance","camera","cellularGateway","secureConnect","sensor","switch","systemsManager","wireless"]
            self.log_debug(f"_get_all_mer_nets_for_site - getOrganizationDevices")
            devices = self.get_dashboard().organizations.getOrganizationDevices(
                organizationId=net.org.meraki_id,
                productTypes=devtypes,
                networkIds=mns.get_net_ids(),
            )
            for dev in devices:
                if mns.has_net_id(dev["networkId"]):
                    if (x := dev.get("productType")) is not None:
                        if x == MerakiConstants.dev_type_appliance:
                            mn: MerakiNetwork = mns.get_net(dev["networkId"])
                            mn.add_appliance(dev["serial"], net.org.meraki_id)
                            self.log_debug(
                                f"_get_all_mer_nets_for_site - getNetworkApplianceSecurityIntrusion"
                            )
                            x: (
                                dict
                            ) = self.get_dashboard().appliance.getNetworkApplianceSecurityIntrusion(
                                mn.id
                            )
                            # self.log_debug(f"netappids {x}")
                            mn._ids_mode = x.get("mode")
                            self.log_debug(
                                f"_get_all_mer_nets_for_site - getNetworkApplianceSecurityMalware"
                            )
                            x: (
                                dict
                            ) = self.get_dashboard().appliance.getNetworkApplianceSecurityMalware(
                                mn.id
                            )
                            # self.log_debug(f"netappamp {x}")
                            mn._amp_mode = x.get("mode")
                            self.log_debug(
                                f"_get_all_mer_nets_for_site - getNetworkApplianceContentFiltering"
                            )
                            x: (
                                dict
                            ) = self.get_dashboard().appliance.getNetworkApplianceContentFiltering(
                                mn.id
                            )
                            # self.log_debug(f"netctfilter {x}")
                            mn._ctflt = x
                            # self.log_debug(f"built {mn}")
                        elif x == MerakiConstants.dev_type_wireless:
                            mns.get_net(dev["networkId"]).add_access_point(dev)
        return mns

    # ============================================================================================

    def _fetch_hubs(self, mns: MerakiNets, *args, **kwargs) -> MerakiVPNHubs:
        mvh = MerakiVPNHubs()
        mn: MerakiNetwork = None
        for mn in mns.get_appliance_nets():
            # Fetch network info from Meraki
            self.log_debug(f"Fetching hub info for site {mn.name}...")
            mvh.add_net(
                MerakiS2SInfo(
                    mn.orgId,
                    mn.id,
                    mn.name,
                    mn.bound,
                    self.get_dashboard().appliance.getNetworkApplianceVpnSiteToSiteVpn(
                        mn.id
                    ),
                )
            )
        return mvh

    def enforce_one_netbox_site(self, site: Site, details: bool = False):

        # GET MERAKI NETWORKS FOR NETBOX SITE
        mns: MerakiNets = None
        mns = self._get_all_mer_nets_for_site(site, ("appliance"))
        if details and True:
            self.log_debug(f"MNS => {mns}")
        if len(mns.nets.keys()) == 0:
            self.log_warning(
                f"Impossible to match Meraki networks to this site slug '{site.slug}' !"
            )
            self.log_warning(
                f"Please verify both your slug (lower case match) and your Meraki network naming (matches {SopRegExps.meraki_sitename_str})."
            )
            return
        org_ids: list[str] = list()
        si = site.sopinfra

        # PATCH SITE
        if details:
            self.log_info(f"==== SITE:{site.name} >>>> PATCH SITE")
        for mn in mns.nets.values():
            self.log_debug(
                f"check mn {mn.name}/{mn.id} : has_appliances:{mn.has_appliances}/has_access_points{mn.has_access_points}"
            )

            # Handle appliance networks
            if mn.has_appliances and not (mn.bound):
                # Save Org ID for later
                if details:
                    self.log_debug(f"{mn.appliances=}")
                for v in mn.appliances.values():
                    if v not in org_ids:
                        if details:
                            self.log_debug(f"append {v=}")
                        org_ids.append(v)
                # Reset AMP/IDS/ContentFiltering
                # TODO move that to scheduled task
                if not ("disabled" == mn._amp_mode):
                    self.log_warning(
                        f"Resetting {mn.name}/{mn.id} AMP mode {mn._amp_mode} to 'disabled'"
                    )
                    self.get_dashboard().appliance.updateNetworkApplianceSecurityMalware(
                        mn.id, mode="disabled"
                    )
                if not ("disabled" == mn._ids_mode):
                    self.log_warning(
                        f"Resetting {mn.name}/{mn.id} IDS mode {mn._amp_mode} to 'disabled'"
                    )
                    self.get_dashboard().appliance.updateNetworkApplianceSecurityIntrusion(
                        mn.id, mode="disabled"
                    )
                if mn._ctflt is not None:
                    fix = False
                    if len(mn._ctflt.get("allowedUrlPatterns", [])) > 0:
                        fix = True
                    elif len(mn._ctflt.get("blockedUrlPatterns", [])) > 0:
                        fix = True
                    elif len(mn._ctflt.get("blockedUrlCategories", [])) > 0:
                        fix = True
                    if fix:
                        self.log_warning(
                            f"Resetting {mn.name}/{mn.id} Content Filtering {mn._ctflt} to empty lists"
                        )
                        self.get_dashboard().appliance.updateNetworkApplianceContentFiltering(
                            mn.id,
                            allowedUrlPatterns=[],
                            blockedUrlPatterns=[],
                            blockedUrlCategories=[],
                            urlCategoryListSize="topSites",
                        )
                # Check Prisma Access VPN conf
                if si is not None and si.enabled is not None:
                    # We need to act
                    self.log_debug(
                        f"enforce_one_netbox_site - prisma should be {si.enabled=} / current tags {mn.tags=}"
                    )
                    if si.enabled == "true":
                        fix_new = mn.add_tag(f"{si.endpoint.name}")
                        fix_old = mn.del_tag(f"AUTO-{mn.id}")
                        if fix_new or fix_old:
                            update_meraki: dict = {"tags": mn.tags}
                            if details:
                                self.log_debug(f"{update_meraki=}")
                            d = self.get_dashboard().networks.updateNetwork(
                                mn.id, **update_meraki
                            )
                            self.log_success(
                                f"fixed prisma network tags - new tags {d.get('tags')}"
                            )
                    elif si.enabled == "false":
                        if mn.del_tag(f"{si.endpoint.name}"):
                            if details:
                                self.log_debug(
                                    f"remove new prisma tag '{si.endpoint.name}'"
                                )
                            update_meraki: dict = {"tags": mn.tags}
                            if details:
                                self.log_debug(f"{update_meraki=}")
                            d = self.get_dashboard().networks.updateNetwork(
                                mn.id, **update_meraki
                            )
                            self.log_success(
                                f"fixed prisma network tags - new tags {d.get('tags')}"
                            )
                        pass
                    elif si.enabled == "unknown" or si.enabled.strip() == "":
                        self.log_debug(f"Prisma unknown -> nothing to do !")
                        pass
                    else:
                        raise Exception(
                            f"Unkwnown sopinfra enabled value {si.enabled=} !"
                        )

        # PATCH ORG FOR PRISMA VPN
        if details:
            self.log_info(f"==== SITE:{site.name} >>>> PATCH ORG")
        if si is not None:
            if si.endpoint is not None:
                if details:
                    self.log_debug(
                        f"enforce_one_netbox_site {site.name} - found Prisma Access conf"
                    )
                self.log_debug(f"enforce_one_netbox_site {site.name} - {org_ids=}")
                for org_id in org_ids:
                    dict_peers = self.get_dashboard().appliance.getOrganizationApplianceVpnThirdPartyVPNPeers(
                        org_id
                    )
                    current_peers = dict_peers.get("peers")
                    self.log_debug(
                        f"enforce_one_netbox_site {site.name} - {org_id=} - {current_peers=}"
                    )
                    found = False
                    for p in current_peers:
                        if si.endpoint.name == p.get("name"):
                            found = True
                            break
                    if found:
                        self.log_debug(
                            f"enforce_one_netbox_site {site.name} - {org_id=} - Peer {si.endpoint.name} found -> skipping"
                        )
                    else:
                        peer = {
                            "name": si.endpoint.name,
                            "ikeVersion": "2",
                            "secret": si.endpoint.psk,
                            "privateSubnets": ["0.0.0.0/0"],
                            "ipsecPolicies": {
                                "ikeCipherAlgo": ["aes256"],
                                "ikeAuthAlgo": ["sha256"],
                                "ikePrfAlgo": ["default"],
                                "ikeDiffieHellmanGroup": ["group2"],
                                "ikeLifetime": 28800,
                                "childCipherAlgo": ["aes256"],
                                "childAuthAlgo": ["sha256"],
                                "childPfsGroup": ["group2"],
                                "childLifetime": 10800,
                            },
                            "networkTags": [si.endpoint.name],
                            "localId": si.endpoint.local_id,
                            "remoteId": si.endpoint.remote_id,
                            "publicIp": si.endpoint.peer_ip,
                        }
                        current_peers.append(peer)
                        dict_peers = {"peers": current_peers}
                        self.log_debug(
                            f"enforce_one_netbox_site {site.name} - {org_id=} - Pushing {dict_peers} "
                        )
                        self.get_dashboard().appliance.updateOrganizationApplianceVpnThirdPartyVPNPeers(
                            org_id, peers=current_peers
                        )

        # PATCH NETWORKS
        if details:
            self.log_info(f"==== SITE:{site.name} >>>> PATCH NETWORKS")
        from scripts.DHCPUtils import TargetNetwork

        tgt_nets: list[TargetNetwork] = TargetNetwork.netbox_get_tagged_prefixes(
            self, site, details
        )
        self.patch_meraki_site_networks(
            tgt_nets, f"site_id={site}", mns.get_appliance_nets(), details
        )

        # FETCH HUBS (DEFERRED TO HAVE CURRENT REPRESENTATION)
        mvh: MerakiVPNHubs = None
        mvh = self._fetch_hubs(mns)
        if details and True:
            self.log_debug(f"MVH => {mvh}")

        # PATCH HUBS
        if details:
            self.log_info(f"==== SITE:{site.name} >>>> PATCH HUBS")
        self._vpnhub_enforce_site(site, mvh, details)

        # PATCH VPN
        if details:
            self.log_info(f"==== SITE:{site.name} >>>> PATCH VPN")
        self._vpn_enable_disable_site(site, mvh, details)

        # PATCH STP
        if details:
            self.log_info(f"==== SITE:{site.name} >>>> PATCH STP")
        self._switches_push_stp(site, details)

        # PATCH IGMP
        if details:
            self.log_info(f"==== SITE:{site.name} >>>> PATCH IGMP")
        self._switches_push_igmp(site, details)

        # PATCH QOS RULES
        if details:
            self.log_info(f"==== SITE:{site.name} >>>> PATCH QOS")
        self._switches_push_qos_rules(site, details)


# =======================================================================

class MerakiToolMixin(MerakiUpdater, SopBaseScriptMixin):
    pass


# =======================================================================


def prepare_create_vlan(vlan):
    posargs = {"networkId": vlan["networkId"], "id": vlan["id"], "name": vlan["name"]}
    kwargs = {k: v for k, v in vlan.items()}
    del kwargs["networkId"]
    del kwargs["id"]
    del kwargs["name"]
    if "ipv6" in kwargs:
        del kwargs["ipv6"]
    posargs.update(kwargs)
    return posargs


def prepare_put_vlan(vlan):
    posargs = {"networkId": vlan["networkId"], "vlanId": vlan["id"]}
    kwargs = {k: v for k, v in vlan.items()}
    del kwargs["networkId"]
    del kwargs["id"]
    if "ipv6" in kwargs:
        del kwargs["ipv6"]
    posargs.update(kwargs)
    return posargs


def prepare_create_route(vlan):
    posargs = {
        "networkId": vlan["networkId"],
    }
    kwargs = {k: v for k, v in vlan.items()}
    del kwargs["networkId"]
    if "gatewayVlanId" in kwargs:
        del kwargs["gatewayVlanId"]
    posargs.update(kwargs)
    return posargs


def prepare_put_route(vlan):
    posargs = {"networkId": vlan["networkId"], "staticRouteId": vlan["id"]}
    kwargs = {k: v for k, v in vlan.items()}
    del kwargs["networkId"]
    del kwargs["id"]
    if "gatewayVlanId" in kwargs:
        del kwargs["gatewayVlanId"]
    posargs.update(kwargs)
    return posargs
