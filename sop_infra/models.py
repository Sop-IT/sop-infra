from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from utilities.choices import ChoiceSet
from netbox.models import NetBoxModel
from dcim.models import Site


__all__ = (
    'InfraClassification',
    'InfraSizing',
    'InfraMerakiSDWAN',
    'InfraTypeChoices',
    'InfraTypeIndusChoices',
    'InfraMerakiHubOrderChoices',
    'InfraSdwanhaChoices',
    'InfraBoolChoices'
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


class InfraMerakiHubOrderChoices(ChoiceSet):

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


class InfraMerakiSDWAN(NetBoxModel):
    site = models.ForeignKey(
        to=Site,
        on_delete=models.CASCADE,
    )
    nha_target = models.CharField(
        choices=InfraSdwanhaChoices
    )
    hub_order_setting = models.CharField(
        choices=InfraMerakiHubOrderChoices
    )
    hub_default_route_setting = models.CharField(
        choices=InfraBoolChoices
    )
    wan1_bw = models.CharField()
    wan2_bw = models.CharField()
    master_location = models.CharField()
    master_site = models.CharField()
    migration_date = models.CharField()
    monitor_in_starting = models.CharField(
        choices=InfraBoolChoices
    )

    def __str__(self)->str:
        return f'{self.site}'

    def get_absolute_url(self)->str:
        return reverse('plugins:sop_infra:inframerakisdwan_detail', args=[self.pk])

    class Meta(NetBoxModel.Meta):
        verbose_name = _('Meraki SDWAN')
        verbose_name_plural = _('Meraki SDWANs')


class InfraSizing(NetBoxModel):
    site = models.ForeignKey(
        to=Site,
        on_delete=models.CASCADE,
    )
    ad_cumul_user = models.CharField(
        blank=True,
        null=True
    )
    est_cumul_user = models.CharField(
        blank=True,
        null=True
    )
    reco_bw = models.CharField(
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        return f'{self.site}'

    def get_absolute_url(self) -> str:
        return reverse('plugins:sop_infra:infrasizing_detail', args=[self.pk])

    class Meta(NetBoxModel.Meta):
        verbose_name = _('Sizing')
        verbose_name_plural = _('Sizings')


class InfraClassification(NetBoxModel):
    site = models.ForeignKey(
        to=Site,
        on_delete=models.CASCADE,
    )
    infrastructure = models.CharField(
        choices=InfraTypeChoices,
    )
    industrial = models.CharField(
        choices=InfraTypeIndusChoices,
    )
    phone_critical = models.CharField(
        max_length=30,
        choices=InfraBoolChoices,
    )
    r_and_d = models.CharField(
        max_length=30,
        choices=InfraBoolChoices,
    )
    vip = models.CharField(
        max_length=30,
        choices=InfraBoolChoices,
    )
    wms = models.CharField(
        max_length=30,
        choices=InfraBoolChoices,
    )

    def __str__(self):
        return f'{self.site}'

    def get_absolute_url(self) -> str:
        return reverse('plugins:sop_infra:infraclassification_detail', args=[self.pk])

    class Meta(NetBoxModel.Meta):
        verbose_name =_('Classification')
        verbose_name_plural=_('Classifications')
