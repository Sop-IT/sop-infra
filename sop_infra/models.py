from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from netbox.models import NetBoxModel
from utilities.choices import ChoiceSet
from dcim.models import Site, Location

from .validators import SopInfraValidator


__all__ = (
    'SopInfra',
    'InfraBoolChoices',
    'InfraTypeChoices',
    'InfraTypeIndusChoices',
    'InfraHubOrderChoices',
    'InfraSdwanhaChoices'
)


class InfraBoolChoices(ChoiceSet):

    CHOICES = (
        ('unknown', _('Unknown'), 'gray'),
        ('true', _('True'), 'green'),
        ('false', _('False'), 'red'),
    )


class InfraTypeChoices(ChoiceSet):

    CHOICES = (
        ('box', _('Simple BOX server')),
        ('superb', _('Super Box')),
        ('sysclust', _('Full cluster')),
    )


class InfraTypeIndusChoices(ChoiceSet):

    CHOICES = (
        ('wrk', _('WRK - Workshop')),
        ('fac', _('FAC - Factory')),
    )


class InfraHubOrderChoices(ChoiceSet):

    CHOICES = (
        ('N_731271989494311779,L_3689011044769857831,N_731271989494316918,N_731271989494316919', 'EQX-NET-COX-DDC'),
        ('N_731271989494316918,N_731271989494316919,N_731271989494311779,L_3689011044769857831', 'COX-DDC-EQX-NET'),
        ('L_3689011044769857831,N_731271989494311779,N_731271989494316918,N_731271989494316919', 'NET-EQX-COX-DDC'),
        ('N_731271989494316919,N_731271989494316918,N_731271989494311779,L_3689011044769857831', 'DDC-COX-EQX-NET'),
    )


class InfraSdwanhaChoices(ChoiceSet):
    
    CHOICES = (
        ('-HA-', _('-HA-')),
        ('-NHA-', _('-NHA-')),
        ('-NO NETWORK-', _('-NO NETWORK-')),
        ('-SLAVE SITE-', _('-SLAVE SITE-')),
        ('-DC-', _('-DC-')),
    )


class SopInfra(NetBoxModel):
    site = models.OneToOneField(
        to=Site,
        on_delete=models.CASCADE,
        unique=True,
        verbose_name=_('Site')
    )
    # ______________
    # Classification
    site_infra_sysinfra = models.CharField(
        choices=InfraTypeChoices,
        null=True,
        blank=True,
        verbose_name=_('System infrastructure')
    )
    site_type_indus = models.CharField(
        choices=InfraTypeIndusChoices,
        null=True,
        blank=True,
        verbose_name=_('Industrial')
    )
    criticity_stars = models.CharField(
        max_length=6,
        null=True,
        blank=True,
        verbose_name=_('Criticity stars')
    )
    site_phone_critical = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('PHONE Critical ?')
    )
    site_type_red = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('R&D ?')
    )
    site_type_vip = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('VIP ?')
    )
    site_type_wms = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('WMS ?')
    )
    #_______
    # Sizing
    ad_cumul_user = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('AD cumul. users')
    )
    est_cumulative_users = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Est. cumul. users')
    )
    site_user_count = models.CharField(
        null=True,
        blank=True
    )
    wan_reco_bw = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Reco. BW (Mbps)')
    )
    site_mx_model = models.CharField(
        max_length=6,
        null=True,
        blank=True,
        verbose_name=_('Reco. MX Model')
    )
    wan_computed_users = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('WAN users')
    )
    #_______
    # Meraki
    sdwanha = models.CharField(
        choices=InfraSdwanhaChoices,
        null=True,
        blank=True,
        verbose_name=_('HA(S) / NHA target')
    )
    hub_order_setting = models.CharField(
        choices=InfraHubOrderChoices,
        null=True,
        blank=True,
        verbose_name=_('HUB order setting')
    )
    hub_default_route_setting = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('HUB default route setting')
    )
    sdwan1_bw = models.CharField(
        null=True,
        blank=True,
        verbose_name=_('WAN1 BW')
    )
    sdwan2_bw = models.CharField(
        null=True,
        blank=True,
        verbose_name=_('WAN2 BW')
    )
    site_sdwan_master_location = models.ForeignKey(
        to=Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('MASTER Location')
    )
    master_site = models.ForeignKey(
        to=Site,
        related_name="master_site",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('MASTER Site')
    )
    migration_sdwan = models.CharField(
        null=True,
        blank=True,
        verbose_name=_('Migration date')
    )
    monitor_in_starting = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('Monitor in starting')
    )

    def __str__(self):
        return f'{self.site} Infrastructure'

    def get_absolute_url(self) -> str:
        return reverse('plugins:sop_infra:sopinfra_detail', args=[self.pk])

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
        return InfraBoolChoices.colors.get(self.hub_default_route_setting)

    def get_criticity_stars(self) -> str:
        html:str = ['<span class="mdi mdi-star-outline"></span>' for _ in self.criticity_stars]
        return mark_safe(''.join(html))

    class Meta(NetBoxModel.Meta):
        verbose_name = _('Infrastructure')
        verbose_name_plural = _('Infrastructures')
        constraints = [
            models.UniqueConstraint(
                fields=['site'],
                name='%(app_label)s_%(class)s_unique_site',
                violation_error_message=_('This site has already an Infrastrcture.')
            ),
            # PostgreSQL doesnt provide database-level constraints with related fields
            # That is why i cannot check if site == master_location__site on db level, only with clean()
            models.CheckConstraint(
                check=~models.Q(site=models.F('master_site')),
                name='%(app_label)s_%(class)s_master_site_equal_site',
                violation_error_message=_('SDWAN MASTER site cannot be itself')
            )
        ]

    def clean(self):
        super().clean()

        # DC site status special case
        if self.site.status == 'dc':
            SopInfraValidator.dc_site_reset_fields(self)

        # slave sites
        if self.site_sdwan_master_location:
            # check that the location doesn't already have another slave site linked to it
            if SopInfra.objects.exclude(pk=self.pk).filter(site_sdwan_master_location=self.site_sdwan_master_location).exists():
                raise ValidationError({
                    'site_sdwan_master_location': 'This location is already the master location for other sites.'
                })
            # check that there is no loop
            if self.site_sdwan_master_location.site == self.site:
                raise ValidationError({
                    'site_sdwan_master_location': 'SDWAN MASTER site cannot be itself'
                })

            # forces the master site to match the master location
            if self.master_site is None:
                self.master_site = self.site_sdwan_master_location.site

            # reset some fields
            SopInfraValidator.slave_site_reset_fields(self)

        # non-slave sites
        else:

            # no master site on non-slave
            self.master_site = None
            # compute user count depending on status
            self.wan_computed_users = SopInfraValidator.count_wan_computed_users(self)
            if self.wan_computed_users is None:
                self.wan_computed_users = 0

            '''
            # if the site is a children, add its compute users to the parent
            target = Site.objects.filter(pk=self.master_site)
            if target.exists():
                parent = SopInfra.objects.filter(site=target.first())
                if parent.exists():
                    parent = parent.first()
                    parent.wan_computed_users += self.wan_computed_users
            '''

            # count site_user_count and fix user slice
            # according to wan computed users
            self.site_user_count, self.site_mx_model = SopInfraValidator.count_and_fix_user_slice(self.wan_computed_users)
            # compute and set recommended bandwidth
            self.wan_reco_bw = SopInfraValidator.set_recommended_bandwidth(self.wan_computed_users)
            

            # compute SDWANHA
            SopInfraValidator.compute_sdwanha(self)

