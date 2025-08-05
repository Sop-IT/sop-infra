import netaddr
from typing import Any

from django.utils.text import slugify
from django.db.models import Q

from core.models import ObjectType

from dcim.models import Site
from ipam.models import Prefix, VLANGroup, VLAN, vlans, Role, VRF, IPAddress


class NetboxConstants():
    # TODO : move that to config settings
    base_adm_ip_addr=netaddr.IPAddress('10.40.0.0')
    spokes_root_id=11
    sopit_id=386    


class NetboxUtils:

    @staticmethod
    def __get_std_nets()->dict[int, dict[str,Any]]:
        return {
            1:   { 'name':'USR',                    'nature':'IT', 'start':netaddr.IPAddress('10.24.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            20:  { 'name':'LXC',                    'nature':'IT', 'start':netaddr.IPAddress('10.20.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':240, 'vlan_cidr':28},
            201: { 'name':'LXM',                    'nature':'IT', 'start':netaddr.IPAddress('10.20.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':224, 'vlan_cidr':28},
            32:  { 'name':'IND',                    'nature':'IT', 'start':netaddr.IPAddress('10.32.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            36:  { 'name':'STR',                    'nature':'IT', 'start':netaddr.IPAddress('10.36.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            44:  { 'name':'WMS',                    'nature':'IT', 'start':netaddr.IPAddress('10.44.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            48:  { 'name':'ALA',                    'nature':'IT', 'start':netaddr.IPAddress('10.48.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            52:  { 'name':'SOL',                    'nature':'IT', 'start':netaddr.IPAddress('10.52.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            56:  { 'name':'CAM',                    'nature':'IT', 'start':netaddr.IPAddress('10.56.0.0'),     'sdw_vpn_enable':'vpnoff', 'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            64:  { 'name':'GTB',                    'nature':'IT', 'start':netaddr.IPAddress('10.64.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            68:  { 'name':'ACS',                    'nature':'IT', 'start':netaddr.IPAddress('10.68.0.0'),     'sdw_vpn_enable':'vpnoff', 'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            76:  { 'name':'RED',                    'nature':'IT', 'start':netaddr.IPAddress('10.76.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            80:  { 'name':'TMR',                    'nature':'IT', 'start':netaddr.IPAddress('10.80.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            101: { 'name':'MOB',                    'nature':'IT', 'start':netaddr.IPAddress('10.192.0.0'),    'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset',   'slice_cidr':24},
            102: { 'name':'GST',                    'nature':'IT', 'start':netaddr.IPAddress('192.168.100.0'), 'sdw_vpn_enable':'vpnoff', 'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset',   'slice_cidr':24, 'fixed':True, 'local_vrf':True},
            104: { 'name':'EVC',                    'nature':'IT', 'start':netaddr.IPAddress('192.168.104.0'), 'sdw_vpn_enable':'vpnoff', 'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset',   'slice_cidr':24, 'fixed':True, 'local_vrf':True},
            105: { 'name':'AGV',                    'nature':'IT', 'start':netaddr.IPAddress('192.168.105.0'), 'sdw_vpn_enable':'vpnoff', 'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset',   'slice_cidr':24, 'fixed':True, 'local_vrf':True},
            106: { 'name':'VND',                    'nature':'IT', 'start':netaddr.IPAddress('192.168.106.0'), 'sdw_vpn_enable':'vpnoff', 'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset',   'slice_cidr':24, 'fixed':True, 'local_vrf':True},
            401: { 'name':'IMM',                    'nature':'IT', 'start':netaddr.IPAddress('10.18.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset',   'slice_cidr':27},
            402: { 'name':'ESX',                    'nature':'IT', 'start':netaddr.IPAddress('10.19.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':27},
            #403: { 'name':'ST2',                    'nature':'IT', 'start':netaddr.IPAddress('10.18.128.0'),   'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset',   'slice_cidr':27},
            404: { 'name':'BRK',                    'nature':'IT', 'start':netaddr.IPAddress('10.19.128.0'),   'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':27},
            405: { 'name':'BKP',                    'nature':'IT', 'start':netaddr.IPAddress('10.17.0.0'),     'sdw_vpn_enable':'vpnoff', 'dhcp_dhcp_mode':'disabled', 'dhcp_mandatory_dhcp':'unset', 'slice_cidr':27},
            406: { 'name':'ADM-EXT', 'role':'ADM',  'nature':'IT', 'start':netaddr.IPAddress('10.84.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24},
            720: { 'name':'PTC',                    'nature':'IT', 'start':netaddr.IPAddress('10.72.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':0,   'vlan_cidr':28},
            721: { 'name':'BRC',                    'nature':'IT', 'start':netaddr.IPAddress('10.72.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':16,  'vlan_cidr':29},
            722: { 'name':'DRK',                    'nature':'IT', 'start':netaddr.IPAddress('10.72.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':24,  'vlan_cidr':29},
            723: { 'name':'TPE',                    'nature':'IT', 'start':netaddr.IPAddress('10.72.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':32,  'vlan_cidr':29},
            724: { 'name':'DRD',                    'nature':'IT', 'start':netaddr.IPAddress('10.72.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':40,  'vlan_cidr':29},
            729: { 'name':'AFF',                    'nature':'IT', 'start':netaddr.IPAddress('10.72.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':80,  'vlan_cidr':29},
            730: { 'name':'AIS',                    'nature':'IT', 'start':netaddr.IPAddress('10.72.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':88,  'vlan_cidr':29},
            731: { 'name':'RED',                    'nature':'IT', 'start':netaddr.IPAddress('10.72.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':96,  'vlan_cidr':28},
            732: { 'name':'GOV',                    'nature':'IT', 'start':netaddr.IPAddress('10.72.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':112, 'vlan_cidr':28},
            733: { 'name':'PRF',                    'nature':'IT', 'start':netaddr.IPAddress('10.72.0.0'),     'sdw_vpn_enable':'vpnon',  'dhcp_dhcp_mode':'enabled',  'dhcp_mandatory_dhcp':'unset', 'slice_cidr':24, 'offset_alloc':128, 'vlan_cidr':27},
            3999:{ 'name':'STP',                    'nature':'IT', 'start':netaddr.IPAddress('127.99.0.0'), 'sdw_vpn_enable':'vpnoff', 'dhcp_dhcp_mode':'disabled',  'dhcp_mandatory_dhcp':'unset',   'slice_cidr':30, 'fixed':True, 'local_vrf':True, 'force_fix':True},
        }

    @staticmethod
    def get_site_sopinfra(site: Site):
        try:
            return site.sopinfra  # type: ignore
        except:
            return None

    @staticmethod
    def get_sopinfra_site_master_site_id(site: Site) -> int | None:
        sopinfra = NetboxUtils.get_site_sopinfra(site)
        if sopinfra is not None and sopinfra.master_site is not None:
            return site.sopinfra.master_site.id  # type: ignore
        return None

    @staticmethod
    def get_sopinfra_ad_direct_users(site: Site) -> int | None:
        sopinfra = NetboxUtils.get_site_sopinfra(site)
        if sopinfra is not None:
            return site.sopinfra.ad_direct_users  # type: ignore
        return None
    
    @staticmethod
    def check_if_vlan_naming_is_compliant(vl:VLAN) -> bool:
        if vl is None or not isinstance(vl, VLAN):
            raise Exception(f"vl must be a VLAN instance")
        std_nets=NetboxUtils.__get_std_nets()
        # First check if we have an exact match in "user" vlans
        if vl.vid in std_nets.keys():
            std_vl:dict[str,Any]=std_nets.get(vl.vid) # type: ignore
            std_vl_name=std_vl.get("name")
            return vl.name == std_vl_name
        short_name=vl.name.lower()[:3]
        # Then check for the ADM Vlan
        if vl.vid>=40 and vl.vid<50:
            return short_name in ("adm")
        # Then check for INTERNET vlans
        if vl.vid>=50 and vl.vid<=59:
            return short_name in ("obs", "int")
        # Then check for the VOICE Vlan
        if vl.vid==300:
            return short_name in ("voi")
        # Then check for INDUSTRIAL vlans
        if short_name=="ind":
            return True
        return False

    @staticmethod
    def list_non_compliant_vlan_namings(site:Site) -> list[VLAN]:
        ret:list[VLAN]=list()
        vls=VLAN.objects.filter(site_id=site.pk)
        for vl in vls:
            if not NetboxUtils.check_if_vlan_naming_is_compliant(vl):
                ret.append(vl)
        return ret

    @staticmethod
    def get_site_compliance_warning_messages(site:Site)->list[str]:
        ret:list[str]=list()
        lst:list[VLAN]=NetboxUtils.list_non_compliant_vlan_namings(site)
        if len(lst) > 0:
            vl_msgs=[ f'<a href="{v.get_absolute_url()}">{v.vid}/{v.name}</a>' for v in lst ]
            msg=f"Non compliant vlan ID/name : "+ ", ".join(vl_msgs)
            ret.append(msg)
        return ret


class NetboxHelpers():

    def __init__(self, logger):
        self.logger=logger

    def _get_adm_prefix_for_site(self, site:Site)->Prefix:
        flt=Q(Q(scope_type=ObjectType.objects.get_by_natural_key('dcim', 'site'))&Q(scope_id=site.pk))
        # First try to find one vlan with VID 40 and status active
        pfs=Prefix.objects.filter(flt).filter(vlan__vid=40).filter(status='active')
        if pfs.count==1:
            return pfs[0]
        elif pfs.count()>1:
            raise Exception(f"Found several ({pfs.count()}) admin prefixes for site {site.pk}/{site.name} (filter:vid=40 and status=active)")
        # Widen the search without status active
        pfs=Prefix.objects.filter(flt).filter(vlan__vid=40)
        if pfs.count==1:
            return pfs[0]
        elif pfs.count()>1:
            raise Exception(f"Found several ({pfs.count()}) admin prefixes for site {site.pk}/{site.name} (filter:vid=40)")
        # Try with the role and contained in 10.40.0.0/14 and status active
        pfs=Prefix.objects.filter(flt).filter(role_id=3).filter(prefix__net_contained="10.40.0.0/13").filter(status='active')
        if pfs.count()==1:
            return pfs[0]
        elif pfs.count()>1:
            raise Exception(f"Found several ({pfs.count()}) admin prefixes for site {site.pk}/{site.name} (filter: role_id=3 and status active)")
        # Widen the search without status active
        pfs=Prefix.objects.filter(flt).filter(role_id=3).filter(prefix__net_contained="10.40.0.0/13")
        if pfs.count()==1:
            return pfs[0]
        elif pfs.count()>1:
            raise Exception(f"Found several ({pfs.count()}) admin prefixes for site {site.pk}/{site.name} (filter: role_id=3)")
        raise Exception(f"Unable to find the admin prefix for site {site.pk}/{site.name}")

    def _calc_site_net_num(self, p:Prefix)->int:
        if p.prefix.ip.value is None:
            raise Exception("p.prefix.ip.value cannot be None")
        if NetboxConstants.base_adm_ip_addr.value is None:
            raise Exception("NetboxConstants.base_adm_ip_addr.value cannot be None")
        net_num=int((p.prefix.ip.value-NetboxConstants.base_adm_ip_addr.value)/256)
        return net_num
    
    def _calc_std_network_start(self, net_num:int, base:netaddr.IPAddress, cidr:int) -> netaddr.IPAddress:
        start_val=base.value+net_num*(2**(32-cidr))
        start_ip=netaddr.IPAddress(start_val)
        return start_ip
    
    def _calc_std_network(self, net_num:int, base:netaddr.IPAddress, slice_cidr:int, cidr_shift:int, offset_alloc:int, vlan_cidr:int) -> netaddr.IPNetwork:
        if cidr_shift<0:
            raise Exception("cidr_shift cannot be nagative !")
        start_ip=self._calc_std_network_start(net_num, base, slice_cidr)
        shifted_slice_cidr=slice_cidr-cidr_shift
        shifted_alloc_cidr=shifted_slice_cidr
        if offset_alloc is not None and offset_alloc>=0 and vlan_cidr is not None and vlan_cidr>0:
            calc_offset=offset_alloc*(2**cidr_shift)
            calc_vlan_cidr=vlan_cidr-cidr_shift
            if calc_offset>(2**(32-shifted_slice_cidr)-2**(32-calc_vlan_cidr)):
                self.logger.log_failure(f"Offset calculation error : alloc {calc_offset} is over \
                    the slice_cidr ({2**(32-shifted_slice_cidr)}) minus vlan_cidr ({2**(32-calc_vlan_cidr)})")
                self.logger.log_debug(f"net_num={net_num}, base={base}, slice_cidr={slice_cidr}, cidr_shift={cidr_shift}, offset_alloc={offset_alloc}, vlan_cidr={vlan_cidr}")
                raise Exception(f"Offset calculation error : alloc {calc_offset} is over \
                    the slice_cidr ({2**(32-shifted_slice_cidr)}) minus vlan_cidr ({2**(32-calc_vlan_cidr)})")
            shifted_alloc_cidr=calc_vlan_cidr
            start_ip+=calc_offset
        start=netaddr.IPAddress(start_ip)
        p=netaddr.IPNetwork(f"{start}/{shifted_alloc_cidr}")
        return p

    @staticmethod
    def _get_std_net_choices() -> tuple:
        # 403 not in there because it shouldn't be used
        std_nets = (
            (1,'1 - USR'),(20,'20 - LXC'), (201,'201 - LXM'), (32,'32 - IND (OLD)'), (36,'36 - STR'), (44,'44 - WMS'), (48,'48 - ALA'), (52,'52 - SOL'), (56,'56 - CAM'), 
            (64,'64 - GTB'), (68,'68 - ACS'), (76,'76 - RED'), (80,'80 - TMR'), 
            (101, '101 - MOB'), (102, '102 - GST'), (104, '104 - EVC'), (105, '105 - AGV'), (106, '106 - VND'), 
            (401, '401 - IMM'), (402,'402 - ESX'),  (404,'404 - BRK'), (405,'405 - BKP'), (406,'406 - ADM-EXT'),
            (720, '720 - PTC'), (721,'721 - BRC'), (722,'722 - DRK'), (723,'723 - TPE'), (724,'724 - DRD'), (729,'729 - AFF'), (730,'730 - AIS'), (731,'731 - RED'), (732,'732 - GOV'), (733,'733 - PRF')
        )
        return std_nets
  
    @staticmethod
    def _get_std_net_status() -> tuple:
        std_status = (
            ('active','Active'),('reserved','Reserved')
        )
        return std_status
    
    def _calc_std_networks(self, site:Site, details:bool=False) -> dict[int, dict]:
        p=self._get_adm_prefix_for_site(site)
        net_num=self._calc_site_net_num(p)
        preflen=p.prefix.prefixlen
        shift=24-preflen
        #if details:
        #    self.logger.log_debug(f"site {site} : adm_prefix={p}, shift={shift}")
        if net_num is None:
            raise Exception("Cannot calculate std networks without an ADM prefix on site !")
        # TODO : ça devrait être de vrais objets, probablement des modèles
        std_nets=NetboxUtils.__get_std_nets()
        ret={}
        for k,v in std_nets.items():
            start:netaddr.IPAddress=v.get('start') # type: ignore
            if start is None:
                    raise Exception("Configuration error : start must be defined ")
            slice_cidr:int=v.get('slice_cidr') # type: ignore
            if slice_cidr is None:
                    raise Exception("Configuration error : slice_cidr must be defined ")
            if v.get('fixed', False):
                p=netaddr.IPNetwork(f"{start}/{slice_cidr-shift}")
            else:
                offset_alloc:int=v.get('offset_alloc') # type: ignore
                if offset_alloc is None:
                    raise Exception("Configuration error : offset_alloc must be defined ")
                vlan_cidr:int=v.get('vlan_cidr') # type: ignore
                if vlan_cidr is None:
                    raise Exception("Configuration error : vlan_cidr must be defined ")               
                p=self._calc_std_network(net_num, start, slice_cidr, shift, offset_alloc, vlan_cidr)
            x={'name':v.get('name'), 'role':v.get('role', v.get('name')), 'nature':v.get('nature'), 'prefix':p, 'sdw_vpn_enable':v.get('sdw_vpn_enable'),\
               'dhcp_dhcp_mode':v.get('dhcp_dhcp_mode'), 'dhcp_mandatory_dhcp':v.get('dhcp_mandatory_dhcp'), 'local_vrf':v.get('local_vrf')}
            ret[k]=x
            if details:
                self.logger.log_info("VLAN {vid:>4} ({nature}:{role})/ {name} --> {prefix} / VPN:{vpn_enable} DHCP:{dhcp_mode} MAND.:{mandatory_dhcp} LOC_VRF:{local_vrf} FIXED:{fixed}"\
                    .format(vid=k, nature=x.get('nature'), role=x.get('role'), name=x.get('name'), prefix=p, vpn_enable=v.get('sdw_vpn_enable'), \
                    dhcp_mode=v.get('dhcp_dhcp_mode'), mandatory_dhcp=v.get('dhcp_mandatory_dhcp'), local_vrf=v.get('local_vrf'), fixed=v.get('fixed')))
        return ret

    def _flag_non_compliant(self, site:Site, details:bool=False):
        raise NotImplementedError("TODO :implement this")
        # TODO revoir
        # stds=self._calc_std_networks(site, details)
        # pfs=Prefix.objects.filter(site_id=site.pk)
        # pf:Prefix
        # i:int=0
        # for pf in pfs:
        #     if details:
        #         self.logger.log_info(f"Checking prefix: {pf}, status={pf.status}, vlan={pf.vlan}")
        #     # revoir les vlans actifs et non compliant
        #     if pf.status in ['active', 'noncompliant']:
        #         continue
        #     i+=1
        #     pf.snapshot()
        #     ok=True
        #     save=False
        #     if pf.vlan is None:
        #         ok=False
        #         self.logger.log_warning(f"Prefix {pf} : vlan is None -> non compliant ")
        #     if ok and (std:=stds.get(pf.vlan.vid)) is not None:
        #         if details:
        #             self.logger.log_debug(f"extracted std {std} ")
        #         if std.get('prefix')!=pf.prefix:
        #             ok=False
        #             self.logger.log_warning(f"Prefix for vlan {pf.vlan.vid} should be {std.get('prefix')} != current {pf.prefix} -> non compliant")
        #         # TODO refondre
        #         if ok and pf.status=='noncompliant':
        #             pf.status='active'     
        #             save=True
        #         if not(ok):
        #             pf.status='noncompliant'
        #             save=True
        #         if save:
        #             pf.full_clean()
        #             pf.save()     
        #     else:
        #         pass
        #         #TODO : traiter le cas des vlans pas standard déclarés
        #self.logger.log_success(f"Checked {i} prefixes")
            
    def _get_or_create_vlgroup(self, site:Site, nature:str, details:bool=False)->VLANGroup:
        vgname:str
        # TODO : vid_ranges ?
        if nature=="OT":
            vgname="{slug_upper} IND vlans".format(slug_upper=site.slug.upper())
        elif nature=="IT":
            vgname="{slug_upper} vlans".format(slug_upper=site.slug.upper())
        else:
            raise Exception(f"Configuration error : Unknown vlan nature {nature}")
        vgs=VLANGroup.objects.filter(site__id=site.pk).filter(name=vgname)
        if vgs.count()>1:
            raise Exception(f"Configuration error : Several vlangroups for site {site} with name {vgname}")
        if vgs.count()==1:
            return vgs[0]
        if details : 
            self.logger.log_info(f"Creating vlangroup {vgname}")
        vg=VLANGroup()
        vg.scope_type=ObjectType.objects.get_by_natural_key('dcim', 'site') # type: ignore
        vg.scope_id=site.pk
        vg.name=vgname
        vg.slug=slugify(vgname)
        vg.vid_ranges=vlans.default_vid_ranges()
        vg.full_clean()
        vg.save()
        self.logger.log_success(f"Created vlangroup [{vg}]({vg.get_absolute_url()})")
        return vg

    def _get_or_create_vlan(self, site:Site, vlan_id:int, name:str, role_slug:str, vlan_nature:str, force_fix:bool, status:str, details:bool=False)->VLAN:
        if details:
            self.logger.log_debug(f"_get_or_create_vlan ")
        vls=VLAN.objects.filter(site_id=site.pk).filter(vid=vlan_id)
        vl:VLAN
        save=False
        if vls.count()>0:
            if force_fix:
                self.logger.log_info(f"Force fixing existing vlan {vlan_id} on site {site}")
                vl=vls[0]
                vl.snapshot()
                if vl.status!=status:
                    vl.status=status
                    save=True  
            else:
                return vls[0]
        else:
            vl=VLAN(vid=vlan_id, site=site, status=status)
            save=True
        rl=Role.objects.get(slug=role_slug.lower())
        val=self._get_or_create_vlgroup(site, vlan_nature, details)
        if vl.group!=val:
            vl.group=val # type: ignore
            save=True
        val=name
        if vl.name!=val:
            vl.name=val
            save=True
        val=rl
        if vl.role!=val:
            vl.role=val # type: ignore
            save=True   
        val=site.tenant
        if vl.tenant!=val:
            vl.tenant=val
            save=True
        val=rl.description
        if vl.description!=val:
            vl.description=val
            save=True
        if save:
            vl.full_clean()
            vl.save()
            self.logger.log_success(f"Created/updated vlan [{vl}]({vl.get_absolute_url()}), status={vl.status}")
        else:
            self.logger.log_info(f"Nothing to do on vlan [{vl}]({vl.get_absolute_url()}), status={vl.status}")
        return vl

    def _create_or_fix_prefix(self, site:Site, vlans:list[str], alloc_gw:bool, details:bool, force_fix:bool, force_status:str):
        stds:dict[int,dict]=self._calc_std_networks(site, details)
        if details:
            self.logger.log_debug(f"stds:  {stds}")
        for vlan in vlans:
            if details : 
                self.logger.log_debug(f"handling vlan {vlan}")
            if int(vlan) in stds.keys():
                save=False
                p:Prefix
                std:dict=stds.get(int(vlan)) # type: ignore
                if details : 
                    self.logger.log_debug(f"found {vlan} in stds -> {std}")
                pfs=Prefix.objects.filter(site__id=site.pk).filter(prefix=std.get('prefix'))
                if pfs.count()>0:
                    if force_fix or std.get('force_fix'):
                        self.logger.log_info(f"Force fixing existing prefix {std.get('prefix')}")
                        p=pfs[0]
                        p.snapshot()
                    else:
                        self.logger.log_info(f"Skipping existing prefix {std.get('prefix')}")
                        continue
                else:
                    p=Prefix()
                    p.prefix=std.get('prefix')
                    p.status='reserved'
                    p.scope_type=ObjectType.objects.get_by_natural_key('dcim', 'site') # type: ignore
                    p.scope=site
                    save=True
                if force_status:
                    if p.status!=force_status:
                        p.status=force_status
                        save=True
                local_vrf=std.get('local_vrf', False)
                local_vrf_id=None
                vname="{slug_upper} local".format(slug_upper=site.slug.upper())
                if details:
                    self.logger.log_debug(f"Local VRF => {local_vrf} / name={vname}")
                if local_vrf:
                    vrfs=VRF.objects.filter(name=vname)
                    if vrfs.count()<1:
                        v=VRF(name=vname)
                        v.tenant=site.tenant
                        v.enforce_unique=True
                        v.full_clean()
                        v.save()
                        self.logger.log_success(f"Created VRF [{v}]({v.get_absolute_url()})")
                    else:
                        v=vrfs[0]
                    local_vrf_id=v
                    if p.vrf!=v:
                        p.vrf=v # type: ignore
                        save=True
                if std.get('role') is None:
                    raise Exception("Configuration error : role name must be defined")
                rl_name:str=std.get('role') # type: ignore
                rl=Role.objects.get(slug=rl_name.lower()) # type: ignore
                if p.role!=rl:
                    p.role=rl # type: ignore
                    save=True
                val=rl.description
                if p.description!=val:
                    p.description=val
                    save=True
                val=self._get_or_create_vlan(site, int(vlan), std.get('name'), rl_name, std.get('nature'), force_fix | (True==std.get('force_fix')), force_status) # type: ignore
                if p.vlan!=val:
                    p.vlan=val # type: ignore
                    save=True
                val=site.tenant
                if p.tenant!=val:
                    p.tenant=val
                    save=True
                for f in ['sdw_vpn_enable', 'dhcp_dhcp_mode', 'dhcp_mandatory_dhcp']:
                    val=std.get(f)
                    if p.custom_field_data.get(f)!=val:
                        p.custom_field_data[f]=val
                        save=True
                if save:
                    p.full_clean()
                    p.save()
                    self.logger.log_success(f"Created (or fixed) prefix [{p}]({p.get_absolute_url()}), status={p.status}")
                else:
                    self.logger.log_info(f"Nothing to do on prefix [{p}]({p.get_absolute_url()}), status={p.status}")
                if alloc_gw:
                    self._create_or_fix_prefix_gw(p, "MX router", force_fix, details, local_vrf_id)

    def _try_allocate_pfx(self, root_pfx:Prefix, mask_length:int, details:bool=False)->Prefix:
        if details : 
            self.logger.log_debug(f"Trying to allocate prefix (EXACT, NO SPLIT)")
        allocated_prefix=None
        # try with exact length first
        for available_prefix in root_pfx.get_available_prefixes().iter_cidrs():
            if mask_length == available_prefix.prefixlen:
                allocated_prefix = netaddr.IPNetwork(f"{available_prefix.network}/{mask_length}")
                self.logger.log_info(f"Found available prefix (exact) : {allocated_prefix}")
                break
        if allocated_prefix is None:
            if details : 
                self.logger.log_debug(f"Trying to allocate prefix (SPLIT ALLOWED)")
            # try with split allowed
            for available_prefix in root_pfx.get_available_prefixes().iter_cidrs():
                if mask_length >= available_prefix.prefixlen:
                    allocated_prefix = netaddr.IPNetwork(f"{available_prefix.network}/{mask_length}")
                    self.logger.log_info(f"Found available prefix (splitting) : {allocated_prefix}")
                    break
        if allocated_prefix is None: 
            raise Exception(f"Could not find an available subnet of size {mask_length} range in container {root_pfx} ")        
        p=Prefix()
        p.prefix=allocated_prefix
        p.prefix_length=mask_length
        return p
    
    def _get_site_alloc_pfx_from_tenantgroup_cf(self, site:Site, cf_name:str, friendly:str, details:bool=False) -> Prefix:
        if site.tenant is None:
            raise Exception(f"Site {site} tenant is undefined !")
        te:Tenant=site.tenant # type: ignore
        tg:TenantGroup=te.group # type: ignore
        pfx_id=None
        while True :
            pfx_id=tg.custom_field_data.get(cf_name)
            if pfx_id is not None:
                break
            if details:
                self.logger.log_debug(f"Not cf {cf_name} set on TenantGroup {tg}, moving up !")
            tg=tg.parent
            if tg is None:
                if details:
                    self.logger.log_debug(f"Reached the top.... breaking out...")
                break
        if pfx_id is None:
            raise Exception(f"Could not find {friendly} master alloc range for tenant group {tg}")
        if details:
            self.logger.log_debug(f"Found site root alloc prefix for {friendly} : {pfx_id}")
        pfx=Prefix.objects.get(id=pfx_id)
        if pfx is None:
            raise Exception(f"This prefix id ({pfx_id}) doesn't exist anymore ! Please check the TenantGroup custom field {cf_name}")
        if details:
            self.logger.log_debug(f"Will allocate into {pfx} for {friendly} !")
        return pfx    

    def _get_site_indus_container(self, site:Site, indus_seg_pfx:Prefix, details:bool=False) -> Prefix|None:
        pfs=Prefix.objects.filter(site__id=site.pk)\
            .filter(prefix__net_contained=indus_seg_pfx.prefix)\
                .filter(prefix__net_mask_length=21)
        if pfs.count()<=0:
            return None
        return pfs[0]

    def _create_or_fix_indus_container(self, site:Site, details:bool=False, force_fix:bool=False):
        indus_seg_pfx=self._get_site_alloc_pfx_from_tenantgroup_cf(site, 'indus_seg_pfx_alloc', "INDUS_CONTAINER", details)
        p=self._get_site_indus_container(site, indus_seg_pfx, details)
        save=False
        if p is not None:
            if force_fix:
                self.logger.log_info(f"Force fixing existing prefix {p}")
            else:
                self.logger.log_info(f"Skipping existing prefix {p}")
                return
        else:
            self.logger.log_info(f"No existing prefix found -> allocating")
            p=self._try_allocate_pfx(indus_seg_pfx, 21, details)
            if p is None:
                raise Exception(f"Could not find an available IND container of size 21 range in {indus_seg_pfx} ")     
            p.scope=site
            p.tenant=site.tenant
            save=True
        val = f"VLAN 32y - NEW INDUS SEG - {site.name}"
        if val!=p.description:
            p.description=val
            save=True
        val ='container'
        if val != p.status:
            p.status=val
            save=True
        val = Role.objects.get(slug='ind')
        if val!=p.role:
            p.role=val # type: ignore
            save=True
        val="vpnoff"
        if p.custom_field_data.get('sdw_vpn_enable')!=val:
            p.custom_field_data['sdw_vpn_enable']=val
            save=True
        val="disabled"
        if p.custom_field_data.get('dhcp_dhcp_mode')!=val:
            p.custom_field_data['dhcp_dhcp_mode']=val
            save=True
        val="unset"
        if p.custom_field_data.get('dhcp_mandatory_dhcp')!=val:
            p.custom_field_data['dhcp_mandatory_dhcp']=val
            save=True            
        if save:
            p.full_clean()
            p.save()
            self.logger.log_success(f"Created (or fixed) prefix [{p}]({p.get_absolute_url()}), status={p.status}")
        else:
            self.logger.log_info(f"Nothing to do on prefix [{p}]({p.get_absolute_url()}), status={p.status}")

    def _allocate_new_indus_prefix(self, site:Site, mask_length:int, details:bool, force_status:str, desc:str, alloc_pa_gw:bool=False):
        indus_seg_pfx=self._get_site_alloc_pfx_from_tenantgroup_cf(site, 'indus_seg_pfx_alloc', "INDUS_CONTAINER", details)
        cont=self._get_site_indus_container(site, indus_seg_pfx, details)
        if cont is None:
            raise Exception("You need to create the industrail container first !")
        p=self._try_allocate_pfx(cont, mask_length, details)
        ind_role=Role.objects.get(slug='ind')  
        p.scope=site
        p.tenant=site.tenant
        p.description = desc or f"VLAN 32y - NEW INDUS SEG - {site.name}"
        p.status=force_status or 'reserved'
        p.role = ind_role # type: ignore
        p.custom_field_data['sdw_vpn_enable']="vpnoff"
        p.custom_field_data['dhcp_dhcp_mode']="disabled"
        p.custom_field_data['dhcp_mandatory_dhcp']="unset"
        p.comments="created by netbox_tools._allocate_new_indus_prefix"
        p.full_clean()
        p.save()
        self.logger.log_success(f"Created (or fixed) prefix [{p}]({p.get_absolute_url()}), status={p.status}")
        if alloc_pa_gw:
            # we do not force fix because the prefix is supposed to be brand new without any IPs in it
            self._create_or_fix_prefix_gw(p, "PA GW", False, details)

    def _create_initial_vl40(self, site:Site, mask_length:int, status:str, alloc_gw:bool, details:bool=False, force_fix:bool=False):
        return self._create_initial_vlan(site, mask_length, status, 40, "ADM", 'vl40_root_pfx_alloc', "ADMIN_VLAN40", 
                                  { 'sdw_vpn_enable': "vpnon", 'dhcp_dhcp_mode':'enabled', "meraki_visible":True}, 
                                  alloc_gw, "MX router", details, force_fix)
        
    def _create_initial_vl50(self, site:Site, status:str, alloc_gw:bool, details:bool=False, force_fix:bool=False) -> Prefix:
        return self._create_initial_vlan(site, 28, status, 50, "OBS", 'vl50_root_pfx_alloc', "BVPN_VLAN50", 
                                  { 'sdw_vpn_enable': "vpnoff", 'dhcp_dhcp_mode':'disabled', "meraki_visible":False}, 
                                  alloc_gw, "OBS router", details, force_fix)

    def _create_initial_vlan(self, site:Site, mask_length:int, status:str, vlan_id:int, name_slug:str, 
                             pfx_alloc_cf_name:str, friendly_name:str, pfx_cf_data:dict, alloc_gw:bool,
                             gw_name:str,
                             details:bool=False, force_fix:bool=False)->Prefix:
        # Extract this vlan root prefix allocation range
        root_pfx_alloc=self._get_site_alloc_pfx_from_tenantgroup_cf(site, pfx_alloc_cf_name, friendly_name, details)
        # Try to find an existing prefix in this root prefix alloc range on that site
        pfs=Prefix.objects.filter(site__id=site.pk).filter(prefix__net_contained=root_pfx_alloc.prefix)
        # We cannot sort between several prefixes
        if pfs.count()>1:
            raise Exception(f"Error : there are several existing prefixes on site {site} contained in the root allox prefix {root_pfx_alloc} ! ")
        p:Prefix
        save:bool=False
        if pfs.count()==1:
            p=pfs[0]
            # We cannot fix incorrect mask length for now
            if p.mask_length!=mask_length:
                raise Exception(f"Cannot fix existing mask length (existing={p.mask_length}, asked={mask_length}) ")
            if not force_fix:
                self.logger.log_info(f"Skipping existing prefix {p}")
                return p  
            self.logger.log_info(f"Force fixing existing prefix {p}")    
            p.snapshot()
            if p.status!=status:
                p.status=status
                save=True            
        else:
            # Try allocate 
            p=self._try_allocate_pfx(root_pfx_alloc, mask_length, details)
            p.status=status
            p.scope=site
            save=True

        rl:Role=Role.objects.get(slug=name_slug.lower())
        if p.role!=rl:
            p.role=rl # type: ignore
            save=True
        val=rl.description
        if p.description!=val:
            p.description=val
            save=True
        vl:VLAN=self._get_or_create_vlan(site, vlan_id, name_slug.upper(), name_slug.lower(), "IT", force_fix, status)
        if p.vlan!=vl:
            p.vlan=vl # type: ignore
            save=True
        val=site.tenant
        if p.tenant!=val:
            p.tenant=val
            save=True
        for k,v in pfx_cf_data.items():
            if p.custom_field_data.get(k)!=v:
                p.custom_field_data[k]=v
                save=True
        if save:
            p.full_clean()
            p.save()
            self.logger.log_success(f"Created (or fixed) prefix [{p}]({p.get_absolute_url()}), status={p.status}")
        else:
            self.logger.log_info(f"Nothing to do on prefix [{p}]({p.get_absolute_url()}), status={p.status}")
        if alloc_gw:
            self._create_or_fix_prefix_gw(p, gw_name, force_fix, details)
        return p

    def _create_or_fix_prefix_gw(self, p:Prefix, gw_name:str, force_fix:bool, details:bool=False, local_vrf:VRF|None=None):
        gw=f"{netaddr.IPAddress(p.prefix.last - 1)}/{p.prefix.prefixlen}"
        if details:
            self.logger.log_debug(f"Computed GW IP =  {gw}")
        ips=IPAddress.objects.filter(address=gw)
        if local_vrf is not None:
            ips=ips.filter(vrf__id=local_vrf.pk)
        ipa:IPAddress
        save:bool=False
        if ips.count()>0:
            if details:
                self.logger.log_debug(f"Found existing GW IP(s) {ips}")
            if not force_fix:
                raise Exception(f"The computed GW address {gw} is already used : [{ips[0]}]({ips[0].get_absolute_url()})")
            ipa=ips[0]
            ipa.snapshot()
        else:    
            ipa=IPAddress()
            ipa.address=gw
            if local_vrf is not None:
                ipa.vrf=local_vrf # type: ignore
            val="created by netbox_tools._create_initial_vlan"
            if ipa.comments!=val:
                ipa.comments=val
                save=True                
        val=gw_name
        if ipa.description!=val:
            ipa.description=val
            save=True
        val='reserved'
        if ipa.status!=val:
            ipa.status=val
            save=True     
        val=p.tenant
        if ipa.tenant!=val:
            ipa.tenant=val
            save=True    
        if save:
            ipa.full_clean()
            ipa.save()
            self.logger.log_success(f"Created or fixed GW '{gw_name}' [{ipa}]({ipa.get_absolute_url()}), status={ipa.status}")
        else:
            self.logger.log_success(f"Nothing to do on GW '{gw_name}' [{ipa}]({ipa.get_absolute_url()}), status={ipa.status}")
        
