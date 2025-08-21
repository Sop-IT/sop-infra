from django.db.models import Count
from netbox.views import generic
from sop_infra.forms import *
from sop_infra.tables import *
from sop_infra.models import *
from django.shortcuts import render, redirect
from django.views import View
from sop_infra.filtersets import *
from django.http import HttpRequest
from sop_infra.jobs import (
    SopMerakiCreateNetworkJob,
    SopMerakiDashRefreshJob,
    SopMerakiOrgRefreshJob,
    SopMerakiNetRefreshJob,
)
from netbox.jobs import Job
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import AccessMixin
from sop_infra.utils.sop_utils import SopUtils
from utilities.views import ObjectPermissionRequiredMixin, register_model_view
from utilities.permissions import get_permission_for_model
from utilities.forms import restrict_form_fields


class SopMerakiTriSearchView(View):
    """
    Send to the site or to the filtered site search page
    """

    def get(self, request: HttpRequest, *args, **kwargs):

        tri: str = request.GET["q"]
        if tri is None or tri.strip() == "":
            # TODO rechercher l'url pour la vue liste des sites
            return redirect(to="/dcim/sites/")

        sites = Site.objects.filter(slug=tri.strip().lower())
        if sites.count() == 1:
            # TODO rechercher l'url pour la vue détails du site
            return redirect(to=f"/dcim/sites/{sites[0].pk}")
        # TODO message si pas trouvé
        return redirect(to=f"/dcim/sites/?slug__ic={tri.strip()}")


# ========================================================================
# SopMerakiDash


class SopMerakiDashView(generic.ObjectView):
    queryset = SopMerakiDash.objects\
        .annotate(orgs_count=Count("orgs", distinct=True))\
        .annotate(nets_count=Count("orgs__nets", distinct=True))\
        .annotate(devs_count=Count("orgs__devices", distinct=True))


class SopMerakiDashListView(generic.ObjectListView):
    queryset = SopMerakiDash.objects\
        .annotate(orgs_count=Count("orgs", distinct=True))\
        .annotate(nets_count=Count("orgs__nets", distinct=True))\
        .annotate(devs_count=Count("orgs__devices", distinct=True))
    table = SopMerakiDashTable
    filterset = SopMerakiDashFilterSet
    filterset_form = SopMerakiDashFilterForm


class SopMerakiDashEditView(generic.ObjectEditView):
    queryset = SopMerakiDash.objects.all()
    form = SopMerakiDashForm


class SopMerakiDashDeleteView(generic.ObjectDeleteView):
    queryset = SopMerakiDash.objects.all()


class SopMerakiDashRefreshChooseView(View, ObjectPermissionRequiredMixin):
    """
    refresh the dashboards
    """

    form = SopMerakiDashRefreshForm
    template_name: str = "sop_infra/actions/sopmerakidash_refresh.html"

    def get(self, request, *args, **kwargs):

        # additional security
        if not request.user.has_perm(
            get_permission_for_model(SopMerakiDash, "refresh")
        ):
            return self.handle_no_permission()

        restrict_form_fields(self.form(), request.user)

        return render(
            request,
            self.template_name,
            {
                "form": self.form(),
                "return_url": reverse("plugins:sop_infra:sopmerakidash_list"),
            },
        )

    def post(self, request, *args, **kwargs):

        # additional security
        if not request.user.has_perm(
            get_permission_for_model(SopMerakiDash, "refresh")
        ):
            return self.handle_no_permission()

        return_url = reverse("plugins:sop_infra:sopmerakidash_list")

        form = self.form(data=request.POST, files=request.FILES)
        if form.is_valid():
            data: dict = form.cleaned_data
            dashs = data["dashs"]
            return_url = data["return_url"]
            details = data["details"]

            # Launch job
            j: Job = SopMerakiDashRefreshJob.launch_manual(dashs=dashs, details=details)
            # Send to script result
            url = reverse("extras:script_result", args=[j.pk])
            if details:
                url += "?log_threshold=debug"
            return redirect(url)


class SopMerakiDashRefreshView(View, ObjectPermissionRequiredMixin):

    def post(self, request, pk, *args, **kwargs):

        # additional security
        if not request.user.has_perm(
            get_permission_for_model(SopMerakiDash, "refresh")
        ):
            return self.handle_no_permission()

        instance = get_object_or_404(SopMerakiDash, pk=pk)

        if not SopUtils.check_permission(request.user, instance, "refresh"):
            return self.handle_no_permission()

        # Launch job
        j: Job = SopMerakiDashRefreshJob.launch_manual(dashs=[instance], details=False)

        # Send to script result
        url = reverse("extras:script_result", args=[j.pk])
        # if details:
        #     url+="?log_threshold=debug"
        return redirect(url)


# ========================================================================
# SopMerakiOrg


class SopMerakiOrgView(generic.ObjectView):
    queryset = SopMerakiOrg.objects\
        .annotate(nets_count=Count("nets", distinct=True))\
        .annotate(devs_count=Count("devices", distinct=True))


class SopMerakiOrgListView(generic.ObjectListView):
    queryset = SopMerakiOrg.objects\
        .annotate(nets_count=Count("nets", distinct=True))\
        .annotate(devs_count=Count("devices", distinct=True))
    table = SopMerakiOrgTable
    filterset = SopMerakiOrgFilterSet
    filterset_form = SopMerakiOrgFilterForm


class SopMerakiOrgEditView(generic.ObjectEditView):
    queryset = SopMerakiOrg.objects.all()
    form = SopMerakiOrgForm


class SopMerakiOrgDeleteView(generic.ObjectDeleteView):
    queryset = SopMerakiOrg.objects.all()


class SopMerakiOrgRefreshChooseView(AccessMixin, View):

    form = SopMerakiOrgRefreshChooseForm
    template_name: str = "sop_infra/actions/sopmerakiorg_refresh.html"

    def get(self, request, *args, **kwargs):

        # additional security
        if not request.user.has_perm(get_permission_for_model(SopMerakiOrg, "refresh")):
            return self.handle_no_permission()

        restrict_form_fields(self.form(), request.user)

        return render(
            request,
            self.template_name,
            {
                "form": self.form(),
                "return_url": reverse("plugins:sop_infra:sopmerakiorg_list"),
            },
        )

    def post(self, request, *args, **kwargs):

        # additional security
        if not request.user.has_perm(get_permission_for_model(SopMerakiOrg, "refresh")):
            return self.handle_no_permission()

        return_url = reverse("plugins:sop_infra:sopmerakiorg_list")

        form = self.form(data=request.POST, files=request.FILES)
        if form.is_valid():
            data: dict = form.cleaned_data
            orgs = data["orgs"]
            return_url = data["return_url"]
            details = data["details"]

            # Launch job
            j: Job = SopMerakiOrgRefreshJob.launch_manual(orgs=orgs, details=details)
            # Send to script result
            url = reverse("extras:script_result", args=[j.pk])
            if details:
                url += "?log_threshold=debug"
            return redirect(url)


class SopMerakiOrgRefreshView(AccessMixin, View):

    def post(self, request, pk, *args, **kwargs):

        # additional security
        if not request.user.has_perm(get_permission_for_model(SopMerakiOrg, "refresh")):
            return self.handle_no_permission()

        # data=request.POST
        # if not "pk" in data.keys():
        #     return

        # pk = data ["pk"]

        instance = get_object_or_404(SopMerakiOrg, pk=pk)

        if not SopUtils.check_permission(request.user, instance, "refresh"):
            return self.handle_no_permission()

        # Launch job
        j: Job = SopMerakiOrgRefreshJob.launch_manual(orgs=[instance], details=False)

        # Send to script result
        url = reverse("extras:script_result", args=[j.pk])
        # if details:
        #     url+="?log_threshold=debug"
        return redirect(url)


# ========================================================================
# SopMerakiNet


class SopMerakiNetView(generic.ObjectView):
    queryset = SopMerakiNet.objects.all().annotate(
        devs_count=Count("devices", distinct=True)
    )


class SopMerakiNetListView(generic.ObjectListView):
    queryset = SopMerakiNet.objects.all().annotate(
        devs_count=Count("devices", distinct=True)
    )
    table = SopMerakiNetTable
    filterset = SopMerakiNetFilterSet
    filterset_form = SopMerakiNetFilterForm


class SopMerakiNetEditView(generic.ObjectEditView):
    queryset = SopMerakiNet.objects.all()
    form = SopMerakiNetForm


class SopMerakiNetDeleteView(generic.ObjectDeleteView):
    queryset = SopMerakiNet.objects.all()


class SopMerakiNetRefreshChooseView(AccessMixin, View):

    form = SopMerakiNetRefreshChooseForm
    template_name: str = "sop_infra/actions/sopmerakinet_refresh.html"

    def get(self, request, *args, **kwargs):

        # additional security
        if not request.user.has_perm(get_permission_for_model(SopMerakiNet, "refresh")):
            return self.handle_no_permission()

        restrict_form_fields(self.form(), request.user)

        return render(
            request,
            self.template_name,
            {
                "form": self.form(),
                "return_url": reverse("plugins:sop_infra:sopmerakiorg_list"),
            },
        )

    def post(self, request, *args, **kwargs):

        # additional security
        if not request.user.has_perm(get_permission_for_model(SopMerakiNet, "refresh")):
            return self.handle_no_permission()

        return_url = reverse("plugins:sop_infra:sopmerakiorg_list")

        form = self.form(data=request.POST, files=request.FILES)
        if form.is_valid():
            data: dict = form.cleaned_data
            nets = data["nets"]
            return_url = data["return_url"]
            details = data["details"]

            # Launch job
            j: Job = SopMerakiNetRefreshJob.launch_manual(nets=nets, details=details)
            # Send to script result
            url = reverse("extras:script_result", args=[j.pk])
            if details:
                url += "?log_threshold=debug"
            return redirect(url)


class SopMerakiNetRefreshView(AccessMixin, View):

    def post(self, request, pk, *args, **kwargs):

        # additional security
        if not request.user.has_perm(get_permission_for_model(SopMerakiNet, "refresh")):
            return self.handle_no_permission()

        # data=request.POST
        # if not "pk" in data.keys():
        #     return

        # pk = data ["pk"]

        instance = get_object_or_404(SopMerakiNet, pk=pk)

        if not SopUtils.check_permission(request.user, instance, "refresh"):
            return self.handle_no_permission()

        # Launch job
        j: Job = SopMerakiNetRefreshJob.launch_manual(nets=[instance], details=False)

        # Send to script result
        url = reverse("extras:script_result", args=[j.pk])
        # if details:
        #     url+="?log_threshold=debug"
        return redirect(url)


# ========================================================================
# SopMerakiSwitchStack

@register_model_view(SopMerakiSwitchStack)
class SopMerakiSwitchStackView(generic.ObjectView):
    queryset = SopMerakiSwitchStack.objects.all()


@register_model_view(SopMerakiSwitchStack, 'list', path='', detail=False)
class SopMerakiSwitchStackListView(generic.ObjectListView):
    queryset = SopMerakiSwitchStack.objects.all()
    table = SopMerakiSwitchStackTable
    filterset = SopMerakiSwitchStackFilterSet
    filterset_form = SopMerakiSwitchStackFilterForm


@register_model_view(SopMerakiSwitchStack, 'add', detail=False)
@register_model_view(SopMerakiSwitchStack, 'edit')
class SopMerakiSwitchStackEditView(generic.ObjectEditView):
    queryset = SopMerakiSwitchStack.objects.all()
    form = SopMerakiSwitchStackForm


@register_model_view(SopMerakiSwitchStack, 'delete')
class SopMerakiSwitchStackDeleteView(generic.ObjectDeleteView):
    queryset = SopMerakiSwitchStack.objects.all()


# ========================================================================
# SopMerakiDevice

@register_model_view(SopMerakiDevice)
class SopMerakiDeviceView(generic.ObjectView):
    queryset = SopMerakiDevice.objects.all()


@register_model_view(SopMerakiDevice, 'list', path='', detail=False)
class SopMerakiDeviceListView(generic.ObjectListView):
    queryset = SopMerakiDevice.objects.all()
    table = SopMerakiDeviceTable
    filterset = SopMerakiDeviceFilterSet
    filterset_form = SopMerakiDeviceFilterForm


@register_model_view(SopMerakiDevice, 'add', detail=False)
@register_model_view(SopMerakiDevice, 'edit')
class SopMerakiDeviceEditView(generic.ObjectEditView):
    queryset = SopMerakiDevice.objects.all()
    form = SopMerakiDeviceForm


@register_model_view(SopMerakiDevice, 'delete')
class SopMerakiDeviceDeleteView(generic.ObjectDeleteView):
    queryset = SopMerakiDevice.objects.all()
