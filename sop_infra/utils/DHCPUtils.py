from core.models import ObjectType
from sop_infra.utils.meraki_objects import MerakiConstants, MerakiNetwork
from sop_utils.misc import SopUtils
from sop_utils.regexps import SopRegExps
from sop_utils.strings import StringUtils

from dcim.models import Site
from ipam.models import IPAddress, Prefix
from django.db.models import Q
import dcim, ipam, re
from django.utils.text import slugify

class DHCPUtils():

    alcatel_vlan_str="Alcatel VLAN (\d+)"
    alcatel_vlan_re=re.compile(alcatel_vlan_str)

    @staticmethod
    def dhcp43_to_alcatel_voice_vlan(opt43: str) -> int:
        """Determine Alcatel Voice VLAN Number from the hex value of DHCP Option 43

        option 43 hex 3a:02:HH:HH:ff where HH:HH is the hex value of your voice vlan

        >>> dhcp43_to_alcatel_voice_vlan('3a:02:00:14:ff')
        20
        >>> dhcp43_to_alcatel_voice_vlan('3a:02:00:72:ff')
        114
        >>> dhcp43_to_alcatel_voice_vlan('3a:02:01:2c:ff')
        300
        >>> dhcp43_to_alcatel_voice_vlan('00:3a:02:01:2c:ff')
        300
        """
        return (int(opt43.replace(':', ''), base=16) & 0xFFFF00) >> 8

    @staticmethod
    def alcatel_voice_vlan_to_dhcp43(vlan: int) -> str:
        """Print hex value of DHCP Option 43 from Alcatal Voice VLAN Number

        >>> alcatel_voice_vlan_to_dhcp43(20)
        '3a:02:00:14:ff'
        >>> alcatel_voice_vlan_to_dhcp43(114)
        '3a:02:00:72:ff'
        >>> alcatel_voice_vlan_to_dhcp43(300)
        '3a:02:01:2c:ff'
        """
        return ":".join(f"{byte:02x}" for byte in (0x3a020000ff | (vlan << 8)).to_bytes(5, byteorder='big'))

    @staticmethod
    def find_ipv4addresses(text:str)->list:
        return SopRegExps.ip4_re.findall(text)

    NETBOX_DNS_CF_2_MERAKI_DNS = {
            'upstream': 'upstream_dns',
            'umbrella': 'opendns',
        }

    @staticmethod
    def netbox_dns_cf_to_meraki_dns(netbox_dns:str)->str:
        return DHCPUtils.NETBOX_DNS_CF_2_MERAKI_DNS.get(netbox_dns)
    
    @staticmethod
    def netbox_get_site_umbrella_servers(site:Site)->str:
        umbrellas:list[IPAddress]=[]
        pfs=Prefix.objects.filter(site__slug=site.slug)
        for pf in pfs:
            umbrellas.extend(pf.get_child_ips().filter(tags__slug='umb-umbrella-server'))
        return "\n".join(umb.address.ip.format() for umb in umbrellas)
    
    @staticmethod
    def netbox_extract_short_vlan_name(pref:Prefix)->str:
        if (v:=pref.vlan) is None:
            return "UNK"
        if (r:=v.role) is None:
            return "UNK"
        if (n:=r.name) is None:
            return "UNK"
        m=re.match(r'^([^ ]+) .*$')
        if m is None:
            return "UNK"
        ret=m.group(1)
        if pref.status=='noncompliant':
            ret+="-(NC)"
        return ret
    
    @staticmethod
    def add_or_replace_dhcp_option(options:list[dict], newopt:dict, logger) -> None:
        if not DHCPUtils.__check_opt_syntax(newopt, logger):
            return
        for opt in options:
            if DHCPUtils.__check_opt_syntax(opt, logger):
                if SopUtils.safe_equals(opt.get('code'), newopt.get('code')):
                    for f in ['type', 'value']:
                        opt[f]=newopt.get(f)
                        return
        options+=[newopt]

    @staticmethod
    def __check_opt_syntax(opt:dict, logger) -> bool:
        for f in ['code', 'type', 'value']:
            if not f in opt:
                logger.log_failure(f"this dhcp option doesn't have a {f} field  : {opt}")
                return False
        return True
    
    @staticmethod
    def get_cf_from_vlan_or_vlan_role(prefix:Prefix, cf_name:str, logger=None):
        if prefix is None:
            return None
        if prefix.vlan is None:
            if prefix.role is None:
                return None
            #logger.log_debug(f"getcfdeep {prefix}/{cf_name} prefix.role.custom_field_data.get(cf_name) ={prefix.role.custom_field_data.get(cf_name)}")
            return prefix.role.custom_field_data.get(cf_name)
        if (x:=prefix.vlan.custom_field_data.get(cf_name)) is not None:
            #logger.log_debug(f"getcfdeep {prefix}/{cf_name} prefix.vlan.custom_field_data.get(cf_name) is not None : {prefix.vlan.custom_field_data.get(cf_name)}")
            return x
        if prefix.vlan.role is None:
            return None
        #logger.log_debug(f"getcfdeep {prefix}/{cf_name} get from role : {prefix.vlan.role.custom_field_data.get(cf_name)}")
        return prefix.vlan.role.custom_field_data.get(cf_name)
        
        
# =======================================================================

class DhcpReservation():
    
    ip: str
    mask: int
    name: str
    site: str = ''
    dns: str = ''
    mac: str = ''
    def __init__(self, ip) -> None:
        #d.ip = str(ip.address).split('/')[0]  # address = IP/Mask
        self.ip = ip.address.ip.format()
        #d.mask = int(str(ip.address).split('/')[1])  # ValueError. Mais pas possible vu Netbox.
        self.mask = ip.address.netmask.netmask_bits()
        self.name = ip.assigned_object.device.name
        self.dns = ip.dns_name
        self.site = ip.assigned_object.device.site.slug
        self.mac = str(ip.assigned_object.mac_address).lower()
    def info(self):
        return f"MyDevice(ip={self.ip},mask={self.mask},mac{self.mac})"


# =======================================================================


# =======================================================================

class DhcpSettings():

    __range_filter=Q(Q(status='active')&(Q(role__slug='rsvd')|Q(role__slug='fix')))
    __internal_dns_servers='10.1.2.3\n10.1.2.4'
    __internal_search_domain='ad.soprema.com'
    __external_dns_servers=MerakiConstants.upstream_dns
    __external_search_domain=None

    sdw_activation:bool=None
    dhcp_activation:bool=None
    dns_name_servers:str=None
    dns_search_domain:str=None
    dhcp_boot_options:bool=False
    dhcp_lease_time:str=None
    mandatory_dhcp:bool=None
    dhcp_options=[]
    sdw_routed_via:IPAddress=None
    # ex: { 'code': '15', 'type': 'text', 'value': 'ad.soprema.com' }
    reservedIpRanges=[]
    # ex: { 'start': '10.24.230.1', 'end': '10.24.230.50', 'comment': '50 prems' }
    devices:list[DhcpReservation]=None
    relays:list[IPAddress]=None

    def __init__(self, nb_prefix:Prefix, site_umbrellas:str, is_isolated_vlan:bool, is_wan_facing_vlan:bool, default_to_upstream_dns:bool, logger=None) -> None:
        self.dhcp_options=[]
        self.reservedIpRanges=[]
        self.dhcp_lease_time='1 hour'
        self.relays=[]
        custom_fields = nb_prefix.custom_field_data
        # Enable/disable/leave DHCP 
        if (x:=custom_fields.get('dhcp_dhcp_mode'))=="leave":
            self.dhcp_activation=None
        elif x=="enabled":
            self.dhcp_activation=True
        elif x=="disabled":
            self.dhcp_activation=True
        else:
            logger.log_failure(f'Unsupported dhcp_dhcp_mode value : {x}')        
        # Get relay if set
        if (x:=custom_fields.get('dhcp_dhcp_relay')) is not None:
            logger.log_debug(f'relays for prefix {nb_prefix}: {x}')
            tgt=[]
            for y in x:
               y=IPAddress.objects.get(pk=y)
               #logger.log_debug(f'add {y} -> {y.address.ip}')
               tgt.append(str(y.address.ip)) 
            self.relays=tgt
        # store SDWAN enablement 
        if (x:=custom_fields.get('sdw_vpn_enable'))=="leave":
            self.sdw_activation=None
        elif x=="vpnon":
            self.sdw_activation=True
        elif x=="vpnoff":
            self.sdw_activation=False
        else:
            self.sdw_activation=None
            logger.log_failure(f'Unsupported sdw_vpn_enable value : {x}')
        # calculate DNS for this prefix
        if is_isolated_vlan or is_wan_facing_vlan :
            self.dns_name_servers=DhcpSettings.__external_dns_servers
            self.dns_search_domain=DhcpSettings.__external_search_domain
        elif self.sdw_activation is None:
            self.dns_name_servers=None
            self.dns_search_domain=None
        elif self.sdw_activation and not (default_to_upstream_dns):
            self.dns_name_servers=(f'{site_umbrellas}\n{DhcpSettings.__internal_dns_servers}').strip()
            self.dns_search_domain=DhcpSettings.__internal_search_domain
        else:
            self.dns_name_servers=DhcpSettings.__external_dns_servers
            self.dns_search_domain=DhcpSettings.__external_search_domain
        # autres dhcp options text
        for opt in [ '66', '191', '235', '242' ]:
            if value := custom_fields.get('dhcp_option_' + opt):
                self.dhcp_options += [
                    { 'code': opt, 'type': 'text', 'value': value }
                ]
        # dhcp options ZTP vs Alcatel
        # TODO faire mieux
        if value := custom_fields.get('dhcp_option_43'):
            if value == "None":
                pass 
            elif (m:= DHCPUtils.alcatel_vlan_re.match(value)):
                dhcp43 = DHCPUtils.alcatel_voice_vlan_to_dhcp43(int(m.group(1)))
                self.dhcp_options += [
                    { 'code': '43', 'type': 'hex', 'value': dhcp43 }
                ]
            else:
                logger.log_warning(f"Option 43 invalide '{value}' ignorée (préfixe: {nb_prefix.prefix}).")
        # ranges dhcp
        for r in nb_prefix.get_child_ranges().filter(DhcpSettings.__range_filter):
            self.addDhcpRsvdRange(r.start_address, r.end_address, r.description if r.description else r.role.name)
        # Mandatory DHCP setting doesn't work properly so let's forcibly unset it
        self.mandatory_dhcp=False
        # mand=custom_fields.get('dhcp_mandatory_dhcp') 
        # if mand is not None:
        #     if mand=="unset":
        #         self.mandatory_dhcp=False
        #     elif mand=="set":
        #         self.mandatory_dhcp=True
        #     elif mand=="leave":
        #         self.mandatory_dhcp=None
        #     else:
        #         self.log_warning(f"Valeur inconnue {mand} pour mandatoryDhcp")
        # Routed via
        x=custom_fields.get('sdw_routed_via')
        if x is not None:
            self.sdw_routed_via=IPAddress.objects.get(pk=x)
        # Devices reservations
        self.devices=[]
        ip:IPAddress=None
        for ip in nb_prefix.get_child_ips():
            if not isinstance(ip.assigned_object, dcim.models.Interface):
                continue
            self.devices.append(DhcpReservation(ip))
    
    def __str__(self):
        return f"DhcpSettings(sdw_routed_via={self.sdw_routed_via},dnsNameservers={self.dns_name_servers},dhcpOptions={self.dhcp_options},reservedIpRanges {self.reservedIpRanges})"
    
    def addDhcpRsvdRange(self, start_address, end_address, description):
        self.reservedIpRanges.append(
            {
                'start': str(start_address).split('/')[0],
                'end': str(end_address).split('/')[0],
                'comment': description if description else "exclusion from NetBox",
            }
        )

    def build_target_meraki_vlan(self, ret:dict, meraki_current, mn:MerakiNetwork, logger) -> None:
        # Set the DHCP mode
        if self.dhcp_activation is None :
            ret['dhcpHandling']=meraki_current.get("dhcpHandling")
        elif self.dhcp_activation:
            ret['dhcpHandling']='Run a DHCP server'
        else:
            ret['dhcpHandling']='Do not respond to DHCP requests'
        # Pass some fields through (only if they exist)
        for f in ['interfaceId']:
            if f in meraki_current.keys():
                ret[f]=meraki_current.get(f)
        # Push some plain options
        ret['dhcpBootOptionsEnabled']=self.dhcp_boot_options
        ret["dhcpLeaseTime"]=self.dhcp_lease_time
        ret["dhcpOptions"]=self.dhcp_options
        # Push ranges 
        ret["reservedIpRanges"]=self.reservedIpRanges
        # Add fixed IP assignments
        ret['fixedIpAssignments'] = self.__build_meraki_fixed_assignments(logger)
        # Set relays 
        if self.relays is not None and len(self.relays)>0:
            ret['dhcpHandling']='Relay DHCP to another server'
            ret['dhcpRelayServerIps']=self.relays
        # DNS servers and options
        if self.dns_name_servers is None:
            # fetch current conf due to VPN "leave as is"
            ret["dnsNameservers"]=meraki_current.get("dnsNameservers")
        else:
            ret["dnsNameservers"]=self.dns_name_servers
            if self.dns_search_domain is not None:
                DHCPUtils.add_or_replace_dhcp_option(
                    ret["dhcpOptions"],
                    { 'code': '15', 'type': 'text', 'value': self.dns_search_domain },
                    logger
                )
        # Mandatory DHCP
        x=meraki_current.get("mandatoryDhcp")
        if self.mandatory_dhcp is None :
            if x is not None:
                ret['mandatoryDhcp']=x
        else:
            tgt={"enabled": self.mandatory_dhcp}
            if not(mn.bound):
                ret['mandatoryDhcp']=tgt
            elif SopUtils.deep_equals_json(x, tgt):
                ret['mandatoryDhcp']=tgt
            else:
                ret['mandatoryDhcp']=x
                logger.log_failure(f"CANNOT CHANGE MANDATORY DHCP ON TEMPLATIZED NETWORKS {mn.name}  ==> THIS MUST BE DONE MANUALLY ON THE TEMPLATE")
        # Cleanup when DHCP is not enabled
        if 'Run a DHCP server'!=ret['dhcpHandling']:
            for o in ['dhcpBootOptionsEnabled', "dhcpLeaseTime", "dhcpOptions"]:
                if o in ret.keys():
                    del ret[o]

    def build_target_meraki_route(self, ret:dict, meraki_current, logger) -> None:
        # SDW Enablement
        if self.sdw_activation is None:
            # fetch current conf due to VPN "leave as is"
            ret["enabled"]=meraki_current["enabled"]
        else:
            ret["enabled"]=self.sdw_activation
        # Push some plain options
        ret["reservedIpRanges"]=self.reservedIpRanges
        # Add fixed IP assignments
        ret['fixedIpAssignments'] = self.__build_meraki_fixed_assignments(logger)
        # Add GW
        if self.sdw_routed_via is not None :
            ret['gatewayIp']=f"{self.sdw_routed_via.address.ip}"

    def __build_meraki_fixed_assignments(self, logger):
        assigns={}
        ips={}
        for device in self.devices:
            if device.mac is None or not(SopRegExps.mac_re.match(device.mac)): 
                logger.log_info(f"Allocation '{device.name}' for '{device.ip}' with incorrect mac {device.mac} -> ignoring")
            elif device.mac in assigns:
                dup = assigns[device.mac]
                logger.log_failure(f"Devices '{device.name}' et '{dup['name']}' ont la même MAC '{device.mac}' dans NetBox -> ABORT")
                # TODO : procédure de résolution des conflits
                return None
            elif device.ip in ips:
                dup = ips[device.ip]
                logger.log_failure(f"Devices '{device.name}' et '{dup['name']}' ont la même IP '{device.ip}' dans NetBox -> ABORT")
                # TODO : procédure de résolution des conflits
                return None
            else:
                x={ 'ip': device.ip, 'name': device.name }
                assigns[device.mac] = x
                ips[device.ip]=x
        return assigns

# =======================================================================

class GroupPolicy():

    prefix:Prefix=None
    group_policy_list:list[dict]=None
    group_policy_id:dict[str,str]=None

    def __init__(self, nb_prefix:Prefix, is_isolated_vlan:bool, dhcp_settings:DhcpSettings, logger, details:bool=False) -> None:
        self.prefix=nb_prefix
        self.group_policy_id=dict()
        if is_isolated_vlan:
            #TODO: affiner pour permettre les exectpions
            if details:
                logger.log_debug(f"Prefix {nb_prefix} : building isolated policy")
            self.group_policy_list=GroupPolicy.__build_isolated_policy()
        else:
            if details:
                logger.log_debug(f"Prefix {nb_prefix} : build custom l3 policies")
            self.group_policy_list=GroupPolicy.l3rules_copy_normalize_main(self.prefix, dhcp_settings, logger, details)
        #logger.log_debug(f"init gp {nb_prefix} -> {self.group_policy_list}")
        
    def __str__(self):
        return f"GroupPolicy(prefix={self.prefix},group_policy_list={self.group_policy_list})"
    
    def has_rules(self):
        return self.group_policy_list is not None and len(self.group_policy_list)>0

    @staticmethod
    def l3rules_copy_normalize_main(prefix:Prefix, dhcp_settings:DhcpSettings, logger, details) -> list[dict]:
        if prefix.vlan is None:
            if details:
                logger.log_debug(f"Prefix {prefix} : prefix.vlan is none")
            return None
        if prefix.vlan.role is None:
            if details:
                logger.log_debug(f"Prefix {prefix} : prefix.vlan.role is none")
            return None
        rl3r=prefix.vlan.role.custom_field_data.get('vlan_l3_rules')
        vl3r=prefix.vlan.custom_field_data.get('vlan_l3_rules')
        return GroupPolicy.l3rules_copy_normalize(
                prefix, rl3r, vl3r, dhcp_settings, logger, details
            )

    @staticmethod
    def l3rules_copy_normalize(prefix:Prefix, rl3r:list[dict], vl3r:list[dict], dhcp_settings:DhcpSettings, logger, details) -> list[dict]:
        toHandle=vl3r
        if toHandle is None:
            if details:
                logger.log_debug(f"Prefix {prefix} : no VL3R -> using RL3R")
            toHandle=rl3r
        if toHandle is None:
            if details:
                logger.log_debug(f"Prefix {prefix} : no RL3R either, skipping policies")
            return None
        if details:
            logger.log_debug(f"Prefix {prefix} : copy_normalize for {toHandle}")        
        ret=[]
        context={'prefix':prefix, 'dhcp_settings':dhcp_settings}
        for r in toHandle:
            try:
                if isinstance(r, dict):
                    n:dict = {k:v for k, v in r.items()}    
                    GroupPolicy.__sanitize_rule(n)
                    ret.append(n)
                elif isinstance(r, str):
                    if details:
                        logger.log_debug(f"Prefix {prefix} : isinstance str : {r}")
                    n:list[dict] = GroupPolicy.__try_macros(r, context, logger) 
                    if details:
                        logger.log_debug(f"Prefix {prefix} : after macros : {n}")
                    GroupPolicy.__sanitize_rules(n)
                    if details:
                        logger.log_debug(f"Prefix {prefix} : after sanitize : {n}")
                    ret.extend(n)                
                else:
                    raise Exception(f"We only support dicts and strings. Actual type : {type(r)}")
            except Exception as err:
                logger.log_failure(f" Error in l3rules_copy_normalize on prefix {prefix}\n r={r} \n {err=}, {type(err)}")
                raise err
        return ret
    
    @staticmethod
    def __matches_any(n:dict) -> bool:
        if n is None:
            return False
        if "any"!=(StringUtils.empty_if_none(n.get('destPort')).lower()):
            return False
        if "any"!=(StringUtils.empty_if_none(n.get('destCidr')).lower()):
            return False
        return True
    
    @staticmethod
    def __sanitize_rule(n:dict) -> None:
        if n.get('destPort') is None or "any"==n.get('destPort'):
            n['destPort']="Any"
        if n.get('destCidr') is None or "any"==n.get('destCidr'):
            n['destCidr']="Any"
    
    @staticmethod
    def __sanitize_rules(l:list[dict]) -> None:
        ret:list[dict]=[]
        for x in l:
            ret.append(GroupPolicy.__sanitize_rule(x))

    @staticmethod
    def __try_macros(txt:str, context, logger=None) -> list[dict]:
        if txt is None:
            return []
        if not txt.startswith("$"):
            return []

        if txt=="$_DENY_RFC1918":
            return GroupPolicy.__build_deny_rfc1918()
        if txt=="$_ALLOW_RFC1918":
            return GroupPolicy.__build_allow_rfc1918()
        if txt=="$_DENY_ALL":
            return [ GroupPolicy.__build_deny_all() ]
        if txt=="$_ALLOW_ALL":
            return [ GroupPolicy.__build_allow_all() ]

        ret: list[dict] = []

        if txt.startswith("$_ALLOW_SITE_PREFIX_ROLE:"):
            role=txt[len("$_ALLOW_SITE_PREFIX_ROLE:"):]
            if role.strip()=="":
                raise Exception(f"Incorrect MACRO '$_ALLOW_SITE_PREFIX_ROLE' : missing role")
            tp:Prefix=context.get("prefix")
            mps=Prefix.objects.filter(scope_id=tp.scope_id).filter(scope_type=tp.scope_type).filter(role__slug=role.lower()).filter(status__in=MerakiConstants.active_route_statuses)
            for mp in mps :
                ret.append(GroupPolicy.__build_allow_cidr(f"{mp.prefix}"))
            return ret

        if txt.startswith("$_DENY_SITE_PREFIX_ROLE:"):
            role=txt[len("$_DENY_SITE_PREFIX_ROLE:"):]
            if role.strip()=="":
                raise Exception(f"Incorrect MACRO '$_DENY_SITE_PREFIX_ROLE' : missing role")
            tp:Prefix=context.get("prefix")
            mps=Prefix.objects.filter(scope_id=tp.scope_id).filter(scope_type=tp.scope_type).filter(role__slug=role.lower()).filter(status__in=MerakiConstants.active_route_statuses)
            for mp in mps :
                ret.append(GroupPolicy.__build_deny_cidr(f"{mp.prefix}"))
            return ret

        if txt=="$_ALLOW_SITE_DNS":
            dhcp_settings:DhcpSettings=context.get('dhcp_settings')
            if dhcp_settings is None:
                raise Exception(f"Cannot apply macro '$_ALLOW_SITE_DNS' : NO DHCP settings context !")
            if MerakiConstants.upstream_dns==dhcp_settings.dns_name_servers:
                tp:Prefix=context.get("prefix")
                logger.log_warning(f"'$_ALLOW_SITE_DNS' macro called on an 'upstream_dns' prefix/vlan ({tp})")
                return []
            for x in dhcp_settings.dns_name_servers.split("\n"):
                ret.append(GroupPolicy.__build_allow_cidr(f"{x}/32"))
            #logger.log_debug(f"would send {ret}")
            return ret

        raise Exception(f"Unknown MACRO {txt}")


    @staticmethod
    def __build_deny_cidr(cidr:str) -> dict:
        return  {
                "comment": f"DENY {cidr}",
                "destCidr": f"{cidr}",
                "destPort": "Any",
                "policy": "deny",
                "protocol": "Any"
            }
    
    @staticmethod
    def __build_allow_cidr(cidr:str) -> dict:
        return  {
                "comment": f"ALLOW {cidr}",
                "destCidr": f"{cidr}",
                "destPort": "Any",
                "policy": "allow",
                "protocol": "Any"
            }
    
    @staticmethod
    def __build_allow_all() -> dict:
        return  {
                "comment": "ALLOW ALL",
                "destCidr": "any",
                "destPort": "Any",
                "policy": "allow",
                "protocol": "Any"
            }
    
    @staticmethod
    def __build_deny_all() -> dict:
        return  {
                "comment": "DENY ALL",
                "destCidr": "any",
                "destPort": "Any",
                "policy": "deny",
                "protocol": "Any"
            }

    @staticmethod
    def __build_allow_rfc1918() -> list[dict]:
        return  [
            GroupPolicy.__build_allow_cidr('10.0.0.0/8'),
            GroupPolicy.__build_allow_cidr('172.16.0.0/12'),
            GroupPolicy.__build_allow_cidr('192.168.0.0/16')
        ]

    @staticmethod
    def __build_deny_rfc1918() -> list[dict]:
        return  [
            GroupPolicy.__build_deny_cidr('10.0.0.0/8'),
            GroupPolicy.__build_deny_cidr('172.16.0.0/12'),
            GroupPolicy.__build_deny_cidr('192.168.0.0/16')
        ]
    
    @staticmethod
    def __build_isolated_policy() -> list[dict]:
        x=GroupPolicy.__build_deny_rfc1918()
        x.append(GroupPolicy.__build_allow_all())
        return x

# =======================================================================

class TargetNetwork():

    prefix_str:str=None
    dhcp_settings:DhcpSettings=None
    nb_prefix:Prefix=None
    gp:GroupPolicy=None

    isolated_vlan:bool=None
    wan_facing_vlan:bool=None
    meraki_visible:bool=None
    default_to_upstream_dns:bool=None

    def get_nb_prefix(self)->Prefix:
        return self.nb_prefix
    def get_site(self) -> Site:
        return self.nb_prefix.scope
    def is_vlan(self)->bool:
        return not(self.is_route())
    def is_route(self)->bool:
        return self.dhcp_settings.sdw_routed_via is not None
    def is_wan_facing_vlan(self)->bool:
        return self.wan_facing_vlan
    def is_isolated_vlan(self)->bool:
        return self.isolated_vlan
    def is_meraki_visible(self)->bool:
        return self.meraki_visible
    @property   
    def vlan_id(self)->int:
        if self.nb_prefix.vlan is None:
            return None
        return self.nb_prefix.vlan.vid
    def get_net_name(self)->str:
        if self.nb_prefix.vlan is not None:
            return slugify(self.nb_prefix.vlan.name, False)
        return slugify(f"{self.get_site().name}-{self.prefix_str}", False)

    def __init__(self, nb_prefix:Prefix, site_umbrellas:str, logger, details:bool=False) -> None:
        self.nb_prefix=nb_prefix
        self.prefix_str = str(nb_prefix.prefix)
        self.isolated_vlan=SopUtils.default_if_none(DHCPUtils.get_cf_from_vlan_or_vlan_role(nb_prefix, 'vlan_isolated', logger), False)
        self.wan_facing_vlan=SopUtils.default_if_none(DHCPUtils.get_cf_from_vlan_or_vlan_role(nb_prefix, 'wan_facing_vlan', logger), False)
        self.default_to_upstream_dns=SopUtils.default_if_none(DHCPUtils.get_cf_from_vlan_or_vlan_role(nb_prefix, 'default_to_upstream_dns', logger), False)
        self.meraki_visible=SopUtils.default_if_none(nb_prefix.custom_field_data.get('meraki_visible'), True)
        self.dhcp_settings=DhcpSettings(nb_prefix, site_umbrellas, self.isolated_vlan, self.wan_facing_vlan, self.default_to_upstream_dns, logger)
        self.gp=GroupPolicy(nb_prefix, self.isolated_vlan, self.dhcp_settings,  logger, details)

    def create_target_meraki_vlan(self, id, net_id, subnet, name, appliance_ip, mn:MerakiNetwork, logger) -> dict:
        vlan = {
                    "id": id,
                    "networkId": net_id,
                    "subnet": subnet,
                    "name": name,
                    "applianceIp": appliance_ip,
                }
        return self.adjust_target_meraki_vlan(vlan, mn, logger)

    def adjust_target_meraki_vlan(self, meraki_current, mn:MerakiNetwork, logger, name_over:str=None) -> dict:
        ret={}
        # Pass some fields through
        for f in ['id', 'networkId', 'subnet', 'applianceIp', 'name']:
            if (x:=meraki_current.get(f)) is not None:
                ret[f]=x
        # Overrides
        if not(StringUtils.is_none_or_empty(name_over)):
            ret['name']=name_over.strip()
        # Push dhcp infos 
        self.dhcp_settings.build_target_meraki_vlan(ret, meraki_current, mn, logger)
        # Push group policy ID
        gp_id=self.gp.group_policy_id.get(mn.id)
        if gp_id is not None or meraki_current.get("groupPolicyId") is not None:
            ret['groupPolicyId']=gp_id
        # Last consistency checks
        if StringUtils.is_none_or_empty(ret.get('name')):
            ret['name']=f'{DHCPUtils.netbox_extract_short_vlan_name(self.nb_prefix)}'
        # return our target
        return ret

    def build_target_meraki_route(self, meraki_current, logger, name_over:str=None) -> dict:
        ret={}
        # Pass some fields through
        for f in ['id', 'networkId', 'name', 'subnet', 'gatewayIp']:
            if (x:=meraki_current.get(f)) is not None:
                ret[f]=x
        # Overrides
        if not(StringUtils.is_none_or_empty(name_over)):
            ret['name']=name_over.strip()
        # Push dhcp infos 
        self.dhcp_settings.build_target_meraki_route(ret, meraki_current, logger)
        # Push group policy text
        # TODO but not sure it works (at all)
        # Last consistency checks
        if StringUtils.is_none_or_empty(ret.get('name')):
            ret['name']=f'{DHCPUtils.netbox_extract_short_vlan_name(self.nb_prefix)}'
        # return our target
        return ret

    def __str__(self):
        return f"DhcpPrefix(prefix={self.prefix_str},site={self.get_site().slug},dhcp_settings={self.dhcp_settings},isolated={self.isolated_vlan})"

    def is_valid(self, logger)->bool:
        nbp=self.nb_prefix
        if not(self.meraki_visible):
            logger.log_info(f"Ignoring meraki invisible network : {self.prefix_str}")
            return False
        if self.wan_facing_vlan:
            logger.log_info(f"Ignoring WAN facing network : {self.prefix_str}")
            return False
        if nbp.status in ['reserved','active','noncompliant','decommissioning']:
            # dans ces cas on doit soit avoir un VLAN soit une route
            if nbp.vlan is not None:
                pass
            elif self.dhcp_settings.sdw_routed_via is not None:
                pass
            else : 
                logger.log_warning(f"Ignoring network because of missing vlan or route : {self}")
                return False
        return True

    @staticmethod
    def netbox_get_tagged_prefixes(logger, site:Site, details:bool=False) -> list:
        dhcp_prefixes:list[TargetNetwork] = []
        from django.db.models import Q
        site_ct=ObjectType.objects.get_by_natural_key('dcim', 'site')
        #flt=Q(Q(custom_field_data__dhcp_dhcp_mode='enabled')|Q(custom_field_data__dhcp_dhcp_mode='disabled'))
        if site.status not in MerakiConstants.action_site_status:
            logger.log_debug(f"netbox_get_tagged_prefixes({site}) site status excludes site from processing")
        else:
            flt=Q(scope_type_id=site_ct.id)&Q(scope_id=site.id)
            flt&=Q(status__in=['reserved','active','noncompliant','decommissioning'])
            print(f"filter {flt}")
            site_umbrellas:dict[str,str]={}
            # check if we need to generate artificial prefix for MX native vlan 
            vid1=ipam.models.Prefix.objects.filter(flt&Q(vlan__vid=1))
            if vid1.count()>0 and vid1[0].custom_field_data.get('sdw_routed_via', None) is not None:
                from scripts.netbox_tools import NetboxHelpers
                nbh=NetboxHelpers(logger)
                logger.log_info(f"routed vlan 1 detected -> ensuring stp consistency via stub vlan 3999")
                nbh._create_or_fix_prefix(site, ['3999'], False, details, force_fix=True, force_status=vid1[0].status)
            pfixes=ipam.models.Prefix.objects.filter(flt)
            logger.log_debug(f"netbox_get_tagged_prefixes({site}) found {len(pfixes)} prefixes")
            for pfix in pfixes:
                if (su:=site_umbrellas.get(pfix.scope.slug)) is None:
                    su=DHCPUtils.netbox_get_site_umbrella_servers(pfix.scope)
                    site_umbrellas[pfix.scope.slug]=su
                tgt=TargetNetwork(pfix, su, logger, details)
                if tgt.is_valid(logger):
                    dhcp_prefixes.append(tgt)
            logger.log_debug(f"netbox_get_tagged_prefixes({site}) computed {len(dhcp_prefixes)} TargetNetworks")
        return dhcp_prefixes
    
