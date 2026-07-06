import time
import meraki  
import netaddr
import json

from django.utils.text import slugify
from django.db.models import Min
from django.db.models.functions.math import Mod

from sop_infra.models.infra import SopInfra
from sop_infra.utils.meraki_early_access import EarlyAccessAppliance
from sop_infra.utils.meraki_utils import SopMerakiUtils
from sop_infra.utils.DHCPUtils import TargetPrefix
from sop_infra.utils.umbrella_utils import SopUmbrellaUtils
from utilities.exceptions import AbortScript

import dcim.models

from ipam.models import Prefix
from dcim.models import Site, Device

from sop_infra.utils.meraki_objects import *
from sop_infra.models import SopMerakiNet, SopSwitchTemplate, SopDeviceSetting
from sop_utils.misc import SopUtils
from sop_utils.regexps import SopRegExps
from sop_infra.utils.mixins import JobRunnerLogMixin, SopBaseScriptMixin
from sop_infra.models.sopmeraki import SopMerakiOrg

from meraki.exceptions import APIError

# =======================================================================


class MerakiNetworkUpdater:

    stub_vlan_id: int = 3998

    def __init__(
        self,
        dash: meraki.DashboardAPI,
        site:Site,
        net: MerakiNetwork,
        logger,
        details: bool = False,
    ):
        self.__merakiDashboard = dash
        self.__logger = logger
        self.site:Site = site
        self.siteName:str=f"site_id={site}"
        self.net:MerakiNetwork = net
        self.details = details
        self.site_vlans: list[dict] = []
        self.site_routes: list[dict] = []
        self.site_gps: list[dict] = []
        self.tgt_nets: list[TargetPrefix] = TargetPrefix.netbox_get_tagged_prefixes(
            self.__logger, site, details
        )

    def get_dashboard(self):
        if self.__merakiDashboard is not None:
            return self.__merakiDashboard
        raise Exception("Not connected")

    def _refresh_cache(self):
        # ANALYZE VLANS/ROUTES/POLICIES AND CACHE THEM
        self.__logger.log_debug(
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
        self.__logger.log_debug(
            f"   Analyze done --> found {len(self.site_vlans)} vlans, {len(self.site_routes)} routes and {len(self.site_gps)} group policies "
        )

    #---------------------------------------
    #region VLANS state book keeping

    def _create_meraki_vlan(self, vlan, log_inf: str):
        try:
            self.get_dashboard().appliance.createNetworkApplianceVlan(
                **SopMerakiUtils.prepare_create_vlan(vlan)
            )  # APIError
            self.site_vlans.append(vlan)
        except Exception as err:
            self.__logger.log_failure(
                f"   {log_inf} ;  VLAN : {vlan} \n {err=}, {type(err)=}"
            )
            raise err
        else:
            self.__logger.log_success(f"   {log_inf}")
            if self.details:
                self.__logger.log_success(f"   Added VLAN {vlan}")

    def _update_meraki_vlan(self, vlan, log_inf: str):
        try:
            self.get_dashboard().appliance.updateNetworkApplianceVlan(
                **SopMerakiUtils.prepare_put_vlan(vlan)
            )  # APIError
            index = self.__find_meraki_vlan(vlan.get("id", -1))
            self.site_vlans[index]=vlan
        except Exception as err:
            self.__logger.log_failure(
                f"   {log_inf} ;  VLAN : {vlan} \n {err=}, {type(err)=}"
            )
            raise err
        else:
            self.__logger.log_success(f"   {log_inf}")
            if self.details:
                self.__logger.log_success(f"   Updated VLAN {vlan}")

    def _del_meraki_vlan(self, vlan, log_inf: str):
        if (
            len(self.site_vlans) == 1
            and vlan.get("id") == MerakiNetworkUpdater.stub_vlan_id
        ):
            self.__logger.log_debug(
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
            self.__logger.log_failure(
                f"   {log_inf} ;  VLAN : {vlan} \n {err=}, {type(err)=}"
            )
            raise err
        else:
            self.__logger.log_success(f"   {log_inf}")
            if self.details:
                self.__logger.log_success(f"   Removed VLAN {vlan}")

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
        vid = vlan.get("id", MerakiNetworkUpdater.stub_vlan_id)
        return vid == self.site_vlans[0].get("id")

    def _push_temp_stub_vlan(self):
        self._create_meraki_vlan(
            self.__build_stub_vlan(), "CREATE STUB AS A WORKAROUND"
        )

    def _remove_temp_stub_vlan(self):
        index = self.__find_meraki_vlan(MerakiNetworkUpdater.stub_vlan_id)
        if index >= 0 and len(self.site_vlans) > 1:
            self._del_meraki_vlan(self.__build_stub_vlan(), "REMOVE WORKAROUND STUB")

    def __build_stub_vlan(self):
        return {
            "id": MerakiNetworkUpdater.stub_vlan_id,
            "networkId": self.net.id,
            "subnet": "127.98.0.0/24",
            "name": "netbox_stub",
            "applianceIp": f"127.98.0.254",
        }


    #endregion 


    # ---------------------------------------
    #region  ROUTES state book keeping
    def _create_meraki_route(self, route, log_inf: str):
        try:
            self.get_dashboard().appliance.createNetworkApplianceStaticRoute(
                **SopMerakiUtils.prepare_create_route(route)
            )  # APIError
            self.site_routes.append(route)
        except Exception as err:
            self.__logger.log_failure(
                f"   {log_inf} ;  ROUTE : {route} \n {err=}, {type(err)=}"
            )
            raise err
        else:
            self.__logger.log_success(f"   {log_inf}")
            if self.details:
                self.__logger.log_success(f"   Added ROUTE {route}")

    def _update_meraki_route(self, route, log_inf: str):
        try:
            self.get_dashboard().appliance.updateNetworkApplianceStaticRoute(
                **SopMerakiUtils.prepare_put_route(route)
            )  # APIError
            index = self.__find_meraki_route(route.get("subnet", ""))
            self.site_routes[index]=route
        except Exception as err:
            self.__logger.log_failure(
                f"   {log_inf} ;  ROUTE : {route} \n {err=}, {type(err)=}"
            )
            raise err
        else:
            self.__logger.log_success(f"   {log_inf}")
            if self.details:
                self.__logger.log_success(f"   Updated ROUTE {route}")

    def _del_meraki_route(self, route, log_inf: str):
        try:
            self.get_dashboard().appliance.deleteNetworkApplianceStaticRoute(
                self.net.id, route.get("id")
            )
            self.__remove_meraki_route(route.get("subnet", ""))
        except Exception as err:
            self.__logger.log_failure(
                f"   {log_inf}; Route : {route} \n {err=}, {type(err)=}"
            )
            self.raiseError = True
        else:
            self.__logger.log_success(f"   {log_inf}")
            if self.details:
                self.__logger.log_success(f"   Removed route : {route}")

    def __find_meraki_route(self, subnet: str):
        for index in range(len(self.site_routes)):
            if subnet == self.site_routes[index].get("subnet"):
                return index
        return -1
    
    def __remove_meraki_route(self, subnet: str):
        index = self.__find_meraki_route(subnet)
        if index >= 0:
            self.site_routes.pop(index)

    #endregion


    # ---------------------------------------
    # region update logic
    def _update_or_create_meraki_network(
        self,
        tgt_net: TargetPrefix,
    ):
        if self.details:
            self.__logger.log_debug(f"handling {tgt_net} ")
        if tgt_net.get_nb_prefix().status in ["retired", "reserved"]:
            self.__logger.log_debug(
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
                    self.site_vlans,
                )
            )
            # Check logique (de programmation, ne devrait pas arriver)
            if len(vlans) > 1:
                # Problem here : we cannot have twice the same vlan subnet on the same MX device !
                self.__logger.log_failure(
                    f"   Several VLANs found on Meraki site {self.net.name}/{self.net.id} for prefix '{tgt_net.prefix_str}'"
                )
                return
            # Check besoin de création
            elif len(vlans) == 0:
                # Not found -> need to create it
                tgt = tgt_net.create_target_meraki_vlan(
                    tgt_net.nb_prefix.vlan.vid,
                    self.net.id,
                    tgt_net.prefix_str,
                    tgt_net.get_net_name(),
                    f"{netaddr.IPAddress(tgt_net.nb_prefix.prefix.last-1)}", 
                    self.net, 
                    self.__logger,
                )
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
                # Found a single one, let's update
                vlan = vlans[0]
                # Clear potential failure causes
                if "ipv6" in vlan:
                    del vlan["ipv6"]
                # Build target
                tgt = tgt_net.adjust_target_meraki_vlan(vlan, self.net, self.__logger)
                # ranges are not sorted -> need to be sorted before being serialized
                if tgt.get("reservedIpRanges") is not None:
                    tgt["reservedIpRanges"].sort(key=(lambda x: x.get("start")))
                if vlan.get("reservedIpRanges") is not None:
                    vlan["reservedIpRanges"].sort(key=(lambda x: x.get("start")))
                if self.details:
                    import json
                    deep1 = json.dumps(tgt, sort_keys=True, indent=2)
                    deep2 = json.dumps(vlan, sort_keys=True, indent=2)
                    self.__logger.log_debug(
                        f"Compare {deep1==deep2}vs{SopUtils.deep_equals_json(tgt, vlan)} -> { deep1} to {deep2}"
                    )
                if SopUtils.deep_equals_json(tgt, vlan):
                    self.__logger.log_info(
                        f"   no change on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'"
                    )
                else:
                    self._update_meraki_vlan(
                        tgt,
                        f"   Meraki updateNetworkApplianceVlan on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'",
                    )
        elif tgt_net.is_route():
            # Correspondance NetBox prefix == Meraki vlan/staticroute (ex: 10.170.11.0/24)
            routes = list(
                filter(lambda v: tgt_net.prefix_str == v["subnet"], self.site_routes)
            )
            # Check logique (de programmation, ne devrait pas arriver)
            if len(routes) > 1:
                # Problem here : we cannot have twice the same route on the same MX device !
                self.__logger.log_failure(
                    f"   Several ROUTES found on Meraki site {self.net.name}/{self.net.id} for prefix '{tgt_net.prefix_str}'"
                )
                return
            # Check besoin de creation
            if do_create := (len(routes) == 0):
                # Not found -> need to create it
                route = {
                    "networkId": self.net.id,
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
            tgt = tgt_net.build_target_meraki_route(route, self.__logger)
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
                if self.details:
                    import json
                    deep1 = json.dumps(tgt, sort_keys=True, indent=2)
                    deep2 = json.dumps(route, sort_keys=True, indent=2)
                    self.__logger.log_debug(
                        f"Compare {deep1==deep2}vs{SopUtils.deep_equals_json(tgt, route)} -> { deep1} to {deep2}"
                    )
                if SopUtils.deep_equals_json(tgt, route):
                    self.__logger.log_info(
                        f"   no change on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'"
                    )
                else:
                    # site_to_sites=self.get_dashboard().appliance.getNetworkApplianceVpnSiteToSiteVpn(route['networkId'])
                    self._update_meraki_route(
                        tgt,
                        f"   Meraki updateNetworkApplianceStaticRoute on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'",
                    )
                    # self.get_dashboard().appliance.updateNetworkApplianceVpnSiteToSiteVpn(networkId=route['networkId'], **site_to_sites)
        else:
            self.__logger.log_failure(
                f"UPDATE/CREATE CODE ERROR : tgt_net is neither VLAN nor ROUTE {tgt_net}"
            )

    def purge_l3_fw_rules(self, nbp: Prefix, tgt_net: TargetPrefix) -> None:
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
                self.__logger.log_info(
                    f"   Delete ruleset '{rule_name}' on '{self.siteName}'"
                )
                self.get_dashboard().networks.deleteNetworkGroupPolicy(
                    self.net.id, r.get("groupPolicyId")
                )
                self.site_gps.remove(r)
            except Exception as err:
                self.__logger.log_failure(f"Failure detected : {err}")
                self.__logger.log_failure(
                    f"Current object :  {self.siteName}/{tgt_net.prefix_str} "
                )
                raise err

    def push_l3_fw_rules(self, nbp: Prefix, tgt_net: TargetPrefix) -> None:
        if self.details:
            self.__logger.log_debug(f"push_l3_fw_rules handling {tgt_net} ")
        if tgt_net.get_nb_prefix().status in ["retired", "reserved"]:
            if self.details:
                self.__logger.log_debug(
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
                # self.__logger.log_info(f" fas is none for {rule_name}")
            else:
                ol3r = fas.get("l3FirewallRules")
                if ol3r is None:
                    upd = True
                    # self.__logger.log_info(f" ol3r is none for {rule_name}")
                elif not (
                    SopUtils.deep_equals_json_ic(ol3r, tgt_net.gp.group_policy_list)
                ):
                    upd = True
                    if self.details:
                        self.__logger.log_debug(f" conf distincte :")
                        self.__logger.log_debug(
                            f" OLD : {json.dumps(ol3r, sort_keys=True, indent=2)}"
                        )
                        self.__logger.log_debug(
                            f" NEW : {json.dumps(tgt_net.gp.group_policy_list, sort_keys=True, indent=2)}"
                        )
            if upd:
                # PROBLEM IF WE HAVE TO UPDATE IN THE TEMPLATE -> HAS TO BE DONE MANUALY
                if self.net.bound:
                    self.__logger.log_failure(
                        f"CANNOT UPDATE L3 RULES ON TEMPLATIZED NETWORK '{self.siteName}' (for prefix: '{tgt_net.prefix_str}') ===> THIS MUST BE DONE MANUALY"
                    )
                    return
                # Update !
                try:
                    self.__logger.log_success(
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
                    self.__logger.log_failure(f"Failure detected : {err}")
                    self.__logger.log_failure(
                        f"Current object :  {self.siteName}/{tgt_net.prefix_str}\n -> {tgt_net.gp.group_policy_list}"
                    )
                    raise err
            # Pas sûr si c'est cause des templates ou du non commit ou ....
            if r.get("groupPolicyId") is not None:
                if self.details:
                    self.__logger.log_debug(
                        f"setting groupPolicyId to {r.get('groupPolicyId')} for {rule_name} on network {self.net.name}/{self.net.id}"
                    )
                tgt_net.gp.group_policy_id[self.net.id] = f"{r.get('groupPolicyId')}"

        else:
            # We did not find the rule ->  let's create it
            # PROBLEM WITH TEMPLATES -> HAS TO BE DONE MANUALY
            if self.net.bound:
                self.__logger.log_failure(
                    f"CANNOT CREATE L3 RULES ON TEMPLATIZED NETWORK '{self.siteName}' (for prefix: '{tgt_net.prefix_str}') ===> THIS MUST BE DONE MANUALY"
                )
                return
            # No FW rule or rule not found by name
            self.__logger.log_info(
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
                self.__logger.log_failure(f"Failure detected : {err}")
                self.__logger.log_failure(
                    f"Current object :  {self.siteName}/{tgt_net.prefix_str}\n -> {tgt_net.gp.group_policy_list}"
                )
                raise err
            # Check creation return
            if r is None or r.get("groupPolicyId") is None:
                self.__logger.log_failure(
                    f"PROBLEM WITH L3RULES CREATION ON NETWORK '{self.siteName}' (for prefix: '{tgt_net.prefix_str}') ===> THIS MUST BE LOOKED MANUALY"
                )
            else:
                if self.details:
                    self.__logger.log_debug(
                        f"setting groupPolicyId to {r.get('groupPolicyId')} for {rule_name} on network {self.net.name}/{self.net.id}"
                    )
                tgt_net.gp.group_policy_id[self.net.id] = f"{r.get('groupPolicyId')}"


    def patch_one_meraki_site_network(self):

        tgt_net: TargetPrefix

        # HANDLE THE CASE OF ROUTED VLAN 1
        self.__logger.log_debug(
            f"----- CHECKING FOR ROUTED VLAN 1 ON MERAKI NETWORK {self.net.name} - {self.net.id}"
        )
        rtone = False
        for tgt_net in self.tgt_nets:
            if tgt_net.vlan_id == 1 and tgt_net.is_route():
                if self.details:
                    self.__logger.log_debug(f" rtone for net {self.net.id} : {tgt_net}")
                rtone = True
                break
        lports = self.get_dashboard().appliance.getNetworkAppliancePorts(self.net.id)
        if self.details:
            self.__logger.log_debug(
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
                            self.__logger.log_debug(
                                f" found diff on port {num} between existing port {lport} and computed target {stg}"
                            )
                        self.get_dashboard().appliance.updateNetworkAppliancePort(
                            self.net.id, num, **stg
                        )
                        self.__logger.log_success(f"Updated appliance port {num} ")
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
                            self.__logger.log_debug(
                                f" found diff on port {num} between existing port {lport} and computed target {stg}"
                            )
                        self.get_dashboard().appliance.updateNetworkAppliancePort(
                            self.net.id, num, **stg
                        )
                        self.__logger.log_success(f"Updated appliance port {num} ")
                else:
                    raise AbortScript(
                        f"Meraki API changed and we have a MX port type that we didn't expect : {lport['type']} on port {lport['number']}"
                    )

        # ANALYZE VLANS/ROUTES/POLICIES AND CACHE THEM
        self._refresh_cache()

        # DELETE PREFIXES OF THE WRONG TYPE (ROUTES VS VLANS)
        self.__logger.log_debug(f'----- DELETING "WRONG" PREFIXES ')
        for tgt_net in self.tgt_nets:
            if self.details:
                self.__logger.log_debug(f"handling {tgt_net} ")
            if tgt_net.is_vlan():
                # Find the Meraki routes that exist for this subnet instead of vlans
                routes = list(
                    filter(
                        lambda v: tgt_net.prefix_str == v["subnet"], self.site_routes
                    )
                )
                # self.__logger.log_debug(f' is vlan {tgt_net} -> routes to remove = {routes}')
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
                # self.__logger.log_debug(f' is route {tgt_net} -> vlans to remove = {vlans}')
                for vlan in vlans:
                    self._del_meraki_vlan(
                        vlan,
                        f"   Meraki deleteNetworkApplianceVlan on site '{self.siteName}' for prefix: '{tgt_net.prefix_str}'",
                    )
            else:
                self.__logger.log_failure(
                    f"DELETE WRONG NETWORKS CODE ERROR : tgt_net is either VLAN or ROUTE {tgt_net}"
                )

        # DELETE PREFIXES THAT WERE RETIRED OR DO NOT EXIST IN NETBOX
        self.__logger.log_debug(
            f"----- DELETING RETIRED , RESERVED OR NON-EXISTENT PREFIXES "
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
        self.__logger.log_debug(
            f"----- PUSHING L3 RULES ON NETWORK {self.net.name} - {self.net.id}"
        )
        for tgt_net in self.tgt_nets:
            if tgt_net.is_vlan:
                self.push_l3_fw_rules(tgt_net.nb_prefix, tgt_net)

        # UPDATE EXISTING PREFIXES / CREATE NON-EXISTING ONES
        self.__logger.log_debug(f"----- UPDATING/CREATING PREFIXES ")
        tgt_net: TargetPrefix|None = None
        for tgt_net in self.tgt_nets:
            self._update_or_create_meraki_network(
                tgt_net
            )

        # DELETE L3RULES THAT HAVE AREN'T NEEDED ANYMORE ON THE EXISTING PREFIXES (RULES EMPTIED)
        self.__logger.log_debug(
            f"----- PURGING L3 RULES ON NETWORK {self.net.name} - {self.net.id}"
        )
        for tgt_net in self.tgt_nets:
            if tgt_net.is_vlan():
                self.purge_l3_fw_rules(tgt_net.nb_prefix, tgt_net)

        # TODO : DELETE L3RULES THAT MATCH OUR RULES NAMES CONVENTION AND AREN'T NEEDED ANYMORE

        # PURGE STUB
        self.__logger.log_debug(f"----- REMOVE STUB ")
        self._remove_temp_stub_vlan()
    
    #endregion

# =======================================================================



# =======================================================================
class NetboxSiteMerakiUpdater():

    def __init__(self, site:Site, logger, details:bool, simulate:bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__site:Site=site
        self.__logger=logger
        self.__details=details
        self.__simulate=simulate
        self.__merakiDashboard = None
        self.__smorg:SopMerakiOrg=SopMerakiUtils.get_site_meraki_org(self.__site)

    #region dashboard  
    def __meraki_connect(self) -> None:
        if self.__smorg is None:
            raise Exception(f"Unknown dashboard for the site {self.__site.name} ! ")
        self.__merakiDashboard = SopMerakiUtils.connect(self.__smorg.dash.nom, self.__smorg.dash.api_url, self.__simulate)
        self.__logger.log_info(f"Meraki connection established to dashboard {self.__smorg.dash.nom}")

    def __get_dash(self):
        if self.__merakiDashboard is None:
            self.__meraki_connect()
        if self.__merakiDashboard is not None:
            return self.__merakiDashboard
        raise Exception("Not connected")
    #endregion 

    def _vpn_enable_disable_prefix(
        self, nbp: Prefix, mvh: MerakiVPNHubs, details: bool = False
    ):
        """Enables or disables the AutoVPN SDWAN participation for a prefix

        Warning :
        - only active/noncompliant/decomissionning prefixes will be pushed
        - other prefixes will be VPN disabled forcibly
        """

        if details:
            self.__logger.log_debug(f"__vpn_enable_disable_prefix '{nbp.prefix}' =========")
        meraki_visible = SopUtils.default_if_none(
            nbp.custom_field_data.get("meraki_visible"), True
        )
        if not meraki_visible:
            if details:
                self.__logger.log_debug(
                    f"__vpn_enable_disable_prefix skipping '{nbp.prefix}' : NOT MERAKI VISIBLE ========="
                )
            return
        forced_off = False
        mand = nbp.custom_field_data.get("sdw_vpn_enable")
        if nbp.status not in ["active", "noncompliant", "decommissioning"]:
            forced_off = True
            mand = "vpnoff"
        if details:
            self.__logger.log_debug(
                f"__vpn_enable_disable_prefix '{nbp.prefix}' computed state : {mand} ========="
            )
        if mand is None:
            return
        if mand == "leave":
            return
        nets = mvh.get_site_to_site_nets()
        if details:
            self.__logger.log_debug(
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
                self.__logger.log_debug(
                    f"__vpn_enable_disable_prefix '{nbp.prefix}' nets loop for {net} ========="
                )
            if net.bound:
                if details:
                    self.__logger.log_warning(
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
            if nbp.status not in ["retired", "reserved", "container"]:
                self.__logger.log_warning(
                    f"Prefix {nbp.prefix} not found on site {nbp.scope.name}."
                )
            return
        upd = False
        # print(f"OLD mand:{mand} - z.vpn:{z.vpn}")
        if mand == "vpnon" and not (z.vpn):
            z.vpn = True
            upd = True
            self.__logger.log_success(f"Enabling VPN for {nbp.prefix} on site {nbp.scope.name}")
        elif mand == "vpnoff" and z.vpn:
            z.vpn = False
            upd = True
            self.__logger.log_success(f"Disabling VPN for {nbp.prefix} on site {nbp.scope.name}")
            if forced_off:
                self.__logger.log_warning(
                    f"==== FORCIBLY DISABLING PREVIOUSLY ENABLED VPN for {nbp.prefix} on site {nbp.scope.name}"
                )
        if upd:
            self.__get_dash().appliance.updateNetworkApplianceVpnSiteToSiteVpn(
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
            si:SopInfra = nbs.sopinfra
            d = si.hub_default_route_setting
            dflt = d is not None and d.strip() == "true"
            sho = si.hub_order_setting
        except dcim.models.sites.Site.sopinfra.RelatedObjectDoesNotExist:
            si = None
        # Sanitize before use
        if sho is None:
            sho = ""
        # TODO set reasonnable defaut if empty

        # Build target
        target = []
        for x in sho.split(","):
            target.append({"hubId": x, "useDefaultRoute": dflt})
        # See if the target is good
        nets = mvh.get_all_nets()
        for net in nets:
            if net.bound:
                if details:
                    self.__logger.log_info(
                        f"========= CANNOT VPN ENABLE/DISABLE VLANS ON TEMPLATIZED NETWORK {net.name} ========="
                    )
                continue
            # we can have several meraki nets on a netbox net -> we need to build a target for each of those
            hasnets = len(net.get_meraki_subnets_list()) > 0
            if net.mode == "none":
                if hasnets:
                    # SHould never happen !
                    self.__logger.log_failure(
                        f"Appliance in org {net.orgId} and net {net.id} (in netbox net {nbs.name}) has nets but mode is NONE !"
                    )
                continue
            elif net.mode == "hub":
                self.__logger.log_warning(
                    f"Ignoring -> HUB MODE <- appliance in org {net.orgId} and net {net.id} (in netbox net {nbs.name})."
                )
                continue
            upd = False
            if hasnets:
                hl = net.get_meraki_hubs_list()
                if not (SopUtils.deep_equals_json(hl, target)):
                    self.__logger.log_success(
                        f"Changing hub list for {nbs.name} (org:{net.orgId}/net:{net.id})."
                    )
                    net._hubs = []
                    for y in target:
                        net._hubs.append(MerakiS2SHub(y))
                    upd = True
            else:
                if not ("none" == net.mode):
                    self.__logger.log_success(
                        f"Clearing hub list for {nbs.name} (org:{net.orgId}/net:{net.id})."
                    )
                    net.mode = "none"
                    net._hubs = []
                    net._subnets = []
                    upd = True
            if upd:
                self.__get_dash().appliance.updateNetworkApplianceVpnSiteToSiteVpn(
                    net.id,
                    mode=net.mode,
                    hubs=net.get_meraki_hubs_list(),
                    subnets=net.get_meraki_subnets_list(),
                )


    def _switches_push_stp(self, nbs: Site, details: bool = False):

        if details:
            self.__logger.log_debug(f"_switches_push_stp '{nbs}' =========")

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
                    self.__logger.log_failure(f"Cannot configure stack {sts.nom} on network {stsnet.nom} without related netbox devices")
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
                    self.__logger.log_failure(f"Cannot configure stack {sts.nom} on network {stsnet.nom} without STP configuration")
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
            curr = self.__get_dash().switch.getNetworkSwitchStp(mnet)
            tgt = {"rstpEnabled": True, "stpBridgePriority": stpbp}
            if SopUtils.deep_equals_json_ic(tgt, curr):
                self.__logger.log_info(
                    f"Spanning settings for [{mnet}] are correct {tgt=}, skipping update."
                )
            else:
                if details: 
                    self.__logger.log_debug(
                        f"Spanning settings for [{mnet}] are different {curr=} VS {tgt=}"
                    )
                # passer l'appel
                self.__get_dash().switch.updateNetworkSwitchStp(
                    mnet, rstpEnabled=True, stpBridgePriority=stpbp
                )
                self.__logger.log_success(f"Updated spanning tree for [{mnet}] : {tgt=}")

    def _switches_push_igmp(self, nbs: Site, details: bool = False):
        if details:
            self.__logger.log_debug(f"_switches_push_igmp '{nbs}' =========")
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
            curr = self.__get_dash().switch.getNetworkSwitchRoutingMulticast(mid)
            tgt = {"defaultSettings": defaultSettings, "overrides": overrides}
            if SopUtils.deep_equals_json_ic(tgt, curr):
                self.__logger.log_info(
                    f"IGMP settings for [{mnet}] are correct, skipping update."
                )
            else:
                if details: 
                    self.__logger.log_debug(
                        f"IGMP settings for [{mnet}] are different {curr=} VS {tgt=}"
                    )
                # Procéder à l'update
                self.__get_dash().switch.updateNetworkSwitchRoutingMulticast(
                    mid, defaultSettings=defaultSettings, overrides=overrides
                )
                self.__logger.log_success(
                    f"Updated IGMP settings for [{mnet}] to {defaultSettings=} and {overrides=}"
                )

    def _switches_push_qos_rules(self, nbs: Site, details: bool = False):
        if details:
            self.__logger.log_debug(f"_switches_push_qos_rules '{nbs}' =========")
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
            curr = self.__get_dash().switch.getNetworkSwitchQosRules(mid)
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
                    self.__logger.log_debug(f"could not find {x=} in {tgt=}")
                lst_rem.append(curr_id)
            # Now add all the settings that weren't found
            for y in tgt:
                changed = True
                if details:
                    self.__logger.log_debug(f"Adding QOS Rules in [{mnet}] : {y}")
                self.__get_dash().switch.createNetworkSwitchQosRule(mid, **y)
            # Now remove all those that we didn't want
            for x in lst_rem:
                changed = True
                if details:
                    self.__logger.log_debug(f"Deleting QOS Rules in [{mnet}] : {x}")
                self.__get_dash().switch.deleteNetworkSwitchQosRule(mid, x)
            if changed:
                self.__logger.log_success(f"Updated QOS Rules for [{mnet}] !")
            elif details:
                self.__logger.log_debug(f"No change in QOS Rules for [{mnet}]")

    # ============================================================================================

    def _get_all_mer_nets_for_site(
        self, site: Site
    ) -> MerakiNets:
        
        mns = MerakiNets()

        # Meraki org/net loop
        self.__logger.log_debug(f"_get_all_mer_nets_for_site - Meraki net loop")
        if site.meraki_nets.count()==0:
            return mns
        net: SopMerakiNet
        for net in site.meraki_nets.all():
            self.__logger.log_debug(f"_get_all_mer_nets_for_site - handling {net.nom}")
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

        # Check that all Meraki Networks are in the same Organisation
        if len(mns.get_orgs_ids())>1:
            raise Exception(f"Meraki networks are spread over several organizations : {mns.get_orgs_ids()} ")
            
        # TODO : quand le claim sera dans netbox, on pourra éliminer l'appel à getOrganizationDevices
    
        # ["appliance","camera","cellularGateway","secureConnect","sensor","switch","systemsManager","wireless"]
        self.__logger.log_debug(f"_get_all_mer_nets_for_site - getOrganizationDevices")
        # TODO: bug quand on a un network sur plusieurs orgs   
        devices = self.__get_dash().organizations.getOrganizationDevices(
            organizationId=net.org.meraki_id,
            productTypes=[MerakiConstants.dev_type_appliance],
            networkIds=mns.get_net_ids(),
        )
        for dev in devices:
            if mns.has_net_id(dev["networkId"]):
                if (x := dev.get("productType")) is not None:
                    if x == MerakiConstants.dev_type_appliance:
                        mn: MerakiNetwork = mns.get_net(dev["networkId"])
                        mn.add_appliance(dev["serial"], net.org.meraki_id)
                        self.__logger.log_debug(
                            f"_get_all_mer_nets_for_site - getNetworkApplianceSecurityIntrusion"
                        )
                        x: (
                            dict
                        ) = self.__get_dash().appliance.getNetworkApplianceSecurityIntrusion(
                            mn.id
                        )
                        # self.__logger.log_debug(f"netappids {x}")
                        mn._ids_mode = x.get("mode")
                        self.__logger.log_debug(
                            f"_get_all_mer_nets_for_site - getNetworkApplianceSecurityMalware"
                        )
                        x: (
                            dict
                        ) = self.__get_dash().appliance.getNetworkApplianceSecurityMalware(
                            mn.id
                        )
                        # self.__logger.log_debug(f"netappamp {x}")
                        mn._amp_mode = x.get("mode")
                        self.__logger.log_debug(
                            f"_get_all_mer_nets_for_site - getNetworkApplianceContentFiltering"
                        )
                        x: (
                            dict
                        ) = self.__get_dash().appliance.getNetworkApplianceContentFiltering(
                            mn.id
                        )
                        # self.__logger.log_debug(f"netctfilter {x}")
                        mn._ctflt = x
                        # self.__logger.log_debug(f"built {mn}")
        return mns

    # ============================================================================================

    def _fetch_hubs(self, mns: MerakiNets, *args, **kwargs) -> MerakiVPNHubs:
        mvh = MerakiVPNHubs()
        mn: MerakiNetwork = None
        for mn in mns.get_appliance_nets():
            # Fetch network info from Meraki
            self.__logger.log_debug(f"Fetching hub info for site {mn.name}...")
            mvh.add_net(
                MerakiS2SInfo(
                    mn.orgId,
                    mn.id,
                    mn.name,
                    mn.bound,
                    self.__get_dash().appliance.getNetworkApplianceVpnSiteToSiteVpn(
                        mn.id
                    ),
                )
            )
        return mvh

    def enforce_one_netbox_site(self):

        # GET MERAKI NETWORKS FOR NETBOX SITE
        mns: MerakiNets = None
        mns = self._get_all_mer_nets_for_site(self.__site)
        if self.__details:
            self.__logger.log_debug(f"MNS => {mns}")
        if len(mns.nets.keys()) == 0:
            self.__logger.log_warning(
                f"Impossible to match Meraki networks to this site slug '{self.__site.slug}' !"
            )
            self.__logger.log_warning(
                f"Please verify both your slug (lower case match) and your Meraki network naming (must match {SopRegExps.meraki_sitename_str})."
            )
            return
        org_ids: list[str] = list()
        si = self.__site.sopinfra

        # PATCH SITE
        self.__logger.log_info(f"==== SITE:{self.__site.name} >>>> PATCH NETWORKS SETTINGS")
        for mn in mns.get_unbound_appliance_nets():
            self.__logger.log_debug(
                f"MERAKI NETWORK {mn.name}/{mn.id} : {mn.has_appliances=}/{mn.bound=}"
            )
                    
            # Save Org ID for later
            if self.__details:
                self.__logger.log_debug(f"{mn.appliances=}")
            for v in mn.appliances.values():
                if v not in org_ids:
                    if self.__details:
                        self.__logger.log_debug(f"append {v=}")
                    org_ids.append(v)
            # Reset AMP/IDS/ContentFiltering
            # TODO move that to scheduled task
            if not ("disabled" == mn._amp_mode):
                self.__logger.log_warning(
                    f"Resetting {mn.name}/{mn.id} AMP mode {mn._amp_mode} to 'disabled'"
                )
                self.__get_dash().appliance.updateNetworkApplianceSecurityMalware(
                    mn.id, mode="disabled"
                )
            if not ("disabled" == mn._ids_mode):
                self.__logger.log_warning(
                    f"Resetting {mn.name}/{mn.id} IDS mode {mn._amp_mode} to 'disabled'"
                )
                self.__get_dash().appliance.updateNetworkApplianceSecurityIntrusion(
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
                    self.__logger.log_warning(
                        f"Resetting {mn.name}/{mn.id} Content Filtering {mn._ctflt} to empty lists"
                    )
                    self.__get_dash().appliance.updateNetworkApplianceContentFiltering(
                        mn.id,
                        allowedUrlPatterns=[],
                        blockedUrlPatterns=[],
                        blockedUrlCategories=[],
                        urlCategoryListSize="topSites",
                    )
            
            # ----------------- UMBRELLA ------------------
            # Force umbrella credentials
            self.__get_dash().appliance.connectNetworkApplianceUmbrellaAccount(mn.id, SopUmbrellaUtils.get_legacy_api_key_for_dash_name("GLOBAL"))

            # # DO NOT ENABLE WHEN WE CAN'T SET EXCEPTIONS
            # aea=EarlyAccessAppliance(self.__get_dash()._session)
            # try:
            #     enable=aea.updateUmbrellaNetworkProtection(mn.id,True)
            # except APIError as e:
            #     if e.status==405 and "Umbrella protection is already enabled on this entity" in f"{e.message}":
            #         self.__logger.log_info(f"MERAKI NETWORK {mn.name}/{mn.id} : Umbrella protection is already active")
            #     else:
            #         raise e

            
            # ----------------- PRISMA ------------------
            # Check Prisma Access VPN conf
            if si is not None and si.enabled is not None:
                    # We need to act
                    self.__logger.log_debug(
                        f"enforce_one_netbox_site - prisma should be {si.enabled=} / current tags {mn.tags=}"
                    )
                    if si.enabled == "true":
                        fix_new = mn.add_tag(f"{si.endpoint.name}")
                        fix_old = mn.del_tag(f"AUTO-{mn.id}")
                        if fix_new or fix_old:
                            update_meraki: dict = {"tags": mn.tags}
                            if self.__details:
                                self.__logger.log_debug(f"{update_meraki=}")
                            d = self.__get_dash().networks.updateNetwork(
                                mn.id, **update_meraki
                            )
                            self.__logger.log_success(
                                f"fixed prisma network tags - new tags {d.get('tags')}"
                            )
                    elif si.enabled == "false":
                        if mn.del_tag(f"{si.endpoint.name}"):
                            if self.__details:
                                self.__logger.log_debug(
                                    f"remove new prisma tag '{si.endpoint.name}'"
                                )
                            update_meraki: dict = {"tags": mn.tags}
                            if self.__details:
                                self.__logger.log_debug(f"{update_meraki=}")
                            d = self.__get_dash().networks.updateNetwork(
                                mn.id, **update_meraki
                            )
                            self.__logger.log_success(
                                f"fixed prisma network tags - new tags {d.get('tags')}"
                            )
                        pass
                    elif si.enabled == "unknown" or si.enabled.strip() == "":
                        self.__logger.log_debug(f"Prisma unknown -> nothing to do !")
                        pass
                    else:
                        raise Exception(
                            f"Unkwnown sopinfra enabled value {si.enabled=} !"
                        )

        # # NOT WORKING FOR NOW
        # # PATCH SITE FOR UMBRELLA  (not in the previous loop because of delay to activation)
        # excl=SopUmbrellaUtils.get_umbrella_excluded_domains(self.__site)
        # if excl:
        #     self.__logger.log_info(f"==== SITE:{self.__site.name} >>>> PATCH UMBRELLA DOMAIN EXCLUSIONS")
        #     for mn in mns.get_unbound_appliance_nets():
        #         for tries in range(1,2):
        #             try:
        #                 res=aea.updateUmbrellaExcludedDomains(mn.id, domains=excl)
        #                 print(res)
        #                 break
        #             except APIError as e:
        #                 print(e)
        #                 self.__logger.log_debug(f"MERAKI NETWORK {mn.name}/{mn.id} : updateUmbrellaExcludedDomains failed : sleeping 1s (try {tries})")
        #                 time.sleep(1)
        #         else:
        #             self.__logger.log_failure(f"MERAKI NETWORK {mn.name}/{mn.id} :  updateUmbrellaExcludedDomains failed {tries} times")

        # PATCH ORG FOR PRISMA VPN
        self.__logger.log_info(f"==== SITE:{self.__site.name} >>>> PATCH ORGANISATION SETTINGS")
        if si is not None:
            if si.endpoint is None:
                self.__logger.log_info(f"No Prisma config found -> SKIPPING")
            else:                
                dict_peers = self.__get_dash().appliance.getOrganizationApplianceVpnThirdPartyVPNPeers(
                    self.__smorg.meraki_id
                )
                current_peers = dict_peers.get("peers")
                self.__logger.log_debug(
                    f"enforce_one_netbox_site {self.__site.name} - {self.__smorg.meraki_id=} - {current_peers=}"
                )
                for p in current_peers:
                    if si.endpoint.name == p.get("name"):
                        self.__logger.log_info(f"Peer {si.endpoint.name} found -> SKIPPING")
                        break
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
                    self.__logger.log_info(f"Peer {si.endpoint.name} *NOT* found -> PUSHING")
                    self.__get_dash().appliance.updateOrganizationApplianceVpnThirdPartyVPNPeers(
                        self.__smorg.meraki_id, peers=current_peers
                    )

        # PATCH PREFIXES
        if self.__details:
            self.__logger.log_info(f"==== SITE:{self.__site.name} >>>> PATCH PREFIXES")
        for net in mns.get_appliance_nets():
            mnu = MerakiNetworkUpdater(
                self.__get_dash(), self.__site, net, self.__logger, self.__details
            )
            mnu.patch_one_meraki_site_network()

        # FETCH HUBS (DEFERRED TO HAVE A CURRENT REPRESENTATION)
        mvh: MerakiVPNHubs = None
        mvh = self._fetch_hubs(mns)
        if self.__details and True:
            self.__logger.log_debug(f"MVH => {mvh}")

        # PATCH HUBS
        if self.__details:
            self.__logger.log_info(f"==== SITE:{self.__site.name} >>>> PATCH HUBS")
        self._vpnhub_enforce_site(self.__site, mvh, self.__details)

        # PATCH VPN
        if self.__details:
            self.__logger.log_info(f"==== SITE:{self.__site.name} >>>> PATCH VPN")
        self._vpn_enable_disable_site(self.__site, mvh, self.__details)

        # PATCH STP
        if self.__details:
            self.__logger.log_info(f"==== SITE:{self.__site.name} >>>> PATCH STP")
        self._switches_push_stp(self.__site, self.__details)

        # PATCH IGMP
        if self.__details:
            self.__logger.log_info(f"==== SITE:{self.__site.name} >>>> PATCH IGMP")
        self._switches_push_igmp(self.__site, self.__details)

        # PATCH QOS RULES
        if self.__details:
            self.__logger.log_info(f"==== SITE:{self.__site.name} >>>> PATCH QOS")
        self._switches_push_qos_rules(self.__site, self.__details)



    @classmethod
    def push_to_meraki_dashboard(
        cls, log: JobRunnerLogMixin, site: Site, details: bool, simulate: bool
    ):
        if site is None:
            log.info(f"Nothing to do...")
            return
        if log :
            log.info(f"MerakiUpdater:push_to_sites handling '{site.name}'...")
        upd:NetboxSiteMerakiUpdater=NetboxSiteMerakiUpdater(site, log, details, simulate)
        upd.enforce_one_netbox_site()





# =======================================================================

class MerakiToolMixin(NetboxSiteMerakiUpdater, SopBaseScriptMixin):
    pass


# =======================================================================

