from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from netbox.models import NetBoxModel
from dcim.models import Site, Location

from sop_infra.validators import (
    SopInfraSlaveValidator,
)
from .prisma import *
from .choices import *


__all__ = ("SopInfra",)


class SopInfraUtils():

    @staticmethod
    def get_mx_and_user_slice(wan:int) -> tuple[str,str]:
        if wan < 10 :
            return '<10', 'MX67'
        elif wan < 20 :
            return '10<20', 'MX67'
        elif wan < 50 :
            return '20<50', 'MX68'
        elif wan < 100 :
            return '50<100', 'MX85'
        elif wan < 200 :
            return '100<200', 'MX95'
        elif wan < 500 :
            return '200<500', 'MX95'
        return '>500', 'MX250'

    @staticmethod
    def get_recommended_bandwidth(wan:int) -> int:
        if wan > 100:
            return round(wan * 2.5)
        elif wan > 50:
            return round(wan * 3)
        elif wan > 10:
            return round(wan * 4)
        else:
            return round(wan * 5)

        

class SopInfra(NetBoxModel):
    site = models.OneToOneField(
        to=Site, on_delete=models.CASCADE, unique=True, verbose_name=_("Site"), editable=False
    )
    # ______________
    # Classification / SIZING
    site_infra_sysinfra = models.CharField(
        choices=InfraTypeChoices,
        null=True,
        blank=True,
        verbose_name=_("System infrastructure"),
    )
    site_type_indus = models.CharField(
        choices=InfraTypeIndusChoices,
        null=True,
        blank=True,
        verbose_name=_("Industrial"),
    )
    criticity_stars = models.CharField(
        max_length=6, null=True, blank=True, verbose_name=_("Criticity stars"), editable=False
    )
    site_phone_critical = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_("PHONE Critical ?"),
        help_text=_("Is the phone critical for this site ?"),
    )
    site_type_red = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_("R&D ?"),
        help_text=_("Does the site have and R&D department or a lab ?"),
    )
    site_type_vip = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_("VIP ?"),
        help_text=_("Does the site host VIPs ?"),
    )
    site_type_wms = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_("WMS ?"),
        help_text=_("Does the site run WMS ?"),
    )

    # _______
    # Sizing
    est_cumulative_users_wc = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name=_("Est. users (WC)")
    )
    est_cumulative_users_bc = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name=_("Est. users (BC)")
    )
    est_cumulative_users_ext = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name=_("Est. users (EXT)")
    )
    est_cumulative_users_nom = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name=_("Est. users (NOM)")
    )
    site_user_count = models.CharField(
        null=True, blank=True, verbose_name=_("Site user count"), 
        editable=False,
    )
    wan_reco_bw = models.PositiveBigIntegerField(
        null=True,
        blank=True, editable=False,
        verbose_name=_("Reco. BW (Mbps)"),
        help_text=_("Recommended bandwidth (Mbps)"),
    )
    site_mx_model = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_("Reco. MX Model"),
    )
    wan_computed_users_wc = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("WAN users (WC)"),
        help_text=_("Total computed white collar wan users. (WC)"),
    )
    wan_computed_users_bc = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("WAN users (BC)"),
        help_text=_("Total computed blue collar wan users. (BC)"),
    )
    ad_direct_users_wc = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name=_("AD direct. users (WC)")
    )
    ad_direct_users_bc = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name=_("AD direct. users (BC)")
    )
    ad_direct_users_ext = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name=_("AD direct. users (EXT)")
    )
    ad_direct_users_nom = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name=_("AD direct. users (NOM)")
    )
    # _______
    # SDWAN
    sdwanha = models.CharField(
        choices=InfraSdwanhaChoices,
        null=True,
        blank=True,
        verbose_name=_("HA(S) / NHA target"),
        help_text=_("Calculated target for this site"),
    )
    sdwan1_bw = models.CharField(
        null=True,
        blank=True,
        verbose_name=_("WAN1 BW"),
        help_text=_("SDWAN > WAN1 Bandwidth (real link bandwidth)"),
    )
    sdwan2_bw = models.CharField(
        null=True,
        blank=True,
        verbose_name=_("WAN2 BW"),
        help_text=_("SDWAN > WAN2 Bandwidth (real link bandwidth)"),
    )
    site_sdwan_master_location = models.ForeignKey(
        to=Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("MASTER Location"),
        help_text=_(
            "When this site is an SDWAN SLAVE, you have to materialize a location on the MASTER site and link it here"
        ),
    )
    master_site = models.ForeignKey(
        to=Site,
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("MASTER Site"),
        help_text=_("Or select the MASTER site."),
    )
    migration_sdwan = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Migration date"),
        help_text=_("SDWAN > Site migration date to SDWAN"),
    )
    # _______
    # CENTREON
    monitor_in_starting = models.BooleanField(
        null=True,
        blank=True,
        verbose_name=_("Monitor in starting"),
        help_text=_("Centreon > Start monitoring when starting the site"),
    )
    # _______
    # MERAKI
    hub_order_setting = models.CharField(
        choices=InfraHubOrderChoices,
        null=True,
        blank=True,
        verbose_name=_("HUB order setting"),
        help_text=_("Choose one of the various supported combinations"),
    )
    hub_default_route_setting = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_("HUB default route setting"),
        help_text=_(
            "Set to true if the default route should be sent through the AutoVPN"
        ),
    )
    claim_net_mx=models.ForeignKey(to="SopMerakiNet", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Claim appliances in ")
    claim_net_ms=models.ForeignKey(to="SopMerakiNet", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Claim switches in ")
    claim_net_mr=models.ForeignKey(to="SopMerakiNet", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Claim access points in ")
    # _______
    # PRISMA
    endpoint = models.ForeignKey(
        to=PrismaEndpoint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Prisma Access Tunnel EP"),
    )
    enabled = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_("Enabled ?"),
    )
    valid = models.CharField(
        choices=InfraBoolChoices, null=True, blank=True, verbose_name=_("Valid ?")
    )

    # =============================
    # PROPERTIES

    @property
    def isilog_code(self):
        if self.site is None:
            return None
        if self.site.region is None:
            return None
        if self.site.tenant is None:
            return None
        if self.site.tenant.group is None:
            return None
        return f"{self.site.region.name}-{self.site.tenant.group.name}-{self.site.name}"
    
    @property
    def centreon_active(self)->bool:
        if self.site is None:
            return False
        if self.site.status is None:
            return False
        return self.site.status=="active" or (self.site.status=="starting" and self.monitor_in_starting==True)


    # get_object_color methods are used by NetBoxTable
    # to display choices colors
    def get_site_type_red_color(self) -> str:
        return InfraBoolChoices.colors.get(self.site_type_red)

    def get_site_type_vip_color(self) -> str:
        return InfraBoolChoices.colors.get(self.site_type_vip)

    def get_site_type_wms_color(self) -> str:
        return InfraBoolChoices.colors.get(self.site_type_wms)

    def get_site_phone_critical_color(self) -> str:
        return InfraBoolChoices.colors.get(self.site_phone_critical)

    def get_hub_default_route_setting_color(self) -> str:
        return InfraBoolChoices.colors.get(self.hub_default_route_setting)

    def get_monitor_in_starting_color(self) -> str:
        if self.monitor_in_starting is None:
            return "gray"
        elif  self.monitor_in_starting:
            return "green"
        return "red"

    def get_criticity_stars(self) -> str | None:

        if self.criticity_stars is None:
            return None

        html: list[str] = [
            '<span class="mdi mdi-star-outline" style="color: rgba(218, 165, 32, 1);"></span>'
            for _ in self.criticity_stars
        ]
        return mark_safe("".join(html))
    

    # ===================================
    # DJANGO STD

    class Meta(NetBoxModel.Meta):
        verbose_name = "SOP Infra"
        verbose_name_plural = "SOP Infras"
        constraints = [
            models.UniqueConstraint(
                fields=["site"],
                name="%(app_label)s_%(class)s_unique_site",
                violation_error_message=_("This site has already a 'SOP Infra'."),
            ),
            # PostgreSQL doesnt provide database-level constraints with related fields
            # That is why i cannot check if site == master_location__site on db level, only with clean()
            models.CheckConstraint(
                check=~models.Q(site=models.F("master_site")),
                name="%(app_label)s_%(class)s_master_site_equal_site",
                violation_error_message=_("SDWAN MASTER site cannot be itself"),
            ),
        ]


    def __str__(self):
        return f"{self.site}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:sopinfra_detail", args=[self.pk])



    # =================================================
    # DJANGO OVERRIDES

    def clean(self, *args, **kwargs):
        
        # just to be sure, should never happens
        if self.site is None:
            raise ValidationError({"site": "Infrastructure must be set on a site."})
        
        # dc site__status related validators
        if self.site.status == "dc":
            self.enforce_dc_fields()
            return
        
        if self.is_slave():
            # Enforce master site
            if self.site_sdwan_master_location is not None :
                self.master_site = self.site_sdwan_master_location.site
            # Enforce slave fields
            self.enforce_slave_fields()
            # all slave related validators
            SopInfraSlaveValidator(self)
        else :
            # Normal site, maybe master
            self.compute_sdwanha()

        # recompute user counts and propagate
        self.calc_cumul_and_propagate()

        return super().clean(*args, **kwargs)


    def delete(self, *args, **kwargs):
        # RAZ values for recompute propagation
        self.ad_direct_users_wc=0
        self.ad_direct_users_bc=0
        self.ad_direct_users_ext=0
        self.ad_direct_users_nom=0
        self.est_cumulative_users_wc=0
        self.est_cumulative_users_bc=0
        self.est_cumulative_users_ext=0
        self.est_cumulative_users_nom=0
        # recompute and propagate
        self.calc_cumul_and_propagate()
        # delete
        return super().delete(*args, **kwargs)


    # ===================================================
    # MASTER / SLAVE UTILS

    def is_slave(self) -> bool:
        return self.master_site is not None \
            or self.site_sdwan_master_location is not None


    # ===================================================
    # HNA/NHA UTILS

    def compute_sdwanha(self):
        if self.site.status in [
            'no_infra', 'reserved',
            'template', 'inventory', 'teleworker']:
            # enforce no_infra constraints
            self.sdwanha = '-NO NETWORK-'
            self.sdwan1_bw = None
            self.sdwan2_bw = None
            self.criticity_stars = None
            self.site_infra_sysinfra = None
        else:
            # compute sdwanha for normal sites
            self.sdwanha = '-NHA-'
            self.criticity_stars = '*'
            if self.site_type_vip == 'true':
                self.sdwanha = '-HA-'
                self.criticity_stars = '***'
            # no -HAS- because there is no site_type_indus == IPL
            elif self.site_type_indus == 'fac' \
                or self.site_phone_critical == 'true' \
                or self.site_type_red == 'true' \
                or self.site_type_wms == 'true' \
                or self.site_infra_sysinfra == 'sysclust' \
                or self.site_user_count in ['50<100', '100<200', '200<500', '>500']:
                self.sdwanha = '-HA-'
                self.criticity_stars = '**'


        
    # ===================================================
    # FIELDS ENFORCING

    def enforce_slave_fields(self):
        self.sdwanha = '-SLAVE SITE-'
        self.sdwan1_bw = None
        self.sdwan2_bw = None
        self.migration_sdwan = None
        self.site_type_vip = None
        self.site_type_wms = None
        self.site_type_red = None
        self.site_phone_critical = None
        self.site_infra_sysinfra = None
        self.site_type_indus = None
        self.wan_reco_bw = None
        self.criticity_stars = None
        self.site_mx_model = None


    def enforce_dc_fields(self):
        self.sdwanha = '-DC-'
        self.site_user_count = '-DC'
        self.site_sdwan_master_location = None
        self.master_site = None
        self.wan_reco_bw = None
        self.wan_computed_users_wc = None
        self.wan_computed_users_bc = None
        self.criticity_stars = '****'
        self.site_mx_model = 'MX450'


    # ===================================================
    # USER COUNT UTILS

    def calc_cumul_and_propagate(self)->bool:
        loop=list()
        # calculate cumul
        return self._rec_calc_cumul_and_propagate(loop, False)

    def _rec_calc_cumul_and_propagate(self, loop, save)->bool:
        if self in loop:
            raise Exception("Loop detected when propagating to masters !")
        loop.append(self)
        (wc, bc) = self.calc_wan_computed_users()
        if wc==self.wan_computed_users_bc and bc==self.wan_computed_users_bc:
            # NO change -> no propagation
            return False
        # If we're already propagating, we'll need to snap and save
        if save :
            self.snapshot()
        self.wan_computed_users_wc=wc
        self.wan_computed_users_bc=bc
        self.wan_reco_bw=SopInfraUtils.get_recommended_bandwidth(self.wan_computed_users_wc)
        (self.site_user_count,self.site_mx_model)=SopInfraUtils.get_mx_and_user_slice(self.wan_computed_users_wc)
        # If we're already propagating, we'll need to snap and save
        if save :
            self.save()
        # Try to propagate further
        ms=self.master_site
        if ms is None:
            return True
        si=ms.sopinfra
        if si is None:
            return True
        si._rec_calc_cumul_and_propagate(loop, True)
        return True



    def calc_wan_computed_users(self) -> tuple[int, int]:
        isilog=self.site.custom_field_data.get("site_integration_isilog")
        loop=list()
        return self._rec_calc_site_users(isilog, loop)
    
    def _rec_calc_site_users(self, isilog:str, loop:list) -> tuple[int, int] :
        if self in loop:
            raise Exception("Loop detected when computed users !")
        loop.append(self)
        if isilog=="done":
            wan_wc = self.ad_direct_users_wc
            wan_bc = self.ad_direct_users_bc
        else : 
            wan_wc = self.est_cumulative_users_wc
            wan_bc = self.est_cumulative_users_bc
        if wan_wc is None:
            wan_wc = 0
        if wan_bc is None:
            wan_bc = 0
        slaves = SopInfra.objects.filter(master_site=self.site)
        for slave in slaves:
            tup:tuple[int, int] = slave._rec_calc_site_users(isilog, loop)
            wan_wc += tup[0]
            wan_bc += tup[1]
        return (wan_wc, wan_bc)




