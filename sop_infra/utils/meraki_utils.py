from zoneinfo import ZoneInfo

from dcim.models import Device, DeviceType, Region, Site, SiteGroup
from netbox.context import current_request
from sop_infra.models.infra import SopDeviceSetting
from sop_infra.models.sopmeraki import SopMerakiDash, SopMerakiDevice, SopMerakiNet, SopMerakiOrg, SopMerakiSwitchStack
from sop_infra.utils.mixins import JobRunnerLogMixin
from sop_utils.arrays import ArrayUtils
from sop_utils.misc import SopUtils
from sop_utils.regexps import SopRegExps
from tenancy.models import Tenant, TenantGroup


import meraki
from django.contrib import messages


class SopMerakiUtils:

    # DEV TYPES:
    # 'appliance', 'camera', 'campusGateway', 'cellularGateway', 'secureConnect', 'sensor', 'switch', 'systemsManager', 'wireless' or 'wirelessController'
    DEV_TYPE_MX = "appliance"
    DEV_TYPE_MV = "camera"
    DEV_TYPE_MS = "switch"
    DEV_TYPE_MR = "wireless"

    __parsed: bool = False
    __meraki_api_keys: dict[str, str] = {}

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
            api_key=api_key, base_url=api_url, suppress_logging=True, simulate=simulate
        )

    @classmethod
    def connect_by_name(cls, dash_name: str, simulate: bool = False) -> meraki.DashboardAPI:
        smds=SopMerakiDash.objects.filter(nom=dash_name)
        if not smds.exists():
            raise Exception(f"Unknown dashboard name {dash_name} ! ")
        return cls.connect(dash_name, smds[0].api_url, simulate)

    @classmethod
    def connect_for_site(cls, site: Site, simulate: bool = False,) -> meraki.DashboardAPI:
        org:SopMerakiOrg=cls.get_site_meraki_org(site)
        if org is None:
            raise Exception(f"Unknown dashboard for the site {site.name} ! ")
        return cls.connect(org.dash.nom, org.dash.api_url, simulate)
    
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
        cls, log: JobRunnerLogMixin, simulate: bool, nets: list, details: bool = False
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
    def create_meraki_networks(
        cls, log: JobRunnerLogMixin, simulate: bool, site: Site, details: bool = False
    ):
        if log and details:
            log.log_debug(f"create_meraki_networks for site {site}")
        # Check site sopinfra for existing nets
        if site.meraki_nets.exists():  # type: ignore
            if log and details:
                log.log_failure(f"SopMerakiNets already exist for site {site}...")
            return
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
        SopMerakiNet.create_or_refresh(conn, sdwan, org, log, details)
        switches = conn.organizations.createOrganizationNetwork(
            org.meraki_id,
            name=switch_name,
            productTypes=["switch", "wireless"],
            tags=SopMerakiUtils.calc_site_netbox_tags(site),
        )
        if log and details:
            log.log_debug(f"created Switch + Wifi network {switches=}")
        SopMerakiNet.create_or_refresh(conn, switches, org, log, details)
        bind = conn.networks.bindNetwork(switches["id"], "L_731271989494293752")
        if log and details:
            log.log_debug(f"bound network {bind=}")
        SopMerakiNet.create_or_refresh(conn, bind, org, log, details)
        if log:
            log.log_success(f"Done creating networks !")

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
    #     SopMerakiNet.create_or_refresh(conn, sdwan, org, log)
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
    #     SopMerakiNet.create_or_refresh(conn, switches, org, log)
    #     bind=conn.networks.bindNetwork(switches["id"], "L_731271989494293752")
    #     if log and details:
    #         log.log_debug(
    #             f"bound network {bind=}"
    #         )
    #     SopMerakiNet.create_or_refresh(conn, bind, org, log)
    #     if log:
    #         log.log_success(
    #             f"Done creating networks !"
    #         )

    @staticmethod
    def extractSiteName(name):
        m = SopRegExps.meraki_sitename_re.match(f"{name}")
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


class SopMerakiNetUtils:
    
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
        if f"{smn.timezone}" != f"{net_data['timeZone']}":
            smn.timezone = net_data["timeZone"]
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
                smn.full_clean()
                smn.save()
            if new_site:
                new_site.meraki_nets.add(smn)


        # Refresh devices from this net
        for dev in conn.organizations.getOrganizationDevices(
            org.meraki_id, networkIds=[smn.meraki_id], total_pages=-1
        ):
            smdev = SopMerakiDeviceUtils.get_by_serial_or_create(dev['serial'],dev['name'])
            SopMerakiDeviceUtils.refresh_from_meraki_data(smdev, conn, dev, org, log, details)

        # Refresh stacks from this net
        if "switch" in smn.ptypes :
            for st in conn.switch.getNetworkSwitchStacks(smn.meraki_id):
                SopMerakiSwitchStackUtils.create_or_refresh(conn, st, smn, log, details)

        return save


class SopMerakiDeviceUtils:
    # ------------------ UTILS
    @staticmethod
    def get_by_serial(serial: str):
        devs = SopMerakiDevice.objects.filter(serial=serial)
        return devs[0] if devs.exists() else None

    @staticmethod
    def get_by_serial_or_create(serial:str, name:str):
        ret=SopMerakiDeviceUtils.get_by_serial(serial)
        return SopMerakiDevice(serial=serial, nom=f"NEW : {name}") if ret is None else ret

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
        if smd.org_id is None or smd.org != org:  # type: ignore
            smd.org = org
            save = True
        nameval = dev_data.get("name", None)
        if nameval is None or nameval.strip() == "":
            nameval = dev_data.get("mac", None)
        if smd.nom != nameval:
            smd.nom = nameval
            save = True
        if smd.model_name != dev_data.get("model", None):
            smd.model_name = dev_data.get("model", None)
            save = True
        if smd.serial != dev_data.get("serial", None):
            smd.serial = dev_data.get("serial", None)
            save = True
        if smd.mac != dev_data.get("mac", None):
            smd.mac = dev_data.get("mac", None)
            save = True
        if smd.meraki_netid != dev_data.get("networkId", None):
            smd.meraki_netid = dev_data.get("networkId", None)
            save = True
        if smd.meraki_notes != dev_data.get("notes", None):
            smd.meraki_notes = dev_data.get("notes", None)
            save = True
        if smd.ptype != dev_data.get("productType", None):
            smd.ptype = dev_data.get("productType", None)
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

        if not ArrayUtils.equal_sets(smd.meraki_tags, dev_data.get("tags", list())):  # type: ignore
            smd.meraki_tags = dev_data.get("tags", list())
            save = True
        if not SopUtils.deep_equals_json_ic(
            smd.meraki_details, dev_data.get("details", dict())
        ):
            smd.meraki_details = dev_data.get("details", dict())
            save = True

        # -----------------------------------------------
        # Rattachement/maintenance d'objets dépendants

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
        if smd.meraki_netid is not None:
            mnets = SopMerakiNet.objects.filter(meraki_id=smd.meraki_netid)
            mnet = None
            if mnets.exists():
                mnet = mnets[0]
            if smd.meraki_network != mnet:
                smd.meraki_network = mnet
                save = True
        else:
            if smd.meraki_network is not None:
                smd.meraki_network = None
                save = True

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
            log.success(f"Saving SopDevice '[{smd.nom}]'.")
            smd.full_clean()
            smd.save()

        return save


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
        smo,
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
            smo.full_clean()
            smo.save()

        # refresh devices that are *NOT* in networks (inventory only)
        serials = []
        smd: SopMerakiDevice
        if log:
            log.info(f"Looping on '{smo.nom}' devices...")
        for dev in conn.organizations.getOrganizationInventoryDevices(
            org_data["id"], total_pages=-1
        ):
            # save serial for orphanaton
            serials.append(dev["serial"])
            # do not refresh devices with networks, will be done when refreshing networks recursibvely
            if dev.get("networkId", None) is not None:
                continue
            # refresh "no net" devices
            smd = SopMerakiDeviceUtils.get_by_serial_or_create(dev['serial'], dev['name'])
            SopMerakiDeviceUtils.refresh_from_meraki_data(smd, conn, dev, smo, log, details)
        # Remove devices that are not in this org anymore
        if log:
            log.info(f"Done looping on '{smo.nom}' devices, starting cleanup...")
        for smd in smo.devices.filter(org__meraki_id=org_data["id"]):  # type: ignore
            if smd.serial not in serials:
                log.info(f"Orphaning '{smd.nom}'/'{smd.serial}'...")
                smd.orphan_device()

        # refresh nets
        net_ids = []
        smn: SopMerakiNet
        if log:
            log.info(f"Looping on '{smo.nom}' networks...")
        for net in conn.organizations.getOrganizationNetworks(
            org_data["id"], total_pages=-1
        ):
            net_ids.append(net["id"])
            SopMerakiNetUtils.create_or_refresh(conn, net, smo, log, details)
        if log:
            log.info(f"Done looping on '{smo.nom}' networks, starting cleanup...")
        for smn in smo.nets.all():  # type: ignore
            if smn.meraki_id not in net_ids:
                log.info(f"Deleting '{smn.nom}'...")
                smn.delete()

        return save
    

class SopMerakiDashUtils: 
    
    @staticmethod
    def refresh_from_meraki(
        smd, conn: meraki.DashboardAPI, log: JobRunnerLogMixin, details: bool
    ):
        save = smd.pk is None

        if save:
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
            smo.refresh_from_meraki_data(conn, org, smd, log, details)

        if log:
            log.info(f"Done looping on '{smd.nom}' organizations, starting cleanup...")
        for smo in smd.orgs.all():  # type: ignore
            if smo.meraki_id not in org_ids:
                log.info(f"Deleting ORG '{smo.nom}' / {smo.meraki_id}")
                smo.delete()
        if log:
            log.info(f"Done cleaning up '{smd.nom}' !")

        return save