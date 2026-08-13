import re

from django.db import transaction
from django.utils.timezone import now as django_now
from zoneinfo import ZoneInfo

from dcim.models import Device, DeviceType, Region, Site, SiteGroup
from dcim.models.devices import DeviceRole
from netbox.context import current_request
from sop_infra.models.infra import SopDeviceSetting, SopInfra
from sop_infra.models.sopmeraki import SopMerakiDash, SopMerakiDevice, SopMerakiNet, SopMerakiOrg, SopMerakiSwitchStack
from sop_infra.utils.mixins import JobRunnerLogMixin
from sop_infra.utils.umbrella_utils import SopUmbrellaUtils
from sop_utils.arrays import ArrayUtils
from sop_utils.misc import SopUtils
from sop_utils.regexps import SopRegExps
from tenancy.models import Tenant, TenantGroup


import meraki
from django.contrib import messages

from utilities.exceptions import AbortRequest, AbortScript

class SopMerakiRegexps:

    meraki_sitename_str = r"^.*--(?:(STOCK-.*|[^ -]+)(|[ -]+[oO][lL][dD].*|[ -].*))$"
    meraki_sitename_re = re.compile(meraki_sitename_str)

    meraki_serial_txt = r'[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}'
    meraki_serial_reg = re.compile(meraki_serial_txt)
    
    meraki_single_serial_txt = r'^(' + meraki_serial_txt + r')$'
    meraki_single_serial_reg = re.compile(meraki_single_serial_txt)

    meraki_padded_serial_txt = r'^\s*(' + meraki_serial_txt + r')\s*$'
    meraki_padded_serial_reg = re.compile(meraki_padded_serial_txt)

    meraki_list_of_serials_txt = r'^(?:[\s,]*' + meraki_serial_txt + r'[\s,]*)+$'
    meraki_list_of_serials_reg = re.compile(meraki_list_of_serials_txt)


class SopMerakiUtils:

    # DEV TYPES:
    # 'appliance', 'camera', 'campusGateway', 'cellularGateway', 'secureConnect', 'sensor', 'switch', 'systemsManager', 'wireless' or 'wirelessController'
    DEV_TYPE_MX = "appliance"
    DEV_TYPE_MV = "camera"
    DEV_TYPE_MS = "switch"
    DEV_TYPE_MR = "wireless"

    __parsed: bool = False
    __meraki_api_keys: dict[str, str] = {}

    # ---------------------------------------------
    #region PLOMBERIE

    @classmethod
    def try_parse_configuration(cls):
        # parse all configuration.py informations
        from django.conf import settings

        infra_config = settings.PLUGINS_CONFIG.get("sop_infra")
        if infra_config is None:
            raise Exception("No sop_infra in .PLUGINS_CONFIG !")
        sopmeraki_config = infra_config.get("sopmeraki")
        if sopmeraki_config is None:
            raise Exception("No sopmeraki in sop_infra PLUGINS_CONFIG key !")
        cls.__meraki_api_keys = sopmeraki_config.get("api_keys")
        if cls.__meraki_api_keys is None:
            raise Exception("No sopmeraki/api_keys plugin config key !")
        cls.__parsed = True

    @classmethod
    def get_ro_api_key_for_dash_name(cls, name: str) -> str:
        return cls.get_api_key_for_dash_name(name, "RO")

    @classmethod
    def get_rw_api_key_for_dash_name(cls, name: str) -> str:
        return cls.get_api_key_for_dash_name(name, "RW")

    @classmethod
    def get_api_key_for_dash_name(cls, name: str, type: str) -> str:
        if type not in ("RO", "RW"):
            raise Exception("API key type must be 'RO' or 'RW'")
        if not cls.__parsed:
            cls.try_parse_configuration()
        keys: dict[str, str] = cls.__meraki_api_keys.get(name)  # type: ignore
        if keys is None:
            raise Exception(f"No keys for dashboard '{name}'")
        return keys.get(type, "")

    @classmethod
    def connect(cls, dash_name: str, api_url: str, simulate: bool = False) -> meraki.DashboardAPI:
        if simulate:
            api_key = cls.get_ro_api_key_for_dash_name(dash_name)
        else:
            api_key = cls.get_rw_api_key_for_dash_name(dash_name)
        if api_key is None or api_key.strip() == "":
            raise Exception(f"APIKEY is empty ! ")
        return meraki.DashboardAPI(
            api_key=api_key, base_url=api_url, suppress_logging=True, simulate=simulate, maximum_retries=10,
        )

    @classmethod
    def connect_by_name(cls, dash_name: str, simulate: bool = False) -> meraki.DashboardAPI:
        smds=SopMerakiDash.objects.filter(nom=dash_name)
        if not smds.exists():
            raise Exception(f"Unknown dashboard name {dash_name} ! ")
        return cls.connect(dash_name, smds[0].api_url, simulate)


    #endregion



    # ---------------------------------------------
    #region DASH SYNC

    @classmethod
    def refresh_dashboards(
        cls, log: JobRunnerLogMixin, simulate: bool, dashs: list, details: bool = False
    ):
        if dashs is None or len(dashs) == 0:
            dashs = SopMerakiDash.objects.all()  # type: ignore
        smd:SopMerakiDash
        for smd in dashs:
            if log:
                log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
            conn = cls.connect(smd.nom, smd.api_url, simulate)
            if log:
                log.info(f"Trying to refresh '{smd.nom}'")
            SopMerakiDashUtils.refresh_from_meraki(smd, conn, log, details)

    @classmethod
    def refresh_organizations(
        cls, log: JobRunnerLogMixin, simulate: bool, orgs: list, details: bool = False
    ):
        if orgs is None or len(orgs) == 0:
            orgs = SopMerakiOrg.objects.all()  # type: ignore
        smo:SopMerakiOrg
        for smo in orgs:
            smd:SopMerakiDash=smo.dash
            if log:
                log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
            conn = cls.connect(smd.nom, smd.api_url, simulate)
            if log:
                log.info(f"Trying to refresh '{smo.nom}'")
            SopMerakiOrgUtils.refresh_from_meraki(smo, conn, smd, log, details)

    @classmethod
    def refresh_networks(
        cls, log: JobRunnerLogMixin, simulate: bool, nets: list[SopMerakiNet], details: bool = False
    ):
        if nets is None or len(nets) == 0:
            nets = SopMerakiNet.objects.all()  # type: ignore
        smn:SopMerakiNet
        for smn in nets:
            smo:SopMerakiOrg=smn.org
            smd:SopMerakiDash=smo.dash
            if log:
                log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
            conn = cls.connect(smd.nom, smd.api_url, simulate)
            if log:
                log.info(f"Trying to refresh '{smn.nom}'")
            SopMerakiNetUtils.refresh_from_meraki(smn, conn, smo, log, details)

    @classmethod
    def refresh_infras(
        cls, log: JobRunnerLogMixin, simulate: bool, infras: list[SopInfra], details: bool = False
    ):
        if infras is None or len(infras) == 0:
            infras = SopInfra.objects.all()  # type: ignore
        soi:SopInfra
        for soi in infras:
            smo:SopMerakiOrg=SopMerakiUtils.get_site_meraki_org(soi.site)
            if smo is None:
                continue
            smd:SopMerakiDash=smo.dash
            if log:
                log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
            conn = cls.connect(smd.nom, smd.api_url, simulate)
            nets=conn.organizations.getOrganizationNetworks(smo.meraki_id, total_pages=-1)
            ids:list[str]=list()
            for net_data in nets:
                site_name=SopMerakiUtils.extractSiteName(net_data.get("name"))
                if site_name==soi.site.slug:
                    ids.append(net_data["id"])
                    if not SopMerakiNet.objects.filter(meraki_id=net_data["id"]).exists():
                        if log:
                            log.info(f"Creating new NET for '{net_data['id']}' on ORG '{smo.nom}'...")
                        smn = SopMerakiNet()
                    else:
                        smn = SopMerakiNet.objects.get(meraki_id=net_data["id"])
                    SopMerakiNetUtils.refresh_from_meraki_data(smn, conn, net_data, smo, log, details)
            # Cleanup former nets that aren't here anymore
            smn:SopMerakiNet
            for smn in soi.site.meraki_nets.all():
                if smn.meraki_id not in ids:
                    log.info(f"Deleting inexistent NET {smn.meraki_id} / {smn.nom}")
                    smn.delete()
                


    @classmethod
    def update_connectivity_statuses_dashboards(
        cls, log: JobRunnerLogMixin, simulate: bool, dashs: list, details: bool = False
    ):
        if dashs is None or len(dashs) == 0:
            dashs = SopMerakiDash.objects.all()  # type: ignore
        smd:SopMerakiDash
        for smd in dashs:
            if log:
                log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
            conn = cls.connect(smd.nom, smd.api_url, simulate)
            if log:
                log.info(f"Trying to refresh '{smd.nom}'")
            SopMerakiDashUtils.update_uplink_statuses(smd, conn, log, details)
            SopMerakiDashUtils.update_vpn_statuses(smd, conn, log, details)
            
    @classmethod
    def update_connectivity_statuses_organizations(
        cls, log: JobRunnerLogMixin, simulate: bool, orgs: list, details: bool = False
    ):
        if orgs is None or len(orgs) == 0:
            orgs = SopMerakiOrg.objects.all()  # type: ignore
        smo:SopMerakiOrg
        for smo in orgs:
            smd:SopMerakiDash=smo.dash
            if log:
                log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
            conn = cls.connect(smd.nom, smd.api_url, simulate)
            if log:
                log.info(f"Trying to refresh '{smo.nom}'")
            SopMerakiOrgUtils.update_uplink_statuses(smo, conn, smd, log, details)
            SopMerakiOrgUtils.update_vpn_statuses(smo, conn, smd, log, details)
            
    @classmethod
    def update_connectivity_statuses_nets(
        cls, log: JobRunnerLogMixin, simulate: bool, nets: list, details: bool = False
    ):
        if nets is None or len(nets) == 0:
            nets = SopMerakiNet.objects.all()  # type: ignore
        smn:SopMerakiNet
        for smn in nets:
            smd:SopMerakiDash=smn.org.dash
            if log:
                log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
            conn = cls.connect(smd.nom, smd.api_url, simulate)
            if log:
                log.info(f"Trying to refresh '{smn.nom}'")
            SopMerakiNetUtils.update_uplink_statuses(smn, conn, smd, log, details)
            SopMerakiNetUtils.update_vpn_statuses(smn, conn, smd, log, details)

    #endregion



    # ---------------------------------------------
    #region ACTIONS

    @classmethod
    def create_meraki_networks(
        cls, log: JobRunnerLogMixin, simulate: bool, sopinfra: SopInfra, details: bool = False
    ):
        if log and details:
            log.log_debug(f"create_meraki_networks for site {sopinfra}")
        site:Site=sopinfra.site
        # Check site sopinfra for existing nets
        if site.meraki_nets.exists():  # type: ignore
            if log and details:
                raise AbortScript(f"SopMerakiNets already exist for site {site}...")
        # Get claim org from region hierarchy
        region: Region = site.region  # type: ignore
        org_id: int = None  # type: ignore
        copy_from_id: int = None  # type: ignore
        while org_id is None and region is not None:
            org_id = region.custom_field_data.get("meraki_org")
            copy_from_id = region.custom_field_data.get("meraki_tmplnet_sdwan")
            region = region.parent  # type: ignore
        if org_id is None or copy_from_id is None:
            if log:
                log.log_failure(
                    f"Unable to determine creation settings for site {site} :  {org_id=}, {copy_from_id=}"
                )
            return
        if log and details:
            log.log_debug(
                f"create_meraki_networks : {org_id=}, {copy_from_id=} for {site}"
            )
        # Get con from dash from org
        org = SopMerakiOrg.objects.get(pk=org_id)
        copy_from = SopMerakiNet.objects.get(pk=copy_from_id)
        if copy_from.org != org:
            if log:
                log.log_failure(
                    f"copy_from org != creation org  {org=} VS {copy_from.org=}"
                )
            return
        smd: SopMerakiDash = org.dash
        if log:
            log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
        conn = cls.connect(smd.nom, smd.api_url, simulate)
        # Calc names
        sdwan_name = f"{site.group.parent.name}-{site.region.name}-{site.tenant.group.name}@--{site.name}"  # type: ignore
        switch_name = f"{site.group.parent.name}-{site.region.name}-{site.tenant.group.name}--{site.name}"  # type: ignore
        if log and details:
            log.log_debug(
                f"create_meraki_networks : network names -> {sdwan_name=}, {switch_name=}"
            )
        # Create missing ones
        sdwan = conn.organizations.createOrganizationNetwork(
            org.meraki_id,
            name=sdwan_name,
            copyFromNetworkId=copy_from.meraki_id,
            timeZone=f"{copy_from.timezone}",
            productTypes=["appliance"],
            tags=SopMerakiUtils.calc_site_netbox_tags(site),
        )
        if log and details:
            log.log_debug(f"created SDWAN network {sdwan=}")
        SopMerakiNetUtils.create_or_refresh(conn, sdwan, org, log, details)
        switches = conn.organizations.createOrganizationNetwork(
            org.meraki_id,
            name=switch_name,
            productTypes=["switch", "wireless"],
            tags=SopMerakiUtils.calc_site_netbox_tags(site),
        )
        if log and details:
            log.log_debug(f"created Switch + Wifi network {switches=}")
        SopMerakiNetUtils.create_or_refresh(conn, switches, org, log, details)
        bind = conn.networks.bindNetwork(switches["id"], "L_731271989494293752")
        if log and details:
            log.log_debug(f"bound network {bind=}")
        SopMerakiNetUtils.create_or_refresh(conn, bind, org, log, details)
        if log:
            log.log_success(f"Done creating networks !")


    @classmethod
    def claim_devices_to_inventory(
        cls,  log:JobRunnerLogMixin, simulate: bool, smo: SopMerakiOrg, serials:list[str]
    )-> list[SopMerakiDevice]:
        print(f"SopMerakiUtils.claim_devices_to_inventory : claiming {len(serials)} serials to org {smo} inventory")
        if len(serials)==0:
            return list()
        smd:SopMerakiDash = smo.dash
        conn = cls.connect(smd.nom, smd.api_url, simulate)       
        return SopMerakiDeviceUtils.claim_devices_to_inventory(smo, serials, conn, log, False)


    # @classmethod
    # def claim_devices_to_infra(
    #     cls,  log:JobRunnerLogMixin, simulate: bool, smo: SopMerakiOrg, serials:list[str]
    # )-> list[SopMerakiDevice]:
    #     print(f"SopMerakiUtils.claim_devices_to_infra : claiming {len(serials)} serials to org {smo} inventory")
    #     smd:SopMerakiDash = smo.dash
    #     conn = cls.connect(smd.nom, smd.api_url, simulate)       
    #     return SopMerakiDeviceUtils.claim_devices_to_inventory(smo, serials, conn, log, False)



    @classmethod
    def move_devices_to_network(
        cls,  log:JobRunnerLogMixin, simulate: bool, smn:SopMerakiNet, devices:list[SopMerakiDevice], force:bool 
    )-> list[SopMerakiDevice]:
        print(f"SopMerakiUtils.move_devices_to_network : claiming {len(devices)} devices to {smn} net")
        if len(devices)==0:
            return list()
        if smn is None:
            raise AbortRequest(f"Destination Meraki Network is not set !")
        smd:SopMerakiDash = smn.org.dash
        conn = cls.connect(smd.nom, smd.api_url, simulate)       
        return SopMerakiDeviceUtils.move_devices_to_network(smn, devices, force, conn, log, False)


    @classmethod
    def connect_to_umbrella_dash(
        cls, log: JobRunnerLogMixin, simulate: bool, site: Site, api_keys:dict[str,str], details: bool = False
    ):
        if log and details:
            log.log_debug(f"connecting site {site.name} to umbrella")
        # Find Meraki Network(s) with appliances for this site
        app_nets:list[SopMerakiNet]=SopMerakiNetUtils.get_appliance_networks(site)
        # Loop on those
        net:SopMerakiNet
        for net in app_nets:
            smo:SopMerakiOrg = net.org
            smd:SopMerakiDash = smo.dash
            if log:
                log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
            conn = cls.connect(smd.nom, smd.api_url, simulate)       
            # Enroll the Meraki Network in Umbrella
            conn.appliance.connectNetworkApplianceUmbrellaAccount(networkId=net.meraki_id, api=api_keys)
            if log :
                log.log_success(f"connected network {net.nom} to Umbrella")
      

    @classmethod
    def enable_umbrella_protection(
        cls, log: JobRunnerLogMixin, simulate: bool, site: Site, details: bool = False
    ):
        if log and details:
                log.log_debug(f"enabling Umbrella protection for site {site.name}")
        # Find Meraki Network(s) with appliances for this site
        app_nets:list[SopMerakiNet]=SopMerakiNetUtils.get_appliance_networks(site)
        # Loop on those
        net:SopMerakiNet
        for net in app_nets:
            smo:SopMerakiOrg = net.org
            smd:SopMerakiDash = smo.dash
            if log:
                log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
            conn = cls.connect(smd.nom, smd.api_url, simulate)       
            # Try enable Umbrella protection
            try:
                conn.appliance.protectionNetworkApplianceUmbrella(networkId=net.meraki_id, enabled=True)
            except meraki.exceptions.APIError as ex:
                if ex.status==405:
                    if log :
                        log.log_debug(f"Umbrella network protection was already enabled for network {net.nom}")
                else:
                    raise ex  
            else:
                if log :
                    log.log_success(f"enabled Umbrella network protection for network {net.nom}")
            # Set exclusion domains
            excluded_domains=SopUmbrellaUtils.get_umbrella_excluded_domains(site)
            conn.appliance.exclusionsNetworkApplianceUmbrellaDomains(networkId=net.meraki_id, domains=excluded_domains)
            if log :
                log.log_success(f"added Umbrella domain exclusions {excluded_domains} for network {net.nom}")
       

    # @classmethod
    # def claim_meraki_device(
    #     cls, log: JobRunnerLogMixin, simulate: bool, site: Site, serial:str, details: bool = False
    # ):
    #     if log and details:
    #         log.log_debug(f"claim_meraki_device - {site=} {serial=}")
    #     # Get claim org from region hierarchy
    #     region: Region = site.region  # type: ignore
    #     org_id: int = None  # type: ignore
    #     while org_id is None and region is not None:
    #         org_id = region.custom_field_data.get("meraki_org")
    #         region = region.parent  # type: ignore
    #     if org_id is None :
    #         if log:
    #             log.log_failure(
    #                 f"Unable to determine claim settings for site {site} :  {org_id=}"
    #             )
    #         return
    #     if log and details:
    #         log.log_debug(
    #             f"create_meraki_networks : {org_id=}} for {site}"
    #         )
    #     # Get con from dash from org
    #     org = SopMerakiOrg.objects.get(pk=org_id)
    #     copy_from = SopMerakiNet.objects.get(pk=copy_from_id)
    #     if copy_from.org != org:
    #         if log:
    #             log.log_failure(
    #                 f"copy_from org != creation org  {org=} VS {copy_from.org=}"
    #             )
    #         return
    #     smd: SopMerakiDash = org.dash
    #     if log:
    #         log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
    #     conn = cls.connect(smd.nom, smd.api_url, simulate)
    #     # Calc names
    #     sdwan_name = f"{site.group.parent.name}-{site.region.name}-{site.tenant.group.name}@--{site.name}"
    #     switch_name = f"{site.group.parent.name}-{site.region.name}-{site.tenant.group.name}--{site.name}"
    #     if log and details:
    #         log.log_debug(
    #             f"create_meraki_networks : network names -> {sdwan_name=}, {switch_name=}"
    #         )
    #     # Create missing ones
    #     sdwan=conn.organizations.createOrganizationNetwork(
    #         org.meraki_id,
    #         name=sdwan_name,
    #         copyFromNetworkId=copy_from.meraki_id,
    #         timeZone=f"{copy_from.timezone}",
    #         productTypes=["appliance"],
    #         tags=SopMerakiUtils.calc_site_netbox_tags(site)
    #     )
    #     if log and details:
    #         log.log_debug(
    #             f"created SDWAN network {sdwan=}"
    #         )
    #     SopMerakiNetUtils.create_or_refresh(conn, sdwan, org, log)
    #     switches=conn.organizations.createOrganizationNetwork(
    #         org.meraki_id,
    #         name=switch_name,
    #         productTypes=["switch","wireless"],
    #         tags=SopMerakiUtils.calc_site_netbox_tags(site)
    #     )
    #     if log and details:
    #         log.log_debug(
    #             f"created Switch + Wifi network {switches=}"
    #         )
    #     SopMerakiNetUtils.create_or_refresh(conn, switches, org, log)
    #     bind=conn.networks.bindNetwork(switches["id"], "L_731271989494293752")
    #     if log and details:
    #         log.log_debug(
    #             f"bound network {bind=}"
    #         )
    #     SopMerakiNetUtils.create_or_refresh(conn, bind, org, log)
    #     if log:
    #         log.log_success(
    #             f"Done creating networks !"
    #         )
    
    #endregion


    # ---------------------------------------------
    #region GENERIC UTILS

    @staticmethod
    def clean_serials_txt(serials:str)->list[str]:
        # Check if it matches the general form
        if not SopMerakiRegexps.meraki_list_of_serials_reg.match(serials):
            return None
        # replace whitespace and commas by a single space
        serials_txt = re.sub(r"[\s,]+", " ", serials)
        # trim the string
        serials_txt = serials_txt.strip()
        # split it by spaces
        serials_list = re.split(r" +", serials_txt)
        # reparse the whole thing properly
        return SopMerakiUtils.clean_serials_list(serials_list)

    @staticmethod
    def clean_serials_list(serials:list[str])->list[str]:
        if serials is None:
            return None
        clean_serials=list()
        for serial in serials:
            if (m:=SopMerakiRegexps.meraki_padded_serial_reg.match(serial)):
                clean_serials.append(m.group(1))
        if len(clean_serials)>0:
            return clean_serials
        return None

    @staticmethod
    def extractSiteName(name):
        m = SopMerakiRegexps.meraki_sitename_re.match(f"{name}")
        if m is None:
            return None
        return m.group(1).lower()

    @staticmethod
    def calc_site_netbox_tags(site: Site) -> list[str]:
        ret: list[str] = []
        for st in site.tags.all():
            ret.append(f"NETBOX_ST_{st.slug}")
        t: Tenant = site.tenant  # type: ignore
        ret.append(f"NETBOX_TENANT_{t.slug}")
        tg: TenantGroup = t.group  # type: ignore
        while tg is not None:
            ret.append(f"NETBOX_TG_{tg.slug}")
            tg = tg.parent  # type: ignore
        sg: SiteGroup = site.group
        while sg is not None:
            ret.append(f"NETBOX_SG_{sg.slug}")
            sg = sg.parent
        r: Region = site.region
        while r is not None:
            ret.append(f"NETBOX_RG_{r.slug}")
            r = r.parent
        ret.sort()
        return ret

    @staticmethod
    def only_netbox_tags(tags: list[str]) -> list[str]:
        ret: list[str] = []
        for x in tags:
            if x.startswith("NETBOX_"):
                ret.append(x)
        ret.sort()
        return ret

    @staticmethod
    def only_non_netbox_tags(tags: list[str]) -> list[str]:
        ret: list[str] = []
        for x in tags:
            if not (x.startswith("NETBOX_")):
                ret.append(x)
        ret.sort()
        return ret

    @staticmethod
    def get_site_meraki_org_id(site: Site) -> int | None:
        """
        Get claim SopMerakiOrg ID from region hierarchy
        """
        region: Region = site.region  # type: ignore
        org_id: int | None = None
        while org_id is None and region is not None:
            org_id = region.custom_field_data.get("meraki_org")
            region = region.parent  # type: ignore
        return org_id

    @staticmethod
    def get_site_meraki_org(site: Site)->SopMerakiOrg|None:
        """
        Get claim SopMerakiOrg from region hierarchy
        """
        org_id: int | None = SopMerakiUtils.get_site_meraki_org_id(site)
        if org_id is None:
            return None
        orgs = SopMerakiOrg.objects.filter(id=org_id)
        if not orgs.exists():
            return None
        return orgs[0]

    @staticmethod
    def check_create_sopdevicesetting(instance: Device)->SopDeviceSetting|None:
        """
        Create a SopDeviceSetting for the device if supported
        """
        if instance.device_type is None:
            return None
        dt:DeviceType=instance.device_type
        if not dt.model.startswith("Meraki "):
            return None
        if not dt.model.startswith("Meraki MS"):
            return None

        sdss = SopDeviceSetting.objects.filter(device=instance)

        sds:SopDeviceSetting
        if sdss.exists():
            sds=sdss[0]
            sds.make_compliant()
            sds.save()
            return sds

        sds = SopDeviceSetting.objects.create(device=instance)
        sds.snapshot()
        sds.make_compliant()
        sds._changelog_message = "SopMerakiUtils.check_create_sopdevicesetting"
        sds.full_clean()
        sds.save()
        try:
            request = current_request.get()
            messages.success(request, f"Created {sds} SopDeviceSetting !") # type: ignore
        except:
            pass
        return sds

    @staticmethod
    def prepare_create_vlan(vlan) -> dict:
        posargs = {"networkId": vlan["networkId"], "id": vlan["id"], "name": vlan["name"]}
        kwargs = {k: v for k, v in vlan.items()}
        del kwargs["networkId"]
        del kwargs["id"]
        del kwargs["name"]
        if "ipv6" in kwargs:
            del kwargs["ipv6"]
        posargs.update(kwargs)
        return posargs

    @staticmethod
    def prepare_put_vlan(vlan) -> dict:
        posargs = {"networkId": vlan["networkId"], "vlanId": vlan["id"]}
        kwargs = {k: v for k, v in vlan.items()}
        del kwargs["networkId"]
        del kwargs["id"]
        if "ipv6" in kwargs:
            del kwargs["ipv6"]
        posargs.update(kwargs)
        return posargs

    @staticmethod
    def prepare_create_route(vlan) -> dict:
        posargs = {
            "networkId": vlan["networkId"],
        }
        kwargs = {k: v for k, v in vlan.items()}
        del kwargs["networkId"]
        if "gatewayVlanId" in kwargs:
            del kwargs["gatewayVlanId"]
        posargs.update(kwargs)
        return posargs

    @staticmethod
    def prepare_put_route(vlan) -> dict:
        posargs = {"networkId": vlan["networkId"], "staticRouteId": vlan["id"]}
        kwargs = {k: v for k, v in vlan.items()}
        del kwargs["networkId"]
        del kwargs["id"]
        if "gatewayVlanId" in kwargs:
            del kwargs["gatewayVlanId"]
        posargs.update(kwargs)
        return posargs

    #endregion




#region OBJECT UTILS

class SopMerakiNetUtils:
    
    # ------------------ UTILS
    @staticmethod
    def get_by_meraki_id(meraki_id: str)->SopMerakiNet:
        nets = SopMerakiNet.objects.filter(meraki_id=meraki_id)
        return nets[0] if nets.exists() else None
    
    @staticmethod
    def create_or_refresh(
        conn: meraki.DashboardAPI,
        net_data:dict,
        org: SopMerakiOrg,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        if not SopMerakiNet.objects.filter(meraki_id=net_data["id"]).exists():
            if log:
                log.info(f"Creating new NET for '{net_data['id']}' on ORG '{org.nom}'...")
            smn = SopMerakiNet()
        else:
            smn = SopMerakiNet.objects.get(meraki_id=net_data["id"])
        SopMerakiNetUtils.refresh_from_meraki_data(smn, conn, net_data, org, log, details)
        return smn

    @staticmethod
    def refresh_from_meraki(
        smn:SopMerakiNet,
        conn: meraki.DashboardAPI,
        org: SopMerakiOrg,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        net_data=conn.networks.getNetwork( smn.meraki_id)
        return SopMerakiNetUtils.refresh_from_meraki_data(smn, conn, net_data, org, log, details)

    @staticmethod
    def refresh_from_meraki_data(
        smn:SopMerakiNet,
        conn: meraki.DashboardAPI,
        net_data : dict,
        org: SopMerakiOrg,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        # cf https://developer.cisco.com/meraki/api-v1/get-organization-networks/
        if log and details:
            log.info(f"Refreshing '{smn.nom}'...")
        save = smn.pk is None
        if smn.nom != net_data["name"]:
            smn.nom = net_data["name"]
            save = True
        if smn.meraki_id != net_data["id"]:
            smn.meraki_id = net_data["id"]
            save = True
        if smn.org_id is None or smn.org != org:  # type: ignore
            smn.org = org
            save = True
        if smn.bound_to_template != net_data["isBoundToConfigTemplate"]:
            smn.bound_to_template = net_data["isBoundToConfigTemplate"]
            save = True
        if smn.meraki_url != net_data["url"]:
            smn.meraki_url = net_data["url"]
            save = True
        if smn.meraki_notes != net_data["notes"]:
            smn.meraki_notes = net_data["notes"]
            save = True
        tz=ZoneInfo(net_data['timeZone'])
        if smn.timezone != tz:
            smn.timezone = tz
            save = True
        if not ArrayUtils.equal_sets(smn.meraki_tags, net_data["tags"]):  # type: ignore
            smn.meraki_tags = net_data["tags"]
            save = True
        if not ArrayUtils.equal_sets(smn.ptypes, net_data["productTypes"]):  # type: ignore
            smn.ptypes = net_data["productTypes"]
            save = True
        slug = SopMerakiUtils.extractSiteName(smn.nom)
        old_site:Site|None=None
        new_site:Site|None=None
        if smn.site_id is not None:
            old_site=Site.objects.get(pk=smn.site_id)
        if slug is None:
            if smn.site_id is not None:
                smn.site_id = None
                if old_site and old_site.meraki_nets:
                    old_site.meraki_nets.remove(old_site)
        elif not Site.objects.filter(slug=slug).exists():
            if smn.site_id is not None:
                smn.site_id = None
                if old_site and old_site.meraki_nets:
                    old_site.meraki_nets.remove(old_site)
        else:
            new_site = Site.objects.get(slug=slug)
            if smn.site_id != new_site.pk:
                if old_site and old_site.meraki_nets:
                    old_site.meraki_nets.remove(old_site)
                smn.site = new_site

        # Prepare Meraki site update
        update_meraki: dict = {}

        # If we have a site , we setup (or fix) certain things
        if smn.site is not None:
            # handle tags
            current_tags: list[str] = SopMerakiUtils.only_non_netbox_tags(
                smn.meraki_tags  # type: ignore
            )
            netbox_tags: list[str] = SopMerakiUtils.calc_site_netbox_tags(smn.site)
            current_tags.extend(netbox_tags)
            if not ArrayUtils.equal_sets(smn.meraki_tags, current_tags):  # type: ignore
                smn.meraki_tags = current_tags
                save = True
                update_meraki["tags"] = smn.meraki_tags
            # handle TZ
            site_tz = smn.site.time_zone
            if site_tz is None:
                site_tz = ZoneInfo("UTC")
            if site_tz != smn.timezone:
                smn.timezone = site_tz
                save = True
                update_meraki["timeZone"] = f"{smn.timezone}"

        # push if needed
        if len(update_meraki.keys()):
            try:
                conn.networks.updateNetwork(smn.meraki_id, **update_meraki)
            except Exception:
                log.failure(
                    f"Exception when updating Meraki Network '{smn.nom}' ({smn.meraki_id}) with dict {update_meraki}"
                )
                raise
            log.success(
                f"Updating Meraki Network '[{smn.nom}]({smn.meraki_url})' : {update_meraki}"
            )

        # only save if something changed
        if save or new_site:
            if save:
                log.success(f"Saving SopMerakiNetwork '[{smn.nom}]'.")
                smn._changelog_message="SopMerakiNetUtils.refresh_from_meraki_data"
                smn.full_clean()
                smn.save()
            if new_site:
                new_site.meraki_nets.add(smn)


        # Refresh devices from this net
        SopMerakiNetUtils.refresh_networks_devices(smn, conn, org, log, details)

        # Refresh stacks from this net
        if "switch" in smn.ptypes :
            for st in conn.switch.getNetworkSwitchStacks(smn.meraki_id):
                SopMerakiSwitchStackUtils.create_or_refresh(conn, st, smn, log, details)

        return save


    @staticmethod
    def refresh_networks_devices(
        smn:SopMerakiNet,
        conn: meraki.DashboardAPI,
        smo: SopMerakiOrg,
        log: JobRunnerLogMixin,
        details: bool):
        # Keep track of devices seen for this network
        devs:dict[str,dict[str,dict]]=dict()
        # INVENTORY - Refresh devices for this net and serials
        for dev in conn.organizations.getOrganizationInventoryDevices(
            smo.meraki_id, networkIds=[smn.meraki_id], total_pages=-1
        ):
            serial=dev['serial']
            d=devs.get(serial, dict())
            d['inv']=dev
            devs[serial]=d
        # ORGANIZATION - Refresh devices for this net and serials
        for dev in conn.organizations.getOrganizationDevices(
            smo.meraki_id, networkIds=[smn.meraki_id], total_pages=-1
        ):
            serial=dev['serial']
            d=devs.get(serial, dict())
            d['org']=dev
            devs[serial]=d
        # LOOP on this data to refresh and keep track of changes
        smdev:SopMerakiDevice
        for serial,d in devs.items():
            inv=d['inv']
            smdev = SopMerakiDeviceUtils.get_by_serial_or_create(serial,inv['name'])
            saved=SopMerakiDeviceUtils.refresh_from_inventory_data(smdev, conn, inv, smo, log, details)
            saved=SopMerakiDeviceUtils.refresh_from_meraki_data(smdev, conn, d['org'], smo, log, details) or saved
            devs[smdev.serial]["saved"]=saved
        # CLEAR network data for devices that are no more in this network
        for smdev in SopMerakiDevice.objects.filter(meraki_netid=smn.meraki_id).exclude(serial__in=devs.keys()):
            smdev.orphan_device()
            d=dict()
            d["saved"]=True
            devs[smdev.serial]=d
        # REFETCH RELATED OBJECTS
        for serial in devs.keys():
            if devs[serial]["saved"]:
                smdev = SopMerakiDeviceUtils.get_by_serial(serial)
                SopMerakiDeviceUtils.relink_related_objects(smdev, log)



    @staticmethod
    def get_appliance_networks(site: Site) -> list[SopMerakiNet]:
        ret: list[SopMerakiNet] = list()
        smns: list[SopMerakiNet] = site.meraki_nets  # type: ignore
        smn:SopMerakiNet
        # loop on the site networks
        for smn in smns.all():
            # skip bound networks
            if smn.bound_to_template:
                continue
            # skip non appliance networks
            if "appliance" not in smn.ptypes:  # type: ignore
                continue
            # skip networks without actual appliances
            if not smn.devices.filter(ptype="appliance").exists():
                continue
            # add to tentative list
            ret.append(smn)
        # return the list
        return ret

    @staticmethod
    def get_all_networks(site: Site) -> list[SopMerakiNet]:
        ret: list[SopMerakiNet] = list()
        smns: list[SopMerakiNet] = site.meraki_nets  # type: ignore
        # loop on the site networks
        for smn in smns.all():
            # add to tentative list
            ret.append(smn)
        # return the list
        return ret

    @staticmethod
    def get_bound_networks(site: Site) -> list[SopMerakiNet]:
        ret: list[SopMerakiNet] = list()
        smns: list[SopMerakiNet] = site.meraki_nets  # type: ignore
        # loop on the site networks
        for smn in smns.all():
            # skip not bound networks
            if not smn.bound_to_template:
                continue
            # add to tentative list
            ret.append(smn)
        # return the list
        return ret

    @staticmethod
    def update_uplink_statuses(
        smn: SopMerakiNet,
        conn: meraki.DashboardAPI,
        dash: SopMerakiDash,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        uplink_status_data:dict
        try:
            uplink_status_data=conn.appliance.getOrganizationApplianceUplinkStatuses(smn.org.meraki_id, total_pages=-1, networkIds=[smn.meraki_id])
        except meraki.exceptions.APIError as ex:
            raise ex
        if len(uplink_status_data)!=1:
            raise Exception(f"Wrong number of networks returned {len(uplink_status_data)}")
        SopMerakiNetUtils.update_uplink_statuses_from_data(smn, conn, uplink_status_data[0], log, details)

    @staticmethod
    def update_uplink_statuses_from_data(
        smn: SopMerakiNet,
        conn: meraki.DashboardAPI,
        uplink_statuses:dict[str,dict],
        log: JobRunnerLogMixin,
        details: bool,
    ):
        # fetch on all devices' uplinks
        prim_dev:SopMerakiDevice=None
        prim_stats:dict=uplink_statuses.get('primary')
        if prim_stats is None:
            return
        prim_dev=SopMerakiDeviceUtils.get_by_serial(prim_stats['serial'])
        spar_dev:SopMerakiDevice=None
        spar_stats:dict=uplink_statuses.get('spare')
        if spar_stats is not None:
            spar_dev=SopMerakiDeviceUtils.get_by_serial(spar_stats['serial'])
        # check if a network refresh is needed
        if prim_dev is None or (spar_stats is not None and spar_dev is None):
            log.log_debug(f"Refreshing network devices for network {smn}")
            SopMerakiNetUtils.refresh_networks_devices(smn, conn, smn.org, log, details)
            prim_dev=SopMerakiDeviceUtils.get_by_serial(prim_stats['serial'])
            if spar_stats is not None:
                spar_dev=SopMerakiDeviceUtils.get_by_serial(spar_stats['serial'])
        # now we can process first the network
        save:bool=False
        if smn.primary_mx != prim_dev:
            save=True
            for x in SopMerakiNet.objects.filter(primary_mx=prim_dev):
                x.primary_mx=None
                x.save()
            smn.primary_mx=prim_dev
        if smn.secondary_mx != spar_dev:
            save=True
            for x in SopMerakiNet.objects.filter(secondary_mx=spar_dev):
                x.secondary_mx=None
                x.save()
            smn.secondary_mx=spar_dev
        if save:
            smn.save()
        # then the devices
        SopMerakiDeviceUtils.update_uplink_statuses(prim_dev, prim_stats)
        if spar_stats is not None:
            SopMerakiDeviceUtils.update_uplink_statuses(spar_dev, spar_stats)
   
    @staticmethod
    def clear_uplink_statuses(
        smn: SopMerakiNet,
    ):
        if smn.primary_mx is not None:
            SopMerakiDeviceUtils.clear_uplink_statuses(smn.primary_mx)
            smn.primary_mx=None
        if smn.secondary_mx is not None:
            SopMerakiDeviceUtils.clear_uplink_statuses(smn.secondary_mx)
            smn.secondary_mx=None
        smn.save()

    
    @staticmethod
    def update_vpn_statuses(
        smn: SopMerakiNet,
        conn: meraki.DashboardAPI,
        dash: SopMerakiDash,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        vpn_status_data:dict
        try:
            vpn_status_data=conn.appliance.getOrganizationApplianceVpnStatuses(smn.org.meraki_id, total_pages=-1, networkIds=[smn.meraki_id])
        except meraki.exceptions.APIError as ex:
            raise ex  
        if len(vpn_status_data)!=1:
            raise Exception(f"Wrong number of networks returned {len(vpn_status_data)}")
        SopMerakiNetUtils.update_vpn_statuses_from_data(smn, vpn_status_data[0], log)


    @staticmethod
    def update_vpn_statuses_from_data(
        smn: SopMerakiNet,
        net_stat:dict,
        log: JobRunnerLogMixin,
    ):
        save:bool= False
        # -- device vpnmode
        vpn_mode:str = net_stat.get("vpnMode", "")
        if vpn_mode != smn.vpn_mode:
            smn.vpn_mode=vpn_mode
            #print(f"vpn_statuses_from_meraki_data {net.nom} : SETTING {net.vpn_mode=}")
            save=True
        # -- number of exported subnets
        exp_subnets:int = len(net_stat.get("exportedSubnets", []))
        if exp_subnets != smn.exp_subnets_count:
            smn.exp_subnets_count=exp_subnets
            #log.log_debug(f"vpn_statuses_from_meraki_data {net.nom} : SETTING {net.exp_subnets_count=}")
            save=True
        # -- device status
        app_status:str = net_stat.get("deviceStatus", "")
        #print(f"vpn_statuses_from_meraki_data {net.nom=} : {app_status=} VS {net.appliance_status=}")
        if app_status != smn.appliance_status:
            smn.appliance_status=app_status
            print(f"vpn_statuses_from_meraki_data {smn.nom} : SETTING {smn.appliance_status=}")
            save=True
        # -- meraki peers reachability
        net_all_peers_reach="all reachable"
        for net_peer in net_stat.get("merakiVpnPeers"):
            if "reachable"!=net_peer.get("reachability",""):
                net_all_peers_reach="unreachable"
                break
        #print(f"vpn_statuses_from_meraki_data {net.nom=} : {net_all_peers_reach=} VS {net.meraki_peers_reachability=}")
        if net_all_peers_reach!=smn.meraki_peers_reachability:
            smn.meraki_peers_reachability=net_all_peers_reach
            #log.log_debug(f"vpn_statuses_from_meraki_data {net.nom}  : SETTING {net.meraki_peers_reachability=}")
            save=True
        # check to save
        if save:
            log.log_debug(f"vpn_statuses_from_meraki_data {smn.nom=} MODIFIED -> SAVE")
            smn.last_stats_change=django_now()
            smn.save()

        


class SopMerakiDeviceUtils:

    __dtmodel_roleslug_mapping : dict[str,str] = { 
        "MR":"access-point", 
        "MS":"access-switch",
        "MX":"sdwan-router",
        "MS":"process-camera",
    }
    __unknown_role_mapping : str = "ukn-unknown"

    # ------------------ UTILS
    @staticmethod
    def get_by_serial(serial: str):
        devs = SopMerakiDevice.objects.filter(serial=serial)
        return devs[0] if devs.exists() else None

    @staticmethod
    def get_by_serial_or_create(serial:str, name:str):
        ret=SopMerakiDeviceUtils.get_by_serial(serial)
        return SopMerakiDevice(serial=serial, nom=f"NEW : {name}") if ret is None else ret

    @staticmethod
    def refresh_from_inventory_data(
        smd:SopMerakiDevice,
        conn: meraki.DashboardAPI,
        dev_data:dict,
        org: SopMerakiOrg,
        log: JobRunnerLogMixin,
        details: bool,
    )->bool:
        # cf https://developer.cisco.com/meraki/api-v1/get-organization-inventory-devices/
        if log and details:
            log.info(f"Refreshing from inventory '{smd.nom}'...")
        save = smd.pk is None
        if smd.pk and hasattr(smd, "snapshot"):
            smd.snapshot()
        #print(f" START refresh_from_inventory_data :{save=}")
        if smd.org is None or smd.org != org:  
            print(f" SQUASH ORG :{smd.org=} {org=}")
            smd.org = org
            save = True
        if smd.mac != dev_data.get("mac", None):
            smd.mac = dev_data.get("mac", None)
            save = True
        if smd.serial != dev_data.get("serial", None):
            smd.serial = dev_data.get("serial", None)
            save = True
        nameval = dev_data.get("name", None)
        if nameval is None or nameval.strip() == "":
            nameval = smd.mac
        if smd.nom != nameval:
            smd.nom = nameval
            save = True
        if smd.model_name != dev_data.get("model"):
            smd.model_name = dev_data.get("model")
            save = True
        # skipping orderNumber
        #print(f" l1068 refresh_from_inventory_data :{save=}")
        from sop_utils.dates import DateUtils
        dt=DateUtils.parse_date(dev_data.get("claimedAt"))
        if smd.claimed_at != dt:
            smd.claimed_at = dt
            save = True
        dt=DateUtils.parse_date(dev_data.get("licenseExpirationDate"))
        if smd.license_expiration_at != dt:
            smd.license_expiration_at = dt
            save = True
        if not ArrayUtils.equal_sets(smd.meraki_tags, dev_data.get("tags", list())):  # type: ignore
            smd.meraki_tags = dev_data.get("tags", list())
            save = True
        if smd.ptype != dev_data.get("productType"):
            smd.ptype = dev_data.get("productType")
            save = True
        if smd.country_code != dev_data.get("countryCode"):
            smd.country_code = dev_data.get("countryCode")
            save = True            
        #print(f" l1087 refresh_from_inventory_data :{save=}")
        # sub dict EOX
        eox=dev_data.get("eox", dict())
        if smd.eox_status != eox.get("status"):
            smd.eox_status = eox.get("status")
            save = True
        dt=DateUtils.parse_date(dev_data.get("endOfSaleAt"))
        if smd.eox_end_of_sale != dt:
            smd.eox_end_of_sale = dt
            save = True
        dt=DateUtils.parse_date(dev_data.get("endOfSupportAt"))
        if smd.eox_end_of_support != dt:
            smd.eox_end_of_support = dt
            save = True
        # only save if something changed
        if save:
            log.success(f"SopMerakiDeviceUtils.refresh_from_inventory_data saving SopDevice '[{smd.nom}]'.")
            smd._changelog_message="SopMerakiDeviceUtils.refresh_from_inventory_data"
            smd.full_clean()
            smd.save()

        return save

    @staticmethod
    def refresh_from_meraki_data(
        smd:SopMerakiDevice,
        conn: meraki.DashboardAPI,
        dev_data:dict,
        org: SopMerakiOrg,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        # cf https://developer.cisco.com/meraki/api-v1/get-organization-devices/
        if log and details:
            log.info(f"Refreshing '{smd.nom}'...")
        save = smd.pk is None
        if smd.pk and hasattr(smd, "snapshot"):
            smd.snapshot()
        if smd.meraki_netid != dev_data.get("networkId", None):
            smd.meraki_netid = dev_data.get("networkId", None)
            save = True
        if smd.meraki_notes != dev_data.get("notes", None):
            smd.meraki_notes = dev_data.get("notes", None)
            save = True
        if smd.firmware != dev_data.get("firmware", None):
            smd.firmware = dev_data.get("firmware", None)
            save = True
        if smd.lan_ip != dev_data.get("lanIp", None):
            smd.lan_ip = dev_data.get("lanIp", None)
            save = True
        from sop_utils.dates import DateUtils
        dt=DateUtils.parse_date(dev_data.get("configurationUpdatedAt"))
        if smd.cfg_updated_at != dt:
            smd.cfg_updated_at = dt
            save = True
        if smd.meraki_url != dev_data.get("url", None):
            smd.meraki_url = dev_data.get("url", None)
            save = True
        from decimal import Decimal
        r=dev_data.get("lat")
        d=round(Decimal(r),6) if r is not None else None
        if smd.latitude != d:
            smd.latitude = d
            save = True
        r=dev_data.get("lng")
        d=round(Decimal(r),6) if r is not None else None
        if smd.longitude != d:
            smd.longitude = d
            save = True
        if not SopUtils.deep_equals_json_ic(
            smd.meraki_details, dev_data.get("details", dict())
        ):
            smd.meraki_details = dev_data.get("details", dict())
            save = True

        # only save if something changed
        if save:
            log.success(f"SopMerakiDeviceUtils.refresh_from_meraki_data saving SopDevice '[{smd.nom}]'.")
            smd._changelog_message="SopMerakiDeviceUtils.refresh_from_meraki_data"
            smd.full_clean()
            smd.save()

        return save

    @staticmethod
    def relink_related_objects(
        smd:SopMerakiDevice,
        log: JobRunnerLogMixin,
    ):
        # -----------------------------------------------
        # Rattachement/maintenance d'objets dépendants
        save=False
        if smd.pk and hasattr(smd, "snapshot"):
            smd.snapshot()
        # Model <-> device type
        if smd.model_name is not None:
            slug=f"cisco-{smd.model_name}".lower()
            dts = DeviceType.objects.filter(manufacturer__slug__exact="cisco").filter(slug__iexact=slug)
            dt = None
            if dts.exists():
                dt = dts[0]
            else:
                log.warning(f"Unable to match {smd.nom} device type {smd.model_name} (lookup slug={slug})")
            if smd.netbox_dev_type != dt:
                smd.netbox_dev_type = dt
                save = True
        else:
            if smd.netbox_dev_type is not None:
                smd.netbox_dev_type = None
                save = True

        # Serial <-> device
        if smd.serial is not None:
            ds = Device.objects.filter(device_type__manufacturer__slug__exact="cisco").filter(serial__exact=smd.serial).order_by('created')
            d = None
            if ds.exists():
                for d in ds[1:]:
                    log.warning(f"Deleting duplicate of '[{ds[0].name}]' Netbox Device : '[{d.name}]({d.serial})' ")
                    d.delete()
                d = ds[0]
            # First remove existing link if it will block the onetoonerelationship
            if d is not None and hasattr(d, "meraki_device") and d.meraki_device != smd:
                print(f" REMOVING 1to1 between {d.meraki_device=} AND {d=}")
                md=d.meraki_device
                d.meraki_device=None
                d.save()
                md.netbox_device=None
                md.save()
            if smd.netbox_device != d:
                print(f" ADDING 1to1 between {smd=} AND {d=}")
                smd.netbox_device = d
                save = True
            if smd.netbox_device is not None:
                SopMerakiUtils.check_create_sopdevicesetting(smd.netbox_device)
        else:
            if smd.netbox_device is not None:
                smd.netbox_device = None
                save = True

        # Net ID <-> Sopmeraki net
        # if smd.meraki_netid is not None:
        #     mnets = SopMerakiNet.objects.filter(meraki_id=smd.meraki_netid)
        #     mnet = None
        #     if mnets.exists():
        #         mnet = mnets[0]
        #     if smd.meraki_network != mnet:
        #         smd.meraki_network = mnet
        #         save = True
        # else:
        #     if smd.meraki_network is not None:
        #         smd.meraki_network = None
        #         save = True

        # Device net <-> netbox site
        if smd.netbox_device is not None:
            st = smd.netbox_device.site
            if smd.site != st:
                smd.site = st
                save = True
        else:
            if smd.site is not None:
                smd.site = None
                save = True

        # Prepare Meraki device update
        update_meraki: dict = {}

        # push if needed
        if len(update_meraki.keys()):
            try:
                pass
            except Exception:
                log.failure(
                    f"Exception when updating Meraki Device '{smd.nom}' ({smd.serial}) with dict {update_meraki}"
                )
                raise
            log.success(
                f"Updating Meraki Device '[{smd.nom}]({smd.serial})' : {update_meraki}"
            )

        # only save if something changed
        if save:
            log.success(f"SopMerakiDeviceUtils.relink_related_objects saving SopDevice '[{smd.nom}]'.")
            smd._changelog_message="SopMerakiDeviceUtils.relink_related_objects"
            smd.full_clean()
            smd.save()

        return save

    @staticmethod
    def update_uplink_statuses(
        smd: SopMerakiDevice,
        uplink_statuses:dict,
    ):
        save:bool=False
        if smd.pk and hasattr(smd, "snapshot"):
            smd.snapshot()
        # first organize by link
        uplink_stat:dict
        by_wan:dict[str,dict]={}
        for uplink_stat in uplink_statuses["uplinks"]:
            interface:str=uplink_stat.get("interface")
            by_wan[interface]=uplink_stat
        # now work
        val:str
        save:bool=False
        val=by_wan.get('wan1', {}).get('status')
        if smd.wan1status != val:
            smd.wan1status = val
            save = True
        val=by_wan.get('wan1', {}).get('ip')
        if smd.wan1ip != val:
            smd.wan1ip = val
            save = True
        val=by_wan.get('wan2', {}).get('status')
        if smd.wan2status != val:
            smd.wan2status = val
            save = True
        val=by_wan.get('wan2', {}).get('ip')
        if smd.wan2ip != val:
            smd.wan2ip = val
            save = True 
        if save:
            smd.save()
   
    @staticmethod
    def clear_uplink_statuses(
        smd: SopMerakiDevice,
    ):
        if smd.pk and hasattr(smd, "snapshot"):
            smd.snapshot()
        smd.wan1ip=None
        smd.wan2ip=None
        smd.wan1status=None
        smd.wan2status=None
        smd._changelog_message="SopmerakiDeviceUtils.clear_uplink_statuses"
        smd.full_clean()
        smd.save()        
   
    @staticmethod
    def claim_devices_to_inventory(
        smo: SopMerakiOrg,
        serials : list[str],
        conn: meraki.DashboardAPI,
        log: JobRunnerLogMixin,
        details:bool
    ) -> list[SopMerakiDevice]:
        log.log_info(f"Trying to claim {serials} to {smo}")
        ret:list[SopMerakiDevice]=list()
        # DO not claim already inventoried devices
        to_claim:list[str]=serials.copy()
        for dev in conn.organizations.getOrganizationInventoryDevices(smo.meraki_id, total_pages=-1, serials=serials):
            serial=dev.get("serial")
            log.log_warning(f"SopMerakiDeviceUtils.claim_devices_to_inventory : device {serial} already exists in the inventory")
            to_claim.remove(serial)
        log.log_info(f"Claiming {to_claim} to {smo}...")
        conn.organizations.claimIntoOrganizationInventory(smo.meraki_id, serials=to_claim)
        log.log_info(f"Claim done, let's refresh claimed SopMerakiDevices from inventory")
        for dev in conn.organizations.getOrganizationInventoryDevices(smo.meraki_id, total_pages=-1, serials=serials):
            serial=dev.get("serial")
            # refresh "no net" devices from inventory
            log.log_info(f"Refreshing device {serial} ...")
            smd = SopMerakiDeviceUtils.get_by_serial_or_create(serial, dev['name'])
            saved = SopMerakiDeviceUtils.refresh_from_inventory_data(smd, conn, dev, smo, log, details)
            # if something changed we might need to refresh related objects
            if saved :
                log.log_info(f"Something changed on device {serial}, let's relink related objects...")
                SopMerakiDeviceUtils.relink_related_objects(smd, log)
            # Now create missing netbox devices
            smd=SopMerakiDeviceUtils.get_by_serial(serial)
            if smd.netbox_device is not None:
                log.log_info(f"SopmerakiDevice {serial} is already linked to an existing Netbox Device {smd.netbox_device}, nothing left to do...")
            elif smd.netbox_dev_type is not None:
                log.log_info(f"SopMerakiDeviceUtils.claim_devices_to_inventory : create netbox device for serial {serial} / devicetype {smd.netbox_dev_type}")
                if smd.pk and hasattr(smd, "snapshot"):
                    smd.snapshot()
                nd = Device(
                    device_type=smd.netbox_dev_type,
                    name=smd.nom,
                    status="inventory",
                    serial=smd.serial,
                    role=SopMerakiDeviceUtils.__get_model_to_role_mapping(smd.model_name),
                    site=Site.objects.get(slug="inventory"),
                    # TODO : platform
                      )
                nd._changelog_message = "SopMerakiDeviceUtils.claim_devices_to_inventory"
                nd.full_clean()
                nd.save()
                smd.netbox_device=nd
                smd._changelog_message = "SopMerakiDeviceUtils.claim_devices_to_inventory"
                smd.full_clean()
                smd.save()
            else:
                log.log_warning(f"SopmerakiDevice {serial} is not yet linked to a Netbox Device but also has no netbox_device_type !")
            ret.append(smd)
        log.log_info(f"Refresh done !")
        return ret

    @staticmethod
    def __get_model_to_role_mapping(model:str)->DeviceRole:
        for k,v in SopMerakiDeviceUtils.__dtmodel_roleslug_mapping.items():
            if not model.startswith(k):
                continue
            rls=DeviceRole.objects.filter(slug=v)
            if not rls.exists():
                raise AbortRequest(f"Cannot find DeviceRole with slug {v} !")
            return rls[0]
        v=SopMerakiDeviceUtils.__unknown_role_mapping
        rls=DeviceRole.objects.filter(slug=v)
        if not rls.exists():
            raise AbortRequest(f"Cannot find DeviceRole with slug {v} !")
        return rls[0]

    @staticmethod
    def move_devices_to_network(
        smn: SopMerakiNet,
        devices : list[SopMerakiDevice],
        force_move:bool,
        conn: meraki.DashboardAPI,
        log: JobRunnerLogMixin,
        details:bool
    ) -> dict:
        # Préparer les reports
        found=list()
        skipped=list()
        failed=list()
        bound=list()
        moved=list()
        # extract serials
        by_serial:dict[str,SopMerakiDevice]=dict( (d.serial, d) for d in devices)
        serials:list[str]=list(set(d.serial for d in devices))
        # Loop to classify
        for dev in conn.organizations.getOrganizationInventoryDevices(smn.org.meraki_id, total_pages=-1, serials=serials):
            serial=dev.get("serial")
            nid=dev.get("networkId")
            if nid is None or nid=="":
                found.append(serial)
                serials.remove(serial)
            elif nid==smn.meraki_id:
                skipped.append(serial)
                serials.remove(serial)
            else:
                if not force_move:
                    bound.append(serial)
                else:
                    moved.append([serial,nid])
                serials.remove(serial)
        not_found=list()
        not_found.extend(serials)
        serials=found.copy()
        print(f"{serials=}")
        # Free devices from networks
        for (sn,nid) in moved:
            conn.networks.removeNetworkDevices(nid, sn)
            serials.append(sn)
            smd=by_serial.get(sn)
            smd.snapshot()
            smd.meraki_netid=None
            # smd.meraki_network=None
            smd.full_clean()
            smd.save()
        print(f"{serials=}")
        log.log_info(f"Trying to claim/move {serials} to network {smn.nom} ({smn.meraki_id}) ...")
        result=conn.networks.claimNetworkDevices(smn.meraki_id, serials=serials, addAtomically=False)
        errs=result.get("errors")
        if errs and len(errs)>0:
            log.log_failure(f"Claim to {smn} had errors : {errs}")
        for sn in result.get("serials"):
            smd=by_serial.get(sn)
            smd.snapshot()
            smd.meraki_netid=smn.meraki_id
            # smd.meraki_network=smn
            smd.full_clean()
            smd.save()
        log.log_info(f"Move {serials} to {smn} done !")
        return {
            "to_claim": found,
            "to_move": moved,
            "bound" : bound,
            "to_skip": skipped,
            "not_found" : not_found,
            "errors": errs,
        }
        

class SopMerakiSwitchStackUtils:
    @staticmethod
    def create_or_refresh(
        conn: meraki.DashboardAPI,
        stack,
        smnet: SopMerakiNet,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        if not SopMerakiSwitchStack.objects.filter(meraki_id=stack["id"]).exists():
            if log:
                log.info(
                    f"Creating new STACK for '{stack['id']}' on NET '{smnet.nom}'..."
                )
            sms = SopMerakiSwitchStack()
        else:
            sms = SopMerakiSwitchStack.objects.get(meraki_id=stack["id"])
        SopMerakiSwitchStackUtils.refresh_from_meraki(sms, conn, stack, smnet, log, details)

    def refresh_from_meraki(
        smss:SopMerakiSwitchStack,
        conn: meraki.DashboardAPI,
        stack,
        smnet: SopMerakiNet,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        # cf https://developer.cisco.com/meraki/api-v1/get-network-switch-stacks/
        if log and details:
            log.info(f"Refreshing '{smss.nom}'...")
        save = smss.pk is None
        serial_change = smss.pk is None
        if smss.nom != stack["name"]:
            smss.nom = stack["name"]
            save = True
        if smss.meraki_id != stack["id"]:
            smss.meraki_id = stack["id"]
            save = True
        if smss.net_id is None or smss.net != smnet:  # type: ignore
            smss.net = smnet
            save = True
        if not ArrayUtils.equal_sets(smss.serials, stack["serials"]):  # type: ignore
            smss.serials = stack["serials"]
            serial_change = True
            save = True
        if not SopUtils.deep_equals_json_ic(smss.members, stack["members"]):  # type: ignore
            smss.members = stack["members"]
            serial_change = True
            save = True

        # -----------------------------------------------
        # Rattachement/maintenance d'objets dépendants

        # Sopmeraki net <-> netbox site
        if smss.net is not None:
            st = smss.net.site
            if smss.site != st:
                smss.site = st
                save = True
        else:
            if smss.site is not None:
                smss.site = None
                save = True

        # only save if something changed
        if save:
            log.success(f"Saving SopMerakiSwitchStack '[{smss.nom}]'.")
            smss._changelog_message="SopMerakiSwitchStackUtils.refresh_from_meraki"
            smss.full_clean()
            smss.save()

        # Always rewire the stack elements
        mems: list[SopMerakiDevice] = list()
        mems.extend(smss.meraki_devices.all())
        for ser in smss.serials:
            dev = SopMerakiDeviceUtils.get_by_serial(ser)
            if dev is None:
                raise Exception("Error : the device should exist at that point")
            if not dev in mems:
                if dev.stack!=smss:
                    dev.snapshot()
                    dev.stack = smss
                    dev.full_clean()
                    dev.save()
            if dev in mems:
                mems.remove(dev)
        # devices still in mems have been removed from the stack -> cleanup
        for mem in mems:
            smss.meraki_devices.remove(mem)

        return save


class SopMerakiOrgUtils:

    # ------------------ UTILS

    @staticmethod
    def get_by_id(id: int)->SopMerakiOrg:
        orgs = SopMerakiOrg.objects.filter(pk=id)
        return orgs[0] if orgs.exists() else None

    @staticmethod
    def get_by_meraki_id(meraki_id: str)->SopMerakiOrg:
        orgs = SopMerakiOrg.objects.filter(meraki_id=meraki_id)
        return orgs[0] if orgs.exists() else None


    @staticmethod
    def refresh_from_meraki(
        smo,
        conn: meraki.DashboardAPI,
        dash: SopMerakiDash,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        org_data=conn.organizations.getOrganization(smo.meraki_id)
        return SopMerakiOrgUtils.refresh_from_meraki_data(smo, conn, org_data, dash, log, details)

    @staticmethod
    def refresh_from_meraki_data(
        smo:SopMerakiOrg,
        conn: meraki.DashboardAPI,
        org_data:dict,
        dash: SopMerakiDash,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        save = smo.pk is None
        # cf https://developer.cisco.com/meraki/api-v1/get-organizations/
        if smo.nom != org_data["name"]:
            smo.nom = org_data["name"]
            save = True
        if smo.meraki_id != org_data["id"]:
            smo.meraki_id = org_data["id"]
            save = True
        if smo.dash_id is None or smo.dash != dash:  # type: ignore
            smo.dash = dash
            save = True
        if smo.meraki_url != org_data["url"]:
            smo.meraki_url = org_data["url"]
            save = True
        if not SopUtils.deep_equals_json_ic(smo.meraki_api, org_data["api"]):  # type: ignore
            smo.meraki_api = org_data["api"]
            save = True
        if not SopUtils.deep_equals_json_ic(smo.meraki_cloud, org_data["cloud"]):  # type: ignore
            smo.meraki_cloud = org_data["cloud"]
            save = True
        if not SopUtils.deep_equals_json_ic(smo.meraki_licensing, org_data["licensing"]):  # type: ignore
            smo.meraki_licensing = org_data["licensing"]
            save = True

        if save:
            smo._changelog_message="SopMerakiOrgUtils.refresh_from_meraki_data"
            smo.full_clean()
            smo.save()

        # refresh nets AND their devices
        #print("====NETLOOP====")
        net_ids = []
        smn: SopMerakiNet
        if log:
            log.info(f"Looping on '{smo.nom}' networks...")
        for net in conn.organizations.getOrganizationNetworks(
            smo.meraki_id, total_pages=-1
        ):
            net_ids.append(net["id"])
            SopMerakiNetUtils.create_or_refresh(conn, net, smo, log, details)
        if log:
            log.info(f"Done looping on '{smo.nom}' networks, starting cleanup...")
        for smn in smo.nets.all():  # type: ignore
            if smn.meraki_id not in net_ids:
                log.info(f"Deleting '{smn.nom}'...")
                smn.delete()

        # refresh devices that are *NOT* in networks (inventory only --> explicit null in networkIds)
        #print("====INVLOOP====")
        devs_saved:dict[str,bool] = dict()
        smd: SopMerakiDevice
        inv_devs=conn.organizations.getOrganizationInventoryDevices(
            smo.meraki_id, total_pages=-1, networkIds=["null"]
        )
        if log:
            log.info(f"Looping on '{smo.nom}' organization's {len(inv_devs)} unattached devices...")
        for dev in inv_devs :
            serial=dev['serial']
            devs_saved[serial]=False
            # do not refresh devices with networks, will be done when refreshing networks recursibvely
            if dev.get("networkId", None) is not None:
                print(f"ERROR {dev} has networkid {dev.get("networkId")} for org {smo.meraki_id}")
                continue
            # refresh "no net" devices
            smd = SopMerakiDeviceUtils.get_by_serial_or_create(serial, dev['name'])
            devs_saved[serial] = SopMerakiDeviceUtils.refresh_from_inventory_data(smd, conn, dev, smo, log, details)
        # Orphan devices that are not in this org anymore
        #print(f"cleanup filter=> {smo.meraki_id=} {net_ids=} {devs_saved.keys()}")
        orph_devs=SopMerakiDevice.objects.filter(org__meraki_id=smo.meraki_id).exclude(serial__in=devs_saved.keys()).exclude(meraki_netid__in=net_ids)
        if log:
            log.info(f"Done looping, starting orphaning of {orph_devs.count()} devices...")
        for smd in orph_devs: 
            log.info(f"Orphaning '{smd.nom}'/'{smd.serial}'...")
            smd.orphan_device()
            devs_saved[smd.serial]=True
        # REFETCH RELATED OBJECTS
        for serial in devs_saved.keys():
            if devs_saved[serial]:
                smdev = SopMerakiDeviceUtils.get_by_serial(serial)
                SopMerakiDeviceUtils.relink_related_objects(smdev, log)         


        return save
    
    @staticmethod
    def update_vpn_statuses(
        smo: SopMerakiOrg,
        conn: meraki.DashboardAPI,
        dash: SopMerakiDash,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        vpn_status_data:dict
        try:
            vpn_status_data=conn.appliance.getOrganizationApplianceVpnStatuses(smo.meraki_id, total_pages=-1)
        except meraki.exceptions.APIError as ex:
            if ex.status==400:
                if log :
                    log.log_info(f"No site-to-site VPN for Organization {smo.nom}")
            else:
                raise ex  
        else:
            SopMerakiOrgUtils.update_vpn_statuses_from_data(smo, conn, vpn_status_data, dash, log, details)


    @staticmethod
    def update_vpn_statuses_from_data(
        smo: SopMerakiOrg,
        conn: meraki.DashboardAPI,
        vpn_status_data:dict,
        dash: SopMerakiDash,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        done:list[str]=[]
        net_stat:dict
        for net_stat in vpn_status_data:
            net_id:str=net_stat.get("networkId")
            nets=SopMerakiNet.objects.filter(meraki_id=net_id)
            if nets.count()==0:
                # May be this net hasn't been synced yet to the DB, skip it
                continue
            SopMerakiNetUtils.update_vpn_statuses_from_data(nets[0], net_stat, log)
            # -- mark as handled
            done.append(net_id)
        # secondary pass to clear unhandled networks
        save:bool
        for net in smo.nets.all():
            if net.meraki_id in done:
                #print(f"vpn_statuses_from_meraki_data {net.nom=} ALREADY HANDLED")
                continue
            save=False
            if net.vpn_mode is not None:
                net.vpn_mode=None
                save=True
            if net.exp_subnets_count is not None:
                net.exp_subnets_count=None
                save=True
            if net.appliance_status is not None:
                net.appliance_status=None
                save=True
            if net.meraki_peers_reachability is not None:
                net.meraki_peers_reachability=None
                save=True
            if save:
                log.log_debug(f"vpn_statuses_from_meraki_data {net.nom=} CLEARED -> SAVE")
                net.last_stats_change=django_now()
                net.save()
            else:
                #print(f"vpn_statuses_from_meraki_data {net.nom=} UNCHANGED")    
                pass
    
    @staticmethod
    def update_uplink_statuses(
        smo: SopMerakiOrg,
        conn: meraki.DashboardAPI,
        dash: SopMerakiDash,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        uplink_status_data:dict
        try:
            uplink_status_data=conn.appliance.getOrganizationApplianceUplinkStatuses(smo.meraki_id, total_pages=-1)
        except meraki.exceptions.APIError as ex:
            if ex.status==400:
                if log :
                    log.log_info(f"No site-to-site VPN for Organization {smo.nom}")
            else:
                raise ex  
        else:
            SopMerakiOrgUtils.update_uplink_statuses_from_data(smo, conn, uplink_status_data, dash, log, details)


    @staticmethod
    def update_uplink_statuses_from_data(
        smo: SopMerakiOrg,
        conn: meraki.DashboardAPI,
        uplink_status_data:dict,
        dash: SopMerakiDash,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        # first organize by networks
        uplink_stat:dict
        by_net:dict[str,dict[str,dict]]={}
        for uplink_stat in uplink_status_data:
            net_id:str=uplink_stat.get("networkId")
            d:dict[str,dict]=by_net.get(net_id,{})
            d[uplink_stat['highAvailability']['role']]=(uplink_stat)
            by_net[net_id]=d
        #print(by_net)
        # then handle network by network
        net:SopMerakiNet
        done:list[str]=[]
        save:bool
        uplink_statuses:dict[str,dict]
        for (net_id,uplink_statuses) in by_net.items():
            smn=SopMerakiNetUtils.get_by_meraki_id(net_id)
            if smn is None:
                continue
            SopMerakiNetUtils.update_uplink_statuses_from_data(smn,conn,uplink_statuses,log,details)
            # -- mark as handled
            done.append(net_id)
        # secondary pass to clear unhandled networks
        for net in smo.nets.all():
            if net.meraki_id in done:
                continue
            save=False
            if net.vpn_mode is not None:
                net.vpn_mode=None
                save=True
            if net.exp_subnets_count is not None:
                net.exp_subnets_count=None
                save=True
            if net.appliance_status is not None:
                net.appliance_status=None
                save=True
            if net.meraki_peers_reachability is not None:
                net.meraki_peers_reachability=None
                save=True
            if save:
                log.log_debug(f"uplinkstatuses_from_meraki_data {net.nom=} CLEARED -> SAVE")
                net.save()
            else:
                #print(f"uplinkstatuses_from_meraki_data {net.nom=} UNCHANGED")    
                pass


class SopMerakiDashUtils: 
    
    @staticmethod
    def refresh_from_meraki(
        smd:SopMerakiDash, conn: meraki.DashboardAPI, log: JobRunnerLogMixin, details: bool
    ):
        save = smd.pk is None

        if save:
            smd._changelog_message="SopMerakiDashUtils.refresh_from_meraki"
            smd.full_clean()
            smd.save()

        org_ids = []
        smo: SopMerakiOrg
        if log:
            log.info(f"Looping on '{smd.nom}' organizations...")
        for org in conn.organizations.getOrganizations():
            org_ids.append(org["id"])
            if not SopMerakiOrg.objects.filter(meraki_id=org["id"]).exists():
                if log:
                    log.info(
                        f"Creating ORG for '{org['name']}' on DASH '{smd.nom}'..."
                    )
                smo = SopMerakiOrg()
            else:
                smo = SopMerakiOrg.objects.get(meraki_id=org["id"])
            SopMerakiOrgUtils.refresh_from_meraki_data(smo, conn, org, smd, log, details)

        if log:
            log.info(f"Done looping on '{smd.nom}' organizations, starting cleanup...")
        for smo in smd.orgs.all():  # type: ignore
            if smo.meraki_id not in org_ids:
                log.info(f"Deleting ORG '{smo.nom}' / {smo.meraki_id}")
                smo.delete()
        if log:
            log.info(f"Done cleaning up '{smd.nom}' !")

        return save

    @staticmethod
    def update_vpn_statuses(
        smd:SopMerakiDash, conn: meraki.DashboardAPI, log: JobRunnerLogMixin, details: bool
    ):
        if log:
            log.info(f"Getting VPN statuses for '{smd.nom}' !")        
        smo:SopMerakiOrg
        for smo in smd.orgs.all():
            if log:
                log.info(f"Getting VPN statuses for '{smd.nom} / {smo.nom}'...")
            SopMerakiOrgUtils.update_vpn_statuses(smo, conn, smd, log, details)
        if log:
            log.info(f"Done getting VPN statuses for '{smd.nom}' !")        

    @staticmethod
    def update_uplink_statuses(
        smd:SopMerakiDash, conn: meraki.DashboardAPI, log: JobRunnerLogMixin, details: bool
    ):
        if log:
            log.info(f"Getting Uplink statuses for '{smd.nom}' !")        
        smo:SopMerakiOrg
        for smo in smd.orgs.all():
            if log:
                log.info(f"Getting Uplink statuses for '{smd.nom} / {smo.nom}'...")
            SopMerakiOrgUtils.update_uplink_statuses(smo, conn, smd, log, details)
        if log:
            log.info(f"Done getting Uplink statuses for '{smd.nom}' !")       

#endregion