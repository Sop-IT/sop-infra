from django.db.models import Count
from netbox.views import generic
from sop_infra.forms import *
from sop_infra.tables import *
from sop_infra.models import *
from django.shortcuts import render
from django.views import View
from sop_infra.filtersets import *


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

        SopMerakiUtils.refresh_dashboards()

        return render(
            request,
            self.template_name
        )



class SopMerakiDashView(generic.ObjectView):
    queryset = SopMerakiDash.objects.all()
    def get_extra_context(self, request, instance):
        table = SopMerakiDashTable(instance.orgs.all())
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
        table = SopMerakiNetTable(instance.nets.all())
        table.configure(request)
        return {
            'nets_table': table,
        }
    
class SopMerakiOrgListView(generic.ObjectListView):
    queryset = SopMerakiOrg.objects.annotate(
        nets_count=Count('nets')
    )
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