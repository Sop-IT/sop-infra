from django.db.models.manager import BaseManager
from django.http.response import HttpResponseRedirect
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
from sop_infra.utils.sop_utils import PrismaAccessLocationRecomputeMixin


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

    queryset: BaseManager[PrismaEndpoint] = PrismaEndpoint.objects.all()
    form = PrismaEndpointForm


class PrismaEndpointDeleteView(generic.ObjectDeleteView):

    queryset: BaseManager[PrismaEndpoint] = PrismaEndpoint.objects.all()


class PrismaEndpointListView(generic.ObjectListView):

    queryset: BaseManager[PrismaEndpoint] = PrismaEndpoint.objects.all()
    table = PrismaEndpointTable
    filterset = PrismaEndpointFilterset
    filterset_form = PrismaEndpointFilterForm


class PrismaEndpointDetailView(GetRelatedModelsMixin, generic.ObjectView):

    queryset: BaseManager[PrismaEndpoint] = PrismaEndpoint.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        """
        additional context for related models/objects
        """
        context = super().get_extra_context(request, instance)
        context["infra"]=SopInfra,
        context["related_models"]=self.get_related_models(request, instance)
        return context


# ______________
# AccessLocation


class PrismaAccessLocationEditView(generic.ObjectEditView):

    queryset: BaseManager[PrismaAccessLocation] = PrismaAccessLocation.objects.all()
    form = PrismaAccessLocationForm


class PrismaAccessLocationDeleteView(generic.ObjectDeleteView):

    queryset: BaseManager[PrismaAccessLocation] = PrismaAccessLocation.objects.all()


class PrismaAccessLocationListView(generic.ObjectListView):

    template_name: str = "sop_infra/tools/tables.html"
    queryset: BaseManager[PrismaAccessLocation] = PrismaAccessLocation.objects.all()
    table = PrismaAccessLocationTable
    filterset = PrismaAccessLocationFilterset
    filterset_form = PrismaAccessLocationFilterForm

    def get_extra_context(self, request) -> dict:
        """add title context for recompute button in template"""
        context = super().get_extra_context(request)
        context["title"] = "PRISMA Access Locations"
        return context


class PrismaAccessLocationDetailView(GetRelatedModelsMixin, generic.ObjectView):

    queryset: BaseManager[PrismaAccessLocation] = PrismaAccessLocation.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        """
        additional context for related models/objects
        """
        context = super().get_extra_context(request, instance)
        context["endpoint"]=PrismaEndpoint,
        context["related_models"]=self.get_related_models(request, instance)
        return context



class PrismaAccessLocationRefreshView(
    View, PrismaAccessLocationRecomputeMixin, ObjectPermissionRequiredMixin
):

    model = PrismaAccessLocation
    parent = PrismaComputedAccessLocation

    return_url: str = "/plugins/sop-infra/access_location/"

    def get(self, request) -> HttpResponseRedirect:

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

    queryset: BaseManager[PrismaComputedAccessLocation] = PrismaComputedAccessLocation.objects.all()
    form = PrismaComputedAccessLocationForm


class PrismaComputedAccessLocationDeleteView(generic.ObjectDeleteView):

    queryset: BaseManager[PrismaComputedAccessLocation] = PrismaComputedAccessLocation.objects.all()


class PrismaComputedAccessLocationListView(generic.ObjectListView):

    queryset: BaseManager[PrismaComputedAccessLocation] = PrismaComputedAccessLocation.objects.all()
    table = PrismaComputedAccessLocationTable
    filterset = PrismaComputedAccessLocationFilterset
    filterset_form = PrismaComputedAccessLocationFilterForm


class PrismaComputedAccessLocationDetailView(GetRelatedModelsMixin, generic.ObjectView):

    queryset: BaseManager[PrismaComputedAccessLocation] = PrismaComputedAccessLocation.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        """
        additional context for related models/objects
        """
        context = super().get_extra_context(request, instance)
        context["access_location"]=PrismaAccessLocation,
        context["related_models"]=self.get_related_models(request, instance)
        return context
