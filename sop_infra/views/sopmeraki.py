from django.db.models import Count
from netbox.views import generic
from sop_infra.forms import *
from sop_infra.tables import *
from sop_infra.models import *
from django.shortcuts import render, redirect
from django.views import View
from sop_infra.filtersets import *
from django.http import HttpRequest
from sop_infra.jobs import SopMerakiDashRefreshJob
from netbox.jobs import Job
from django.urls import reverse




# class SopMerakiCreateNetworksView(View):
#     def get(self, request, pk, *args, **kwargs):
#         # TODO 
#         # ret=SopMerakiUtils.create_meraki_networks(site)
#         # TODO renvoi vers la page source avec un message erreur/OK
#         return redirect(reverse("extras:script_result", args=[j.pk]))
   
   


class SopMerakiRefreshDashboardsView(View):
    """
    refresh the dashboards
    """
    template_name: str = "sop_infra/tools/refresh_dashboards.html"

    def get(self, request, *args, **kwargs):

        # TODO permissions
        #if not request.user.has_perm(get_permission_for_model(SopInfra, "change")):
        #    return self.handle_no_permission()

        #restrict_form_fields(self.form(), request.user)

        j:Job=SopMerakiDashRefreshJob.launch_manual()
        return redirect(reverse("extras:script_result", args=[j.pk]))
   

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