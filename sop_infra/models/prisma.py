from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from timezone_field import TimeZoneField

from netbox.models import NetBoxModel
from ipam.models import IPAddress


__all__ = (
    "PrismaEndpoint",
    "PrismaAccessLocation",
    "PrismaComputedAccessLocation",
)


class PrismaComputedAccessLocation(NetBoxModel):

    name = models.CharField(
        unique=True,
        blank=True,
        verbose_name=_("Name"),
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name=_("slug"),
    )
    strata_id = models.CharField(
        unique=True, null=True, blank=True, verbose_name=_("Strata ID")
    )
    strata_name = models.CharField(null=True, blank=True, verbose_name=_("Strata name"))
    bandwidth = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name=_("Bandwidth (Mbps)")
    )

    class Meta(NetBoxModel.Meta):

        verbose_name = _("PRISMA compute location")
        verbose_name_plural = _("PRISMA compute locations")
        constraints = [
            models.CheckConstraint(
                check=~Q(name=None),
                name="%(app_label)s_%(class)s_name_none",
                violation_error_message="Name must be set.",
            ),
            models.CheckConstraint(
                check=~Q(slug=None),
                name="%(app_label)s_%(class)s_slug_none",
                violation_error_message="Slug must be set.",
            ),
        ]

    def __str__(self) -> str:
        if self.name:
            return f"{self.name}"
        return "PRISMA Computed Access Location"

    def clean(self):
        super().clean()

    def get_absolute_url(self) -> str:
        return reverse(
            "plugins:sop_infra:prismacomputedaccesslocation_detail", args=[self.pk]
        )


class PrismaAccessLocation(NetBoxModel):

    name = models.CharField(
        unique=True,
        blank=True,
        verbose_name=_("Name"),
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name=_("slug"),
    )
    physical_address = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name=_("Physical address"),
        help_text=_("Physical location"),
    )
    time_zone = TimeZoneField(
        null=True,
        blank=True,
        verbose_name=_("Time zone"),
    )
    latitude = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name=_("Latitude"),
        help_text=_("GPS coordinate in decimal format (xx.yyyyyy)"),
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name=_("Longitude"),
        help_text=_("GPS coordinate in decimal format (xx.yyyyyy)"),
    )
    compute_location = models.ForeignKey(
        to=PrismaComputedAccessLocation,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name=_("Computed location"),
    )

    class Meta(NetBoxModel.Meta):

        verbose_name = _("PRISMA access location")
        verbose_name_plural = _("PRISMA access locations")
        constraints = [
            models.CheckConstraint(
                check=~Q(name=None),
                name="%(app_label)s_%(class)s_name_none",
                violation_error_message="Name must be set.",
            ),
            models.CheckConstraint(
                check=~Q(slug=None),
                name="%(app_label)s_%(class)s_slug_none",
                violation_error_message="Slug must be set.",
            ),
        ]

    def __str__(self) -> str:
        if self.name:
            return f"{self.name}"
        return "PRISMA Endpoint"

    def clean(self):
        super().clean()

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:prismaaccesslocation_detail", args=[self.pk])


class PrismaEndpoint(NetBoxModel):

    name = models.CharField(unique=True, verbose_name=_("Name"))
    slug = models.SlugField(
        max_length=100, unique=True, blank=True, verbose_name=_("slug")
    )
    ip_address = models.ForeignKey(
        to=IPAddress, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_("IP address")
    )
    access_location = models.ForeignKey(
        to=PrismaAccessLocation,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name=_("Access location"),
    )

    class Meta(NetBoxModel.Meta):
        verbose_name = _("PRISMA endpoint")
        verbose_name_plural = _("PRISMA endpoints")
        constraints = [
            models.CheckConstraint(
                check=~Q(name=None),
                name="%(app_label)s_%(class)s_name_none",
                violation_error_message="Name must be set.",
            ),
            models.CheckConstraint(
                check=~Q(slug=None),
                name="%(app_label)s_%(class)s_slug_none",
                violation_error_message="Slug must be set.",
            ),
        ]

    def __str__(self) -> str:
        if self.name:
            return f"{self.name}"
        return "PRISMA Endpoint"

    def clean(self):
        super().clean()

        if self.ip_address and hasattr(self.ip_address, "address"):
            if not str(getattr(self.ip_address, "address")).endswith("/32"):
                raise ValidationError(
                    {"ip_address": "You must enter a /32 IP Address."}
                )

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:prismaendpoint_detail", args=[self.pk])
