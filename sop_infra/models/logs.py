from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from netbox.models import NetBoxModel


class LoggedTask(NetBoxModel):

    name = models.CharField(
        max_length=100,
        null=False, blank=False,
        verbose_name=_("Name"),
    )
    slug = models.SlugField(
        max_length=100, unique=True,
        null=False, blank=False,
        verbose_name=_("slug"),
    )
    tstart=models.DateTimeField(
        null=False, blank=False,
        default=datetime.now()
    )
    tend=models.DateTimeField(
        null=True, blank=True,
    )

    class Meta(NetBoxModel.Meta):

        verbose_name = "LoggedTask"
        verbose_name_plural = "LoggedTasks"
        # TODO : contrainte pour les dates tstart/tend
        # constraints = [
        #     models.CheckConstraint(
        #         check=~Q(name=None),
        #         name="%(app_label)s_%(class)s_name_none",
        #         violation_error_message="Name must be set.",
        #     ),
        #     models.CheckConstraint(
        #         check=~Q(slug=None),
        #         name="%(app_label)s_%(class)s_slug_none",
        #         violation_error_message="Slug must be set.",
        #     ),
        # ]

    def __str__(self) -> str:
        return f"{self.date}-{self.name}"

    # def get_absolute_url(self) -> str:
    #     return reverse(
    #         "plugins:sop_infra:prismacomputedaccesslocation_detail", args=[self.pk]
    #     )



class LogEntry(NetBoxModel):
    task = models.ForeignKey(to=LoggedTask, on_delete=models.PROTECT, related_name="entries")
    tstamp = models.DateTimeField(
        null=False, blank=False,
        default=datetime.now()
    )
     

    name = models.CharField(
        max_length=100,
        null=False, blank=False,
        verbose_name=_("Name"),
    )
    slug = models.SlugField(
        max_length=100, unique=True,
        null=False, blank=False,
        verbose_name=_("slug"),
    )
    date=models.DateTimeField(
        null=False, blank=False,
        default=datetime.now()
    )

    class Meta(NetBoxModel.Meta):

        verbose_name = "LoggedTask"
        verbose_name_plural = "LoggedTasks"
        # constraints = [
        #     models.CheckConstraint(
        #         check=~Q(name=None),
        #         name="%(app_label)s_%(class)s_name_none",
        #         violation_error_message="Name must be set.",
        #     ),
        #     models.CheckConstraint(
        #         check=~Q(slug=None),
        #         name="%(app_label)s_%(class)s_slug_none",
        #         violation_error_message="Slug must be set.",
        #     ),
        # ]

    def __str__(self) -> str:
        return f"{self.date}-{self.name}"

    # def get_absolute_url(self) -> str:
    #     return reverse(
    #         "plugins:sop_infra:prismacomputedaccesslocation_detail", args=[self.pk]
    #     )
