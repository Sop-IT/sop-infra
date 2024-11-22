from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from timezone_field import TimeZoneField

from netbox.models import NetBoxModel
from ipam.models import IPAddress
from dcim.models import Site


__all__ = (
    'PrismaEndpoint',
    'PrismaAccessLocation',
    'PrismaComputedAccessLocation',
)


class PrismaComputedAccessLocation(NetBoxModel):

    name = models.CharField(
        unique=True,
        blank=True,
        verbose_name=_('Name'),
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name=_('slug'),
    )
    strata_id = models.CharField(
        unique=True,
        blank=True,
        verbose_name=_('Strata ID')
    )
    strata_name = models.CharField(
        blank=True,
        verbose_name=_('Strata name')
    )
    bandwidth = models.PositiveBigIntegerField(
        blank=True,
        verbose_name=_('Bandwidth (Mbps)')
    )

    class Meta(NetBoxModel.Meta):

        verbose_name = _('PRISMA compute location')
        verbose_name_plural = _('PRISMA compute locations')

    def __str__(self) -> str:
        if self.name:
            return f'{self.name}'
        return 'PRISMA Endpoint'

    def clean(self):
        return super().clean()

    def get_absolute_url(self) -> str:
        return reverse('plugins:sop_infra:prismacomputedaccesslocation', args=[self.pk])



class PrismaAccessLocation(NetBoxModel):

    name = models.CharField(
        unique=True,
        blank=True,
        verbose_name=_('Name'),
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name=_('slug'),
    )
    physical_address = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name=_('Physical address'),
        help_text=_('Physical location')
    )
    time_zone = TimeZoneField(
        null=True,
        blank=True,
        verbose_name=_('Time zone'),
    )
    latitude = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name=_('Latitude'),
        help_text=_('GPS coordinate in decimal format (xx.yyyyyy)')
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name=_('Longitude'),
        help_text=_('GPS coordinate in decimal format (xx.yyyyyy)')
    )
    compute_location = models.ForeignKey(
        to=PrismaComputedAccessLocation,
        on_delete=models.CASCADE,
        blank=True,
        verbose_name=_('Computed location'),
    )

    class Meta(NetBoxModel.Meta):

        verbose_name = _('PRISMA access location')
        verbose_name_plural = _('PRISMA access locations')

    def __str__(self) -> str:
        if self.name:
            return f'{self.name}'
        return 'PRISMA Endpoint'

    def clean(self):
        return super().clean()

    def get_absolute_url(self) -> str:
        return reverse('plugins:sop_infra:prismaaccesslocation', args=[self.pk])


class PrismaEndpoint(NetBoxModel):

    name = models.CharField(
        unique=True,
        verbose_name=_('Name')
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name=_('slug')
    )
    ip_address = models.ForeignKey(
        to=IPAddress,
        on_delete=models.CASCADE,
        blank=True,
        verbose_name=_('IP address')
    )
    access_location = models.ForeignKey(
        to=PrismaAccessLocation,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name=_('Access location')
    )
    
    class Meta(NetBoxModel.Meta):

        verbose_name = _('PRISMA endpoint')
        verbose_name_plural = _('PRISMA endpoints')

    def __str__(self) -> str:
        if self.name:
            return f'{self.name}'
        return 'PRISMA Endpoint'

    def clean(self):
        return super().clean()

    def get_absolute_url(self) -> str:
        return reverse('plugins:sop_infra:prismaendpoint', args=[self.pk])

