from django.db.models import Count
from netbox.views import generic
from sop_infra.forms import *
from sop_infra.tables import *
from sop_infra.models import *
from django.shortcuts import render, redirect
from django.views import View
from sop_infra.filtersets import *
from django.http import HttpRequest
from sop_infra.jobs import SopMerakiCreateNetworkJob, SopMerakiDashRefreshJob
from netbox.jobs import Job
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import AccessMixin
# from users.models import ObjectPermission, Group, User
# from extras.scripts import Script
from utilities.views import register_model_view, ViewTab, ObjectPermissionRequiredMixin
from utilities.permissions import get_permission_for_model
from utilities.forms import restrict_form_fields


class SopMerakiRefreshDashboardsView(View, ObjectPermissionRequiredMixin):
    """
    refresh the dashboards
    """
    form = SopMerakiRefreshDashboardsForm
    template_name: str = "sop_infra/actions/sopmeraki_refresh_dashboards.html"

    def get(self, request, *args, **kwargs):

        # additional security
        if not request.user.has_perm(get_permission_for_model(SopMerakiNet, "change")):
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
        if not request.user.has_perm(get_permission_for_model(SopMerakiNet, "change")):
            return self.handle_no_permission()

        return_url = reverse("plugins:sop_infra:sopmerakidash_list")

        form = self.form(data=request.POST, files=request.FILES)
        if form.is_valid():
            data: dict = form.cleaned_data
            dashs = data ["dashs"]
            return_url = data["return_url"]
            details = data["details"]
                
            # Launch job
            j:Job=SopMerakiDashRefreshJob.launch_manual(dashs=dashs, details=details)
            # Send to script result
            url=reverse("extras:script_result", args=[j.pk])
            if details:
                url+="?log_threshold=debug"
            return redirect(url)
   

class SopMerakiTriSearchView(View):
    """
    Send to the site or to the filtered site search page
    """

    def get(self, request:HttpRequest, *args, **kwargs):

        tri:str=request.GET['q']
        if tri is None or tri.strip()=="":
            # TODO rechercher l'url pour la vue liste des sites
            return redirect(to="/dcim/sites/")
        
        sites=Site.objects.filter(slug=tri.strip().lower())
        if sites.count()==1 :
            # TODO rechercher l'url pour la vue détails du site
            return redirect(to=f"/dcim/sites/{sites[0].id}")
        # TODO message si pas trouvé
        return redirect(to=f"/dcim/sites/?slug__ic={tri.strip()}")


class SopMerakiDashView(generic.ObjectView):
    queryset = SopMerakiDash.objects.all()
    def get_extra_context(self, request, instance):
        table = SopMerakiOrgTable(
            instance.orgs\
            .annotate(nets_count=Count('nets', distinct=True))\
            .annotate(devices_count=Count('devices', distinct=True))\
        )
        table.configure(request)
        return {
            'orgs_table': table,
        }

class SopMerakiDashListView(generic.ObjectListView):
    queryset = SopMerakiDash.objects.annotate(
        orgs_count=Count('orgs')
    )
    table =  SopMerakiDashTable
    filterset = SopMerakiDashFilterSet
    filterset_form = SopMerakiDashFilterForm

class SopMerakiDashEditView(generic.ObjectEditView):
    queryset = SopMerakiDash.objects.all()
    form = SopMerakiDashForm

class SopMerakiDashDeleteView(generic.ObjectDeleteView):
    queryset = SopMerakiDash.objects.all()


class SopMerakiOrgView(generic.ObjectView):
    queryset = SopMerakiOrg.objects.all()
    def get_extra_context(self, request, instance):
        nets_table = SopMerakiNetTable(instance.nets.all())
        nets_table.configure(request)
        devices_table = SopMerakiNetTable(instance.devices.all())
        devices_table.configure(request)
        return {
            'nets_table': nets_table,
            'devices_table': devices_table
        }
    
class SopMerakiOrgListView(generic.ObjectListView):
    queryset = SopMerakiOrg.objects\
        .annotate(nets_count=Count('nets', distinct=True))\
        .annotate(devices_count=Count('devices', distinct=True))
    table =  SopMerakiOrgTable
    filterset = SopMerakiOrgFilterSet
    filterset_form = SopMerakiOrgFilterForm

class SopMerakiOrgEditView(generic.ObjectEditView):
    queryset = SopMerakiOrg.objects.all()
    form = SopMerakiOrgForm

class SopMerakiOrgDeleteView(generic.ObjectDeleteView):
    queryset = SopMerakiOrg.objects.all()


class SopMerakiNetView(generic.ObjectView):
    queryset = SopMerakiNet.objects.all()

class SopMerakiNetListView(generic.ObjectListView):
    queryset = SopMerakiNet.objects.all()
    table =  SopMerakiNetTable
    filterset = SopMerakiNetFilterSet
    filterset_form = SopMerakiNetFilterForm

class SopMerakiNetEditView(generic.ObjectEditView):
    queryset = SopMerakiNet.objects.all()
    form = SopMerakiNetForm

class SopMerakiNetDeleteView(generic.ObjectDeleteView):
    queryset = SopMerakiNet.objects.all()


class SopMerakiDeviceView(generic.ObjectView):
    queryset = SopMerakiDevice.objects.all()

class SopMerakiDeviceListView(generic.ObjectListView):
    queryset = SopMerakiDevice.objects.all()
    table =  SopMerakiDeviceTable
    filterset = SopMerakiDeviceFilterSet
    filterset_form = SopMerakiDeviceFilterForm

class SopMerakiDeviceEditView(generic.ObjectEditView):
    queryset = SopMerakiDevice.objects.all()
    form = SopMerakiDeviceForm

class SopMerakiDeviceDeleteView(generic.ObjectDeleteView):
    queryset = SopMerakiDevice.objects.all()