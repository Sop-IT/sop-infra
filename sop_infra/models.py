from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from netbox.models import NetBoxModel
from utilities.choices import ChoiceSet
from dcim.models import Site, Location

from .validators.model_validators import (
    DC_status_site_fields,
    SopInfraSlaveValidator,
    SopInfraMasterValidator
)


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
        verbose_name=_('System infrastructure'),
    )
    site_type_indus = models.CharField(
        choices=InfraTypeIndusChoices,
        null=True,
        blank=True,
        verbose_name=_('Industrial'),
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
        verbose_name=_('PHONE Critical ?'),
        help_text=_('Is the phone critical for this site ?')
    )
    site_type_red = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('R&D ?'),
        help_text=_('Does the site have and R&D department or a lab ?')
    )
    site_type_vip = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('VIP ?'),
        help_text=_('Does the site host VIPs ?')
    )
    site_type_wms = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('WMS ?'),
        help_text=_('Does the site run WMS ?')
    )
    #_______
    # Sizing
    est_cumulative_users = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Est. cumul. users')
    )
    site_user_count = models.CharField(
        null=True,
        blank=True,
        help_text=_('Site user count')
    )
    wan_reco_bw = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Reco. BW (Mbps)'),
        help_text=_('Recommended bandwidth (Mbps)')       
    )
    site_mx_model = models.CharField(
        max_length=6,
        null=True,
        blank=True,
        verbose_name=_('Reco. MX Model'),
    )
    wan_computed_users = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('WAN users'),
        help_text=_('Total computed wan users.')
    )
    ad_direct_users = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_('AD direct. users')
    )
    #_______
    # Meraki
    sdwanha = models.CharField(
        choices=InfraSdwanhaChoices,
        null=True,
        blank=True,
        verbose_name=_('HA(S) / NHA target'),
        help_text=_('Calculated target for this site'),
    )
    hub_order_setting = models.CharField(
        choices=InfraHubOrderChoices,
        null=True,
        blank=True,
        verbose_name=_('HUB order setting'),
        help_text=_('Choose one of the various supported combinations')
    )
    hub_default_route_setting = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('HUB default route setting'),
        help_text=_('Set to true if the default route should be sent through the AutoVPN'),
    )
    sdwan1_bw = models.CharField(
        null=True,
        blank=True,
        verbose_name=_('WAN1 BW'),
        help_text=_('SDWAN > WAN1 Bandwidth (real link bandwidth)'),
    )
    sdwan2_bw = models.CharField(
        null=True,
        blank=True,
        verbose_name=_('WAN2 BW'),
        help_text=_('SDWAN > WAN2 Bandwidth (real link bandwidth)')
    )
    site_sdwan_master_location = models.ForeignKey(
        to=Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('MASTER Location'),
        help_text=_('When this site is an SDWAN SLAVE, you have to materialize a location on the MASTER site and link it here')
    )
    master_site = models.ForeignKey(
        to=Site,
        related_name="master_site",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('MASTER Site'),
        help_text=_('Or select the MASTER site.')
    )
    migration_sdwan = models.CharField(
        null=True,
        blank=True,
        verbose_name=_('Migration date'),
        help_text=_('SDWAN > Site migration date to SDWAN')
    )
    monitor_in_starting = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True,
        verbose_name=_('Monitor in starting'),
        help_text=_('Centreon > Start monitoring when starting the site')
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

    def get_criticity_stars(self) -> str | None:

        if self.criticity_stars is None:
            return None

        html: str = [
            '<span class="mdi mdi-star-outline" style="color: rgba(218, 165, 32, 1);"></span>' 
            for _ in self.criticity_stars
        ]
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

    def compute_wan_cumulative_users(self, instance) -> int:

        base:int|None = instance.wan_computed_users

        # assume base is never None
        if base is None:
            base = 0

        # check if this is a master site
        targets = SopInfra.objects.filter(master_site=instance.site)

        if targets.exists():
            # if it is, ad slave's wan computed user to master site
            for target in targets:

                # only add if isinstance integer and not None
                if target.wan_computed_users is not None \
                    and isinstance(target.wan_computed_users, int):

                    base += target.wan_computed_users

        return base

    def clean(self):
        '''
        plenty of validators and auto-compute methods in this clean()

        to keep the code readable, cleaning methods are
        separated in class in validators.py file.
        '''

        super().clean()

        # just to be sure, should never happens
        if self.site is None:
            raise ValidationError({
                'site': 'Infrastructure must be set on a site.'
            })

        # dc site__status related validators
        if self.site.status == 'dc':
            DC_status_site_fields(self)
            return

        # all slave related validators
        SopInfraSlaveValidator(self)

        # all non-slave related validators
        SopInfraMasterValidator(self)


    def delete(self, *args, **kwargs):

        # check if it is a child
        if self.master_site is not None:

            parent = SopInfra.objects.filter(site=self.master_site)
            super().delete(*args, **kwargs)

            # if parent exists, recompute its sizing
            if parent.exists():
                master = parent.first()
                master.snapshot()
                master.full_clean()
                master.save()

        if self.id is not None:
            return super().delete(*args, **kwargs)

