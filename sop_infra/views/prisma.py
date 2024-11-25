from django.views import View
from django.shortcuts import redirect

from netbox.views import generic
from utilities.permissions import get_permission_for_model
from utilities.views import GetRelatedModelsMixin, ObjectPermissionRequiredMixin

from sop_infra.filtersets import (
    PrismaEndpointFilterset,
    PrismaAccessLocationFilterset,
    PrismaComputedAccessLocationFilterset,
)
from sop_infra.models import (
    SopInfra,
    PrismaEndpoint,
    PrismaAccessLocation,
    PrismaComputedAccessLocation,
)
from sop_infra.forms import (
    PrismaEndpointForm,
    PrismaAccessLocationForm,
    PrismaComputedAccessLocationForm,
    PrismaEndpointFilterForm,
    PrismaAccessLocationFilterForm,
    PrismaComputedAccessLocationFilterForm,
)
from sop_infra.tables import (
    PrismaEndpointTable,
    PrismaAccessLocationTable,
    PrismaComputedAccessLocationTable,
)
from sop_infra.utils import PrismaAccessLocationRecomputeMixin


__all__ = (
    "PrismaEndpointEditView",
    "PrismaEndpointListView",
    "PrismaEndpointDeleteView",
    "PrismaEndpointDetailView",
    "PrismaAccessLocationEditView",
    "PrismaAccessLocationListView",
    "PrismaAccessLocationDeleteView",
    "PrismaAccessLocationDetailView",
    "PrismaAccessLocationRefreshView",
    "PrismaComputedAccessLocationEditView",
    "PrismaComputedAccessLocationListView",
    "PrismaComputedAccessLocationDeleteView",
    "PrismaComputedAccessLocationDetailView",
)


# ______________
# Endpoint


class PrismaEndpointEditView(generic.ObjectEditView):

    queryset = PrismaEndpoint.objects.all()
    form = PrismaEndpointForm


class PrismaEndpointDeleteView(generic.ObjectDeleteView):

    queryset = PrismaEndpoint.objects.all()


class PrismaEndpointListView(generic.ObjectListView):

    queryset = PrismaEndpoint.objects.all()
    table = PrismaEndpointTable
    filterset = PrismaEndpointFilterset
    filterset_form = PrismaEndpointFilterForm


class PrismaEndpointDetailView(generic.ObjectView):

    queryset = PrismaEndpoint.objects.all()

    def get_related_objects(self, instance):
        related = []

        infra = SopInfra.objects.filter(endpoint=instance)
        related.append((infra, "endpoint"))

        return related

    def get_extra_context(self, request, instance) -> dict:
        """
        additional context for related models/objects
        """
        return {
            "infra": SopInfra,
            "related_models": self.get_related_objects(instance),
        }


# ______________
# AccessLocation


class PrismaAccessLocationEditView(generic.ObjectEditView):

    queryset = PrismaAccessLocation.objects.all()
    form = PrismaAccessLocationForm


class PrismaAccessLocationDeleteView(generic.ObjectDeleteView):

    queryset = PrismaAccessLocation.objects.all()


class PrismaAccessLocationListView(generic.ObjectListView):

    template_name: str = "sop_infra/tools/tables.html"
    queryset = PrismaAccessLocation.objects.all()
    table = PrismaAccessLocationTable
    filterset = PrismaAccessLocationFilterset
    filterset_form = PrismaAccessLocationFilterForm

    def get_extra_context(self, request) -> dict:
        """add title context for recompute button in template"""
        context = super().get_extra_context(request)
        context["title"] = "PRISMA Access Locations"
        return context


class PrismaAccessLocationDetailView(generic.ObjectView):

    queryset = PrismaAccessLocation.objects.all()

    def get_related_objects(self, instance):
        related = []

        endpoints = PrismaEndpoint.objects.filter(access_location=instance)
        related.append((endpoints, "access_location"))

        infra = SopInfra.objects.filter(endpoint__in=endpoints)
        related.append((infra, "endpoint"))

        return related

    def get_extra_context(self, request, instance) -> dict:
        """
        additional context for related models/objects
        """
        return {
            "endpoint": PrismaEndpoint,
            "related_models": self.get_related_objects(instance),
        }


class PrismaAccessLocationRefreshView(
    View, PrismaAccessLocationRecomputeMixin, ObjectPermissionRequiredMixin
):

    model = PrismaAccessLocation
    parent = PrismaComputedAccessLocation

    return_url = "/plugins/sop-infra/access_location/"

    def get(self, request):

        # if not perm to change object, raise no permissions
        if not request.user.has_perm(
            get_permission_for_model(PrismaAccessLocation, "view")
        ):
            return self.handle_no_permission()

        self.try_recompute_access_location()
        return redirect(self.return_url)


# ______________
# ComputedAccessLocation


class PrismaComputedAccessLocationEditView(generic.ObjectEditView):

    queryset = PrismaComputedAccessLocation.objects.all()
    form = PrismaComputedAccessLocationForm


class PrismaComputedAccessLocationDeleteView(generic.ObjectDeleteView):

    queryset = PrismaComputedAccessLocation.objects.all()


class PrismaComputedAccessLocationListView(generic.ObjectListView):

    queryset = PrismaComputedAccessLocation.objects.all()
    table = PrismaComputedAccessLocationTable
    filterset = PrismaComputedAccessLocationFilterset
    filterset_form = PrismaComputedAccessLocationFilterForm


class PrismaComputedAccessLocationDetailView(generic.ObjectView):

    queryset = PrismaComputedAccessLocation.objects.all()

    def get_related_objects(self, instance):
        related = []

        access = PrismaAccessLocation.objects.filter(compute_location=instance)
        related.append((access, "compute_location"))

        endpoints = PrismaEndpoint.objects.filter(access_location__in=access)
        related.append((endpoints, "access_location"))

        infra = SopInfra.objects.filter(endpoint__in=endpoints)
        related.append((infra, "endpoint"))

        return related

    def get_extra_context(self, request, instance) -> dict:
        """
        additional context for related models/objects
        """

        return {
            "access_location": PrismaAccessLocation,
            "related_models": self.get_related_objects(instance),
        }
