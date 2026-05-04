


class MerakiConstants():
    action_site_status=['staging','starting','active','decommissioning','test-poc']
    active_route_statuses=['active','noncompliant','decommissioning']
    upstream_dns='upstream_dns'
    dev_types=["appliance","camera","cellularGateway","secureConnect","sensor","switch","systemsManager","wireless"]
    dev_type_appliance="appliance"
    dev_type_wireless="wireless"



class MerakiS2SHub():
    def __init__(self, hub:dict):
        self._id:str=hub['hubId']
        self._dflt:bool=hub['useDefaultRoute']
    @property
    def id(self) -> str:
        return self._id
    @property
    def dflt(self) -> bool:
        return self._dflt
    def __str__(self):
        return f"hub=(id:{self.id}/dflt:{self.dflt})"
    def __repr__(self):
        return f"MerakiS2SHub(id={self.id},dflt={self.dflt})"
    def _to_dict(self):
        data={}
        data["hubId"]=self.id
        data["useDefaultRoute"]=self.dflt
        return data


class MerakiS2SSubnet():
    def __init__(self, subnet:dict):
        self._cidr:str=subnet['localSubnet']
        self._vpn:bool=subnet['useVpn']
    @property
    def cidr(self) -> str:
        return self._cidr
    @property
    def vpn(self) -> bool:
        return self._vpn
    @vpn.setter
    def vpn(self, value:bool):
        self._vpn=value
    def __str__(self):
        return f"subnet=(cidr:{self.cidr}/vpn:{self.vpn})"
    def __repr__(self):
        return f"MerakiS2SSubnet(cidr={self.cidr},vpn={self.vpn})"
    def _to_dict(self):
        data={}
        data["localSubnet"]=self.cidr
        data["useVpn"]=self.vpn
        return data


class MerakiS2SInfo():
    def __init__(self, org:str, net:str, name:str, bound:bool, data):
        self._id:str=net
        self._orgId:str=org
        self._name:str=name
        self._bound=bound
        self._mode:str="none" if data.get('mode') is None else data.get('mode')
        self._hubs:list[MerakiS2SHub]=[]
        self._subnets:list[MerakiS2SSubnet]=[]
        if not self.site_to_site_enabled():
            return
        for y in data['hubs']:
            self._hubs.append(MerakiS2SHub(y))
        for y in data['subnets']:
            self._subnets.append(MerakiS2SSubnet(y))
    @property
    def id(self) -> str:
        return self._id
    @property
    def orgId(self) -> str:
        return self._orgId
    @property
    def name(self) -> str:
        return self._name    
    @property
    def bound(self) -> bool:
        return self._bound
    @property
    def mode(self) -> str:
        return self._mode
    def site_to_site_enabled(self) -> bool:
        return self._mode!="none"
    def get_meraki_hubs_list(self) -> list[dict]:
        return [hub._to_dict() for hub in self._hubs]
    def get_meraki_subnets_list(self) -> list[dict]:
        return [subnet._to_dict() for subnet in self._subnets]
    def __str__(self):
        return f"org: {self.orgId} - net: {self.id} - bound : {self.bound}"
    def __repr__(self):
        return f"MerakiS2SInfo(id={self.orgId},net.id={self.id},net.name={self.name},bound={self.bound},mode={self.mode},hubs={self._hubs},subnets={self._subnets})"


class MerakiVPNHubs():
    def __init__(self):
        self._nets:dict[str,MerakiS2SInfo]={}
    @property
    def nets(self):
        return self._nets
    def add_net(self, merNet:MerakiS2SInfo):
        #print(f"{merNet}-{merNet.id}")
        if self._nets.get(merNet.id) is not None:
            raise Exception(f"NetworkID is already present : {merNet.id}")
        self._nets[merNet.id]=merNet
    def has_net_id(self, id):
        return id in self._nets.keys
    def has_site_to_site_nets(self) -> bool:
        return len(self.get_site_to_site_nets())>0
    def has_several_site_to_site_nets(self) -> bool:
        return len(self.get_site_to_site_nets())>1
    def get_all_nets(self) -> list[MerakiS2SInfo]:
        ret:list[MerakiS2SInfo]=[]
        for v in self._nets.values():
            ret.append(v)
        return ret
    def get_site_to_site_nets(self) -> list[MerakiS2SInfo]:
        ret:list[MerakiS2SInfo]=[]
        for v in self._nets.values():
            if v.site_to_site_enabled:
                ret.append(v)
        return ret
    def __str__(self):
        return f"MerakiVPNHubs : {self._nets}"

    
class MerakiNetwork():

    def __init__(self, org_id, net_id, net_name, net_isbound, net_tz, net_tags):
        self._id=net_id
        self._orgId=org_id
        self._bound=net_isbound
        self._tz=net_tz
        self._appliances:dict[str,str]={}
        self._access_points:dict[str,dict]={}
        self._name:str=net_name
        self._ids_mode:str=None
        self._amp_mode:str=None
        self._ctflt:dict=None
        self._tags=net_tags
    @property
    def id(self) -> str:
        return self._id
    @property
    def bound(self) -> bool:
        return self._bound
    @property
    def appliances(self) -> dict[str,str]:
        return self._appliances
    @property
    def orgId(self) -> str:
        return self._orgId
    @property
    def name(self) -> str:
        return self._name
    @property
    def has_appliances(self) -> bool:
        return len(self._appliances)>0
    @property
    def has_access_points(self) -> bool:
        return len(self._access_points)>0
    @property
    def tags(self) -> list[str]:
        ret:list[str]=[]
        x:str=None
        for x in self._tags:
            ret.append(x)
        ret.sort()
        return ret    
    @property
    def netbox_tags(self) -> list[str]:
        ret:list[str]=[]
        x:str=None
        for x in self._tags:
            if x.startswith("NETBOX_"):
                ret.append(x)
        ret.sort()
        return ret
    def add_tag(self, tag:str)->bool:
        if tag not in self._tags:
            self._tags.append(tag)
            return True
        return False
    def del_tag(self, tag:str)->bool:
        if tag in self._tags:
            self._tags.remove(tag)
            return True
        return False
    def add_appliance(self,  serial, org_id):
        self._appliances[serial]=org_id
    def add_access_point(self, access_point):
        self._access_points[access_point['serial']]=access_point
    def __str__(self):
        return f"org: {self.orgId} - net: {self.id} - bound : {self.bound}"
    def __repr__(self):
        return f"MerakiNet(id={self.orgId},net.id={self.id},net.name={self.name},bound={self.bound},\
            tz={self._tz},appliances={self.appliances},ids={self._ids_mode},amp={self._amp_mode},ctflt={self._ctflt})"


class MerakiNets():
    def __init__(self):
        self._nets:dict[str,MerakiNetwork]={}
        self._slugs:dict[str:list[MerakiNetwork]]={}
        self._orgs:dict[str:list[MerakiNetwork]]={}
    @property
    def nets(self):
        return self._nets
    def add_net(self, merNet:MerakiNetwork, slug:str=None):
        if self._nets.get(merNet.id) is not None:
            raise Exception(f"NetworkID is already present : {merNet.id}")
        self._nets[merNet.id]=merNet
        if merNet.orgId not in self._orgs.keys():
            self._orgs[merNet.orgId]=[]
        self._orgs[merNet.orgId].append(merNet)
        if slug is not None:
            if slug not in self._slugs.keys():
                self._slugs[slug]=[]
            self._slugs[slug].append(merNet)
    def get_net(self, id:str)->MerakiNetwork:
        return self._nets.get(id)
    def get_net_ids(self):
        return self._nets.keys()
    def get_orgs_ids(self):
        return self._orgs.keys()
    def has_net_id(self, id):
        return id in self._nets.keys()
    def has_appliances_in_several_nets(self) -> bool:
        return len(self.get_appliance_nets())>1
    def get_all_nets(self) -> list[MerakiNetwork]:
        ret:list[MerakiNetwork]=[]
        for v in self._nets.values():
            ret.append(v)
        return ret
    def has_appliances(self) -> bool:
        for v in self._nets.values():
            if v.has_appliances:
                return True
        return False
    def get_appliance_nets(self) -> list[MerakiNetwork]:
        ret:list[MerakiNetwork]=[]
        for v in self._nets.values():
            if v.has_appliances:
                ret.append(v)
        return ret
    def has_access_points(self) -> bool:
        for v in self._nets.values():
            if v.has_access_points:
                return True
        return False
    def get_access_points_nets(self) -> list[MerakiNetwork]:
        ret:list[MerakiNetwork]=[]
        for v in self._nets.values():
            if v.has_access_points:
                ret.append(v)
        return ret
    def __str__(self):
        return f"MerakiNets : {self._nets}"
