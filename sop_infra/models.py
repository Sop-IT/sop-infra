from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from netbox.models import NetBoxModel
from utilities.choices import ChoiceSet
from dcim.models import Site, Location


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
        unique=True
    )
    # ______________
    # Classification
    site_infra_sysinfra = models.CharField(
        choices=InfraTypeChoices,
        null=True,
        blank=True
    )
    site_type_indus = models.CharField(
        choices=InfraTypeIndusChoices(),
        null=True,
        blank=True
    )
    site_phone_critical = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True
    )
    site_type_red = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True
    )
    site_type_vip = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True
    )
    site_type_wms = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True
    )
    #_______
    # Sizing
    ad_cumul_user = models.PositiveBigIntegerField(
        null=True,
        blank=True
    )
    est_cumulative_users = models.PositiveBigIntegerField(
        null=True,
        blank=True
    )
    wan_reco_bw = models.PositiveBigIntegerField(
        null=True,
        blank=True
    )
    wan_computed_users = models.PositiveBigIntegerField(
        null=True,
        blank=True
    )
    #_______
    # Meraki
    sdwanha = models.CharField(
        choices=InfraSdwanhaChoices,
        null=True,
        blank=True,
    )
    hub_order_setting = models.CharField(
        choices=InfraHubOrderChoices,
        null=True,
        blank=True
    )
    hub_default_route_setting = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True
    )
    sdwan1_bw = models.CharField(
        null=True,
        blank=True
    )
    sdwan2_bw = models.CharField(
        null=True,
        blank=True
    )
    site_sdwan_master_location = models.ForeignKey(
        to=Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    master_site = models.ForeignKey(
        to=Site,
        related_name="master_site",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    migration_sdwan = models.CharField(
        null=True,
        blank=True
    )
    monitor_in_starting = models.CharField(
        choices=InfraBoolChoices,
        null=True,
        blank=True
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

    class Meta(NetBoxModel.Meta):
        verbose_name = _('Infrastructure')
        verbose_name_plural = _('Infrastructures')
        constraints = [
            models.UniqueConstraint(
                fields=['site'],
                name='%(app_label)s_%(class)s_unique_site',
                violation_error_message=_('This site has already an Infrastrcture.')
            )
        ]

