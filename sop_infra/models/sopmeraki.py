from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now as django_now

from netbox.models import NetBoxModel
from netbox.models.features import *
from dcim.models import Site, DeviceType, Device

from sop_infra.models.choices import SopMerakiStpGuardChoices
from sop_infra.utils.mixins import JobRunnerLogMixin
from timezone_field import TimeZoneField
from utilities.querysets import RestrictedQuerySet

import meraki



__all__ = (
    "SopMerakiDash",
    "SopMerakiOrg",
    "SopMerakiNet",
    "SopMerakiSwitchStack",
    "SopMerakiDevice",
    "SopMerakiSwitchSettings",
)


class SopMerakiDash(JobsMixin, NetBoxModel):
    """
    Represents a Meraki dashboard
    """

    objects = RestrictedQuerySet.as_manager()
    
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
        permissions = [
            ('refresh', 'Refresh from dashboard'),
        ]


class SopMerakiOrg(JobsMixin, NetBoxModel):
    """
    Represents a Meraki Organisation, child of a Meraki dashboard
    """

    objects = RestrictedQuerySet.as_manager()

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
    meraki_api = models.JSONField(
        verbose_name="API",
        default=dict,
        blank=True,
        null=True,
    )
    meraki_cloud = models.JSONField(
        verbose_name="Cloud",
        default=dict,
        blank=True,
        null=True,
    )    
    meraki_licensing = models.JSONField(
        verbose_name="Licensing",
        default=dict,
        blank=True,
        null=True,
    )  

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
        permissions = [
            ('claim', 'Claim new devices'),
            ('refresh', 'Refresh from dashboard'),
        ]


class SopMerakiNet(JobsMixin, NetBoxModel):
    """
    Represents a Meraki Network on the dashboard
    """

    objects = RestrictedQuerySet.as_manager()

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

    vpn_mode=models.CharField(
        verbose_name="VPN Mode",
        max_length=20,
        blank=True,
        null=True,    
    )
    appliance_status=models.CharField(
        verbose_name="Appliance status",
        max_length=20,
        blank=True,
        null=True,    
    )
    meraki_peers_reachability=models.CharField(
        verbose_name="Meraki peers reachability",
        max_length=20,
        blank=True,
        null=True,    
    )
    exp_subnets_count=models.IntegerField(
        verbose_name="# of exported subnets",
        blank=True,
        null=True,    
    )
    last_stats_change=models.DateTimeField(
        verbose_name="Last stats change",
        default=django_now,
        blank=True,
        null=True,    
    )

    primary_mx=models.OneToOneField(
        to="SopMerakiDevice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Primary MX",
        related_name="net_where_primary",
    )
    secondary_mx=models.OneToOneField(
        to="SopMerakiDevice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Secondary MX",
        related_name="net_where_secondary",
    )

    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:sopmerakinet", args=[self.pk])

    class Meta(NetBoxModel.Meta):
        verbose_name = "Meraki Network"
        verbose_name_plural = "Meraki Networks"
        permissions = [
            ('refresh', 'Refresh from dashboard'),
            ('move', 'Move'),
        ]

    @property
    def is_ha(self) -> bool:
        pmx:SopMerakiDevice|None
        try:
            pmx = self.primary_mx
        except SopMerakiDevice.DoesNotExist:
            pmx =  None
        if pmx is None:
            return False
        smx:SopMerakiDevice|None
        try:
            smx = self.secondary_mx
        except SopMerakiDevice.DoesNotExist:
            smx =  None
        if smx is None:
            return False
        return True
    


class SopMerakiSwitchStack(
    BookmarksMixin,
    ChangeLoggingMixin,
    #CloningMixin,
    #CustomFieldsMixin,
    #CustomLinksMixin,
    #CustomValidationMixin,
    #ExportTemplatesMixin,
    #JournalingMixin,
    NotificationsMixin,
    TagsMixin,
    #EventRulesMixin, 
    models.Model):

    objects = RestrictedQuerySet.as_manager()

    meraki_id = models.CharField(
        max_length=50, null=False, blank=False, verbose_name="Meraki Stack ID"
    )
    nom = models.CharField(max_length=50, null=False, blank=False, verbose_name="Name")
    net = models.ForeignKey(
        to=SopMerakiNet, on_delete=models.CASCADE, null=False, blank=False, related_name="switch_stacks"
    )
    site = models.ForeignKey(
        to=Site,
        related_name="meraki_switchstacks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Site",
    )
    serials = models.JSONField(
        verbose_name="Serials",
        default=list,
        blank=True,
        null=True,
    )
    members = models.JSONField(
        verbose_name="Members",
        default=list,
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse(
            "plugins:sop_infra:sopmerakiswitchstack", args=[self.pk]
        )

    class Meta(NetBoxModel.Meta): # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = "Meraki Switch Stack"
        verbose_name_plural = "Meraki Switch Stacks"



class SopMerakiDevice(
    BookmarksMixin,
    ChangeLoggingMixin,
    #CloningMixin,
    #CustomFieldsMixin,
    #CustomLinksMixin,
    #CustomValidationMixin,
    #ExportTemplatesMixin,
    #JournalingMixin,
    NotificationsMixin,
    TagsMixin,
    #EventRulesMixin, 
    models.Model):

    objects = RestrictedQuerySet.as_manager()

    nom = models.CharField(max_length=150, null=False, blank=False, verbose_name="Name")
    serial = models.CharField(
        max_length=16,
        null=False,
        blank=False,
        unique=True,
        verbose_name="Serial",
        # "Q234-ABCD-5678",
    )
    model_name = models.CharField(
        max_length=16,
        null=False,
        blank=False,
        verbose_name="Model",
    )
    mac = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="MAC",
    )
    meraki_netid = models.CharField(
        max_length=150, null=True, blank=True, verbose_name="Meraki Network ID" 
    )
    meraki_network = models.ForeignObject(
        to=SopMerakiNet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        to_fields=["meraki_id"],
        from_fields=["meraki_netid"],
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
    meraki_url = models.URLField(null=True, blank=True)
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
    # Netbox
    netbox_dev_type = models.ForeignKey(
        to=DeviceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Device Type",
        related_name="meraki_devices",
    )
    netbox_device = models.OneToOneField(
        to=Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Device",
        related_name="meraki_device",
    )
    # switch stack
    stack = models.ForeignKey(
        to=SopMerakiSwitchStack,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="meraki_devices",
    )
    lan_ip=models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=False,
    )
    cfg_updated_at=models.DateTimeField(null=True, 
        blank=True,
        unique=False,)
    latitude = models.DecimalField(
        verbose_name=_('latitude'),
        max_digits=8,
        decimal_places=6,
        blank=True,
        null=True,
        help_text=_('GPS coordinate in decimal format (xx.yyyyyy)')
    )
    longitude = models.DecimalField(
        verbose_name=_('longitude'),
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text=_('GPS coordinate in decimal format (xx.yyyyyy)')
    )

    wan1ip = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=False,
    )
    wan2ip = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=False,
    )
    wan1status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=False,
    )
    wan2status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=False,
    )
    last_reported_at=models.DateTimeField(
        verbose_name="Last reported at",
        default=django_now,
        blank=True,
        null=True,    
    )

    sku= models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=False,
    )
    claimed_at=models.DateTimeField(null=True, 
        blank=True,
        unique=False,)
    license_expiration_at=models.DateTimeField(null=True, 
            blank=True,
            unique=False,)
    country_code= models.CharField(
        max_length=2,
        null=True,
        blank=True,
        unique=False,
    ) 
    eox_status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        unique=False,
    )
    eox_end_of_sale=models.DateTimeField(null=True, 
        blank=True,
        unique=False,)
    eox_end_of_support=models.DateTimeField(null=True, 
        blank=True,
        unique=False,)      

    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:sopmerakidevice", args=[self.pk])

    class Meta(NetBoxModel.Meta): # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = "Meraki Device"
        verbose_name_plural = "Meraki Devices"
        permissions = [
            ('move', 'Move'),
        ]
    # ------------------ CHECKS
    @property
    def has_netbox_device(self) -> bool:
        nd:Device|None
        try:
            nd = self.netbox_device
        except Device.DoesNotExist:
            nd =  None
        return nd is not None

    @property
    def has_netbox_device_in_same_site(self) -> bool:
        nd:Device|None
        try:
            nd = self.netbox_device
        except Device.DoesNotExist:
            nd =  None
        if nd is None:
            return False
        ms:Site|None
        try:
            ms = self.site
        except Site.DoesNotExist:
            ms =  None
        if ms is None:
            # meraki device not in a site -> shortcircuit
            return True
        ns:Site|None
        try:
            ns = nd.site
        except Site.DoesNotExist:
            ns =  None
        if ns is None:
            return False
        return ns==ms
    
    @property
    def has_netbox_device_of_same_type(self) -> bool:
        nd:Device|None
        try:
            nd = self.netbox_device
        except Device.DoesNotExist:
            nd =  None
        if nd is None:
            return False
        ndt:DeviceType|None
        try:
            ndt = nd.device_type
        except Device.DoesNotExist:
            ndt =  None
        if ndt is None:
            return False
        return self.model_name==ndt.part_number

    def orphan_device(self):
        self.meraki_netid = None
        #self.meraki_network = None
        self.org = None
        self.site = None
        self._changelog_message="SopMerakiDevice.orphan_device"
        self.full_clean()
        self.save()



class SopMerakiSwitchSettings(NetBoxModel):

    objects = RestrictedQuerySet.as_manager()

    nom = models.CharField(
        max_length=50, null=False, blank=False, unique=True, verbose_name="Name"
    )
    uplinkClientSampling_enabled = models.BooleanField(
        null=False, blank=True, default=False
    )
    macBlocklist_enabled = models.BooleanField(null=False, blank=True, default=False)

    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse(
            "plugins:sop_infra:sopmerakiswitchsettings_detail", args=[self.pk]
        )

    class Meta(NetBoxModel.Meta):
        verbose_name = "Meraki Switch Settings"
        verbose_name_plural = "Meraki Switches Settings"


class SopMerakiSwitchPortSettings(NetBoxModel):

    objects = RestrictedQuerySet.as_manager()

    port_id = models.CharField(
        max_length=20, null=False, blank=False, unique=True, verbose_name="Port ID",
    )
    nom = models.CharField(
        max_length=50, null=False, blank=False, unique=True, verbose_name="Name",
    )
    port_enabled=models.BooleanField(
        null=False, blank=False, default=False, 
    )
    switchport_mode = models.CharField(
        max_length=20, null=False, blank=False,
    )
    vlan = models.IntegerField(
        null=True, blank=True, 
    )
    voice_vlan = models.IntegerField(
        null=True, blank=True, 
    )
    allowed_vlans = models.CharField(
        max_length=250, null=True, blank=True, unique=True, 
    )
    rstp_enabled = models.BooleanField(null=False, blank=False, default=False,)
    stp_guard = models.CharField(
        choices=SopMerakiStpGuardChoices,
        null=False, blank=False, default="disabled",
    )

    def __str__(self):
        return f"{self.port_id}-{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse(
            "plugins:sop_infra:sopmerakiswitchportsettings_detail", args=[self.pk]
        )

    class Meta(NetBoxModel.Meta):
        verbose_name = "Meraki Switch Port Settings"
        verbose_name_plural = "Meraki Switch Ports Settings"
