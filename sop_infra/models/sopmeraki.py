from zoneinfo import ZoneInfo
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from netbox.models import NetBoxModel
from dcim.models import Site, SiteGroup, Region, DeviceType, Device
from sop_infra.utils.mixins import JobRunnerLogMixin
from tenancy.models import Tenant, TenantGroup
from timezone_field import TimeZoneField

import meraki

from sop_infra.utils.sop_utils import ArrayUtils, SopRegExps, SopUtils


__all__ = (
    "SopMerakiUtils",
    "SopMerakiDash",
    "SopMerakiOrg",
    "SopMerakiNet",
    "SopMerakiDevice",
)


class SopMerakiUtils:

    # DEV TYPES:
    # 'appliance', 'camera', 'campusGateway', 'cellularGateway', 'secureConnect', 'sensor', 'switch', 'systemsManager', 'wireless' or 'wirelessController'
    DEV_TYPE_MX = "appliance"
    DEV_TYPE_MV = "camera"
    DEV_TYPE_MS = "switch"
    DEV_TYPE_MR = "wireless"

    __parsed: bool = False
    __meraki_api_keys: dict[str, str] = {}
    __no_auto_sched: bool = False

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
        cls.__no_auto_sched = infra_config.get("no_auto_sched", False)
        cls.__parsed = True

    @classmethod
    def get_ro_api_key_for_dash_name(cls, name: str) -> str:
        return cls.get_api_key_for_dash_name(name, "RO")

    @classmethod
    def get_rw_api_key_for_dash_name(cls, name: str) -> str:
        return cls.get_api_key_for_dash_name(name, "RW")

    @classmethod
    def get_no_auto_sched(cls) -> bool:
        if not cls.__parsed:
            cls.try_parse_configuration()
        return cls.__no_auto_sched

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
    def connect(cls, dash_name: str, api_url: str, simulate: bool = False):
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
    def refresh_dashboards(
        cls, log: JobRunnerLogMixin, simulate: bool, dashs: list, details: bool = False
    ):
        if dashs is None or len(dashs) == 0:
            dashs = SopMerakiDash.objects.all()  # type: ignore
        for smd in dashs:
            if log:
                log.info(f"Trying to connect to '{smd.nom}' via url '{smd.api_url}'...")
            conn = cls.connect(smd.nom, smd.api_url, simulate)
            if log:
                log.info(f"Trying to refresh '{smd.nom}'")
            smd.refresh_from_meraki(conn, log, details)

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
    def get_site_meraki_org(site: Site):
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


class SopMerakiDash(NetBoxModel):
    """
    Represents a Meraki dashboard
    """

    nom = models.CharField(
        max_length=50, null=False, blank=False, unique=True, verbose_name="Name"
    )

    description = models.CharField(
        max_length=250, null=True, blank=True, unique=False, verbose_name="Description"
    )

    api_url = models.URLField(null=False, blank=False, verbose_name="API base URL")

    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:sopmerakidash_detail", args=[self.pk])

    class Meta(NetBoxModel.Meta):
        verbose_name = "Meraki dashboard"
        verbose_name_plural = "Meraki dashboards"

    def refresh_from_meraki(
        self, conn: meraki.DashboardAPI, log: JobRunnerLogMixin, details: bool
    ):
        save = self.pk is None

        if save:
            self.full_clean()
            self.save()

        org_ids = []
        smo: SopMerakiOrg
        if log:
            log.info(f"Looping on '{self.nom}' organizations...")
        for org in conn.organizations.getOrganizations():
            org_ids.append(org["id"])
            if not SopMerakiOrg.objects.filter(meraki_id=org["id"]).exists():
                if log:
                    log.info(
                        f"Creating ORG for '{org['name']}' on DASH '{self.nom}'..."
                    )
                smo = SopMerakiOrg()
            else:
                smo = SopMerakiOrg.objects.get(meraki_id=org["id"])
            smo.refresh_from_meraki(conn, org, self, log, details)

        if log:
            log.info(f"Done looping on '{self.nom}' organizations, starting cleanup...")
        for smo in self.orgs.all():  # type: ignore
            if smo.meraki_id not in org_ids:
                log.info(f"Deleting ORG '{smo.nom}' / {smo.meraki_id}")
                smo.delete()
        if log:
            log.info(f"Done cleaning up '{self.nom}' !")

        return save


class SopMerakiOrg(NetBoxModel):
    """
    Represents a Meraki Organisation, child of a Meraki dashboard
    """

    nom = models.CharField(max_length=50, null=False, blank=False, verbose_name="Name")
    dash = models.ForeignKey(
        to=SopMerakiDash,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        verbose_name="Dashboard",
        related_name="orgs",
    )
    meraki_id = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        unique=True,
        verbose_name="Meraki OrgID",
    )
    meraki_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:sopmerakiorg_detail", args=[self.pk])

    class Meta(NetBoxModel.Meta):
        verbose_name = "Meraki Organisation"
        verbose_name_plural = "Meraki Organisations"
        constraints = [
            models.UniqueConstraint(
                fields=["nom", "dash"],
                name="%(app_label)s_%(class)s_unique_dash_org",
                violation_error_message=_(
                    "This dashboard already has an org with this name."
                ),
            ),
        ]

    def refresh_from_meraki(
        self,
        conn: meraki.DashboardAPI,
        org,
        dash: SopMerakiDash,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        save = self.pk is None
        # cf https://developer.cisco.com/meraki/api-v1/get-organizations/
        if self.nom != org["name"]:
            self.nom = org["name"]
            save = True
        if self.meraki_id != org["id"]:
            self.meraki_id = org["id"]
            save = True
        if self.dash_id is None or self.dash != dash:  # type: ignore
            self.dash = dash
            save = True
        if self.meraki_url != org["url"]:
            self.meraki_url = org["url"]
            save = True

        if save:
            self.full_clean()
            self.save()

        # refresh nets
        net_ids = []
        smn: SopMerakiNet
        if log:
            log.info(f"Looping on '{self.nom}' networks...")
        for net in conn.organizations.getOrganizationNetworks(
            org["id"], total_pages=-1
        ):
            net_ids.append(net["id"])
            SopMerakiNet.create_or_refresh(conn, net, self, log, details)
        if log:
            log.info(f"Done looping on '{self.nom}' networks, starting cleanup...")
        for smn in self.nets.all():  # type: ignore
            if smn.meraki_id not in net_ids:
                log.info(f"Deleting '{smn.nom}'...")
                smn.delete()

        # refresh devices
        serials = []
        smd: SopMerakiDevice
        if log:
            log.info(f"Looping on '{self.nom}' devices...")
        for dev in conn.organizations.getOrganizationInventoryDevices(
            org["id"], total_pages=-1
        ):
            serials.append(dev["serial"])
            if not SopMerakiDevice.objects.filter(serial=dev["serial"]).exists():
                if log:
                    log.info(
                        f"Creating new DEVICE for '{dev['serial']}' on ORG '{self.nom}'..."
                    )
                smd = SopMerakiDevice()
            else:
                smd = SopMerakiDevice.objects.get(serial=dev["serial"])
            smd.refresh_from_meraki(conn, dev, self, log, details)
        if log:
            log.info(f"Done looping on '{self.nom}' devices, starting cleanup...")
        for smd in self.devices.filter(org__meraki_id=org["id"]):  # type: ignore
            if smd.serial not in serials:
                log.info(f"Orphaning '{smd.nom}'/'{smd.serial}'...")
                smd.orphan_device()

        if log:
            log.info(f"Done cleaning up '{self.nom}'...")

        return save


class SopMerakiNet(NetBoxModel):
    """
    Represents a Meraki Network on the dashboard
    """

    nom = models.CharField(max_length=150, null=False, blank=False, verbose_name="Name")
    site = models.ForeignKey(
        to=Site,
        related_name="meraki_nets",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Site",
    )
    org = models.ForeignKey(
        to=SopMerakiOrg,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        verbose_name="Organization",
        related_name="nets",
    )
    meraki_id = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        unique=True,
        verbose_name="Meraki Network ID",
    )
    ptypes = models.JSONField(
        verbose_name="Product Types",
        default=list,
        blank=True,
        null=True,
    )
    meraki_tags = models.JSONField(
        verbose_name="Tags",
        default=list,
        blank=True,
        null=True,
    )
    bound_to_template = models.BooleanField(default=False, null=True, blank=True)
    meraki_url = models.URLField(null=True, blank=True)
    meraki_notes = models.CharField(max_length=500, null=True, blank=True)
    timezone = TimeZoneField(null=True, blank=True)

    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:sopmerakinet_detail", args=[self.pk])

    class Meta(NetBoxModel.Meta):
        verbose_name = "Meraki Network"
        verbose_name_plural = "Meraki Networks"

    @staticmethod
    def create_or_refresh(
        conn: meraki.DashboardAPI,
        net,
        org: SopMerakiOrg,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        if not SopMerakiNet.objects.filter(meraki_id=net["id"]).exists():
            if log:
                log.info(f"Creating new NET for '{net['id']}' on ORG '{org.nom}'...")
            smn = SopMerakiNet()
        else:
            smn = SopMerakiNet.objects.get(meraki_id=net["id"])
        smn.refresh_from_meraki(conn, net, org, log, details)

    def refresh_from_meraki(
        self,
        conn: meraki.DashboardAPI,
        net,
        org: SopMerakiOrg,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        # cf https://developer.cisco.com/meraki/api-v1/get-organization-networks/
        if log and details:
            log.info(f"Refreshing '{self.nom}'...")
        save = self.pk is None
        if self.nom != net["name"]:
            self.nom = net["name"]
            save = True
        if self.meraki_id != net["id"]:
            self.meraki_id = net["id"]
            save = True
        if self.org_id is None or self.org != org:  # type: ignore
            self.org = org
            save = True
        if self.bound_to_template != net["isBoundToConfigTemplate"]:
            self.bound_to_template = net["isBoundToConfigTemplate"]
            save = True
        if self.meraki_url != net["url"]:
            self.meraki_url = net["url"]
            save = True
        if self.meraki_notes != net["notes"]:
            self.meraki_notes = net["notes"]
            save = True
        if f"{self.timezone}" != f"{net['timeZone']}":
            self.timezone = net["timeZone"]
            save = True
        if not ArrayUtils.equal_sets(self.meraki_tags, net["tags"]):  # type: ignore
            self.meraki_tags = net["tags"]
            save = True
        if not ArrayUtils.equal_sets(self.ptypes, net["productTypes"]):  # type: ignore
            self.ptypes = net["productTypes"]
            save = True
        slug = SopMerakiUtils.extractSiteName(self.nom)
        if slug is None:
            if self.site_id is not None:
                self.site_id = None
        elif not Site.objects.filter(slug=slug).exists():
            if self.site_id is not None:
                self.site_id = None
        else:
            val = Site.objects.get(slug=slug)
            if self.site_id != val.pk:
                self.site = val

        # Prepare Meraki site update
        update_meraki: dict = {}

        # If we have a site , we setup (or fix) certain things
        if self.site is not None:
            # handle tags
            current_tags: list[str] = SopMerakiUtils.only_non_netbox_tags(
                self.meraki_tags  # type: ignore
            )
            netbox_tags: list[str] = SopMerakiUtils.calc_site_netbox_tags(self.site)
            current_tags.extend(netbox_tags)
            if not ArrayUtils.equal_sets(self.meraki_tags, current_tags):  # type: ignore
                self.meraki_tags = current_tags
                save = True
                update_meraki["tags"] = self.meraki_tags
            # handle TZ
            site_tz = self.site.time_zone
            if site_tz is None:
                site_tz = ZoneInfo("UTC")
            if site_tz != self.timezone:
                self.timezone = site_tz
                save = True
                update_meraki["timeZone"] = f"{self.timezone}"

        # push if needed
        if len(update_meraki.keys()):
            try:
                conn.networks.updateNetwork(self.meraki_id, **update_meraki)
            except Exception:
                log.failure(
                    f"Exception when updating Meraki Network '{self.nom}' ({self.meraki_id}) with dict {update_meraki}"
                )
                raise
            log.success(
                f"Updating Meraki Network '[{self.nom}]({self.meraki_url})' : {update_meraki}"
            )

        # only save if something changed
        if save:
            log.success(f"Saving SopMerakiNetwork '[{self.nom}]'.")
            self.full_clean()
            self.save()

        return save

    @staticmethod
    def get_appliance_networks(site: Site) -> list:
        ret: list[SopMerakiNet] = list()
        smns: list[SopMerakiNet] = site.meraki_nets  # type: ignore
        # loop on the site networks
        for smn in smns:
            # skip bound networks
            if smn.bound_to_template:
                continue
            # skip non appliance networks
            if "appliance" not in smn.ptypes:  # type: ignore
                continue
            # add to tentative list
            ret.append(smn)
        # return the list
        return ret

    @staticmethod
    def get_all_networks(site: Site) -> list:
        ret: list[SopMerakiNet] = list()
        smns: list[SopMerakiNet] = site.meraki_nets  # type: ignore
        # loop on the site networks
        for smn in smns:
            # add to tentative list
            ret.append(smn)
        # return the list
        return ret

    @staticmethod
    def get_bound_networks(site: Site) -> list:
        ret: list[SopMerakiNet] = list()
        smns: list[SopMerakiNet] = site.meraki_nets  # type: ignore
        # loop on the site networks
        for smn in smns:
            # skip not bound networks
            if not smn.bound_to_template:
                continue
            # add to tentative list
            ret.append(smn)
        # return the list
        return ret


class SopMerakiDevice(NetBoxModel):

    nom = models.CharField(max_length=150, null=False, blank=False, verbose_name="Name")
    serial = models.CharField(
        max_length=16,
        null=False,
        blank=False,
        unique=True,
        verbose_name="Serial",
        # "Q234-ABCD-5678",
    )
    model = models.CharField(
        max_length=16,
        null=False,
        blank=False,
        verbose_name="Model",
        # "Q234-ABCD-5678",
    )
    mac = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="MAC",
        # "Q234-ABCD-5678",
    )
    meraki_netid = models.CharField(
        max_length=150, null=True, blank=True, verbose_name="Meraki Network ID"
    )
    meraki_network = models.ForeignKey(
        to=SopMerakiNet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Network",
        related_name="devices",
    )
    meraki_notes = models.CharField(max_length=500, null=True, blank=True)
    ptype = models.CharField(
        max_length=50, null=False, blank=False, verbose_name="Product type"
    )
    meraki_tags = models.JSONField(
        verbose_name="Tags",
        default=list,
        blank=True,
        null=True,
    )
    meraki_details = models.JSONField(
        verbose_name="Details",
        default=list,
        blank=True,
        null=True,
    )
    firmware = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Firmware",
        # "Q234-ABCD-5678",
    )
    site = models.ForeignKey(
        to=Site,
        related_name="meraki_devices",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Site",
    )
    org = models.ForeignKey(
        to=SopMerakiOrg,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Organization",
        related_name="devices",
    )
    netbox_dev_type = models.ForeignKey(
        to=DeviceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Device Type",
        related_name="meraki_devices",
    )
    netbox_device = models.ForeignKey(
        to=Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Device",
        related_name="meraki_devices",
    )

    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:sopmerakidevice_detail", args=[self.pk])

    class Meta(NetBoxModel.Meta):
        verbose_name = "Meraki Device"
        verbose_name_plural = "Meraki Devices"

    def refresh_from_meraki(
        self,
        conn: meraki.DashboardAPI,
        dev,
        org: SopMerakiOrg,
        log: JobRunnerLogMixin,
        details: bool,
    ):
        # cf https://developer.cisco.com/meraki/api-v1/get-organization-devices/
        if log and details:
            log.info(f"Refreshing '{self.nom}'...")
        save = self.pk is None
        if self.org_id is None or self.org != org:  # type: ignore
            self.org = org
            save = True
        nameval = dev.get("name", None)
        if nameval is None or nameval.strip() == "":
            nameval = dev.get("mac", None)
        if self.nom != nameval:
            self.nom = nameval
            save = True
        if self.model != dev.get("model", None):
            self.model = dev.get("model", None)
            save = True
        if self.serial != dev.get("serial", None):
            self.serial = dev.get("serial", None)
            save = True
        if self.mac != dev.get("mac", None):
            self.mac = dev.get("mac", None)
            save = True
        if self.meraki_netid != dev.get("networkId", None):
            self.meraki_netid = dev.get("networkId", None)
            save = True
        if self.meraki_notes != dev.get("notes", None):
            self.meraki_notes = dev.get("notes", None)
            save = True
        if self.ptype != dev.get("productType", None):
            self.ptype = dev.get("productType", None)
            save = True
        if self.firmware != dev.get("firmware", None):
            self.firmware = dev.get("firmware", None)
            save = True

        if not ArrayUtils.equal_sets(self.meraki_tags, dev.get("firmware", list())):  # type: ignore
            self.meraki_tags = dev.get("meraki_tags", list())
            save = True
        if not SopUtils.deep_equals_json_ic(
            self.meraki_details, dev.get("details", dict())
        ):
            self.meraki_details = dev.get("details", dict())
            save = True

        # -----------------------------------------------
        # Rattachement/maintenance d'objets dépendants

        # Model <-> device type
        if self.model is not None:
            dts = DeviceType.objects.filter(manufacturer__slug__exact="cisco").filter(
                slug=self.model.lower()
            )
            dt = None
            if dts.exists():
                dt = dts[0]
            if self.netbox_dev_type != dt:
                self.netbox_dev_type = dt
                save = True
        else:
            if self.netbox_dev_type is not None:
                self.netbox_dev_type = None
                save = True

        # Serial <-> device
        if self.serial is not None:
            ds = Device.objects.filter(
                device_type__manufacturer__slug__exact="cisco"
            ).filter(serial__exact=self.serial)
            d = None
            if ds.exists():
                d = ds[0]
            if self.netbox_device != d:
                self.netbox_device = d
                save = True
        else:
            if self.netbox_device is not None:
                self.netbox_device = None
                save = True

        # Net ID <-> Sopmeraki net
        if self.meraki_netid is not None:
            mnets = SopMerakiNet.objects.filter(meraki_id=self.meraki_netid)
            mnet = None
            if mnets.exists():
                mnet = mnets[0]
            if self.meraki_network != mnet:
                self.meraki_network = mnet
                save = True
        else:
            if self.meraki_network is not None:
                self.meraki_network = None
                save = True

        # Sopmeraki net <-> netbox site
        if self.meraki_network is not None:
            st = self.meraki_network.site
            if self.site != st:
                self.site = st
                save = True
        else:
            if self.site is not None:
                self.site = None
                save = True

        # Prepare Meraki site update
        update_meraki: dict = {}

        # push if needed
        if len(update_meraki.keys()):
            try:
                pass
            except Exception:
                log.failure(
                    f"Exception when updating Meraki Device '{self.nom}' ({self.serial}) with dict {update_meraki}"
                )
                raise
            log.success(
                f"Updating Meraki Device '[{self.nom}]({self.serial})' : {update_meraki}"
            )

        # only save if something changed
        if save:
            log.success(f"Saving SopDevice '[{self.nom}]'.")
            self.full_clean()
            self.save()

        return save

    def orphan_device(self):
        self.meraki_netid = None
        self.meraki_network = None
        self.org = None
        self.site = None
        self.full_clean()
        self.save()
