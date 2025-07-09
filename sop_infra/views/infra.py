import json
from django.http import Http404, HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.urls import reverse
from django.db.models import Q, Count
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden
from netbox.jobs import Job

from sop_infra.jobs import SopSyncAdUsers
from utilities.views import register_model_view, ViewTab, ObjectPermissionRequiredMixin
from utilities.permissions import get_permission_for_model
from utilities.forms import restrict_form_fields
from netbox.views import generic

from dcim.models import Site
from ipam.models import Prefix
from tenancy.models import Contact

from sop_infra.forms import *
from sop_infra.tables import SopInfraTable 
from sop_infra.models import *
from sop_infra.filtersets import SopInfraFilterset
from sop_infra.utils.sop_utils import SopInfraRelatedModelsMixin, SopInfraRefreshMixin


__all__ = (
    "SopInfraSiteTabView",
    "SopMerakiSiteTabView",
    "SopInfraAddView",
    "SopInfraEditView",
    "SopInfraListView",
    "SopInfraDeleteView",
    "SopInfraDetailView",
    "SopInfraRefreshView",
    "SopInfraRefreshNoForm",
    # "SopInfraBulkEditView",
    # "SopInfraBulkDeleteView",
    "SopInfraJsonExportsAdSites",
    "SopInfraJsonExportsAdUsers", 
)

class SopInfraSyncAdUsers(View):
    """
    Sync the users from AD
    """
    def get(self, request, *args, **kwargs):

        # TODO permissions
        #if not request.user.has_perm(get_permission_for_model(SopInfra, "change")):
        #    return self.handle_no_permission()

        #restrict_form_fields(self.form(), request.user)

        j:Job=SopSyncAdUsers.launch_manual()
        return redirect(reverse("extras:script_result", args=[j.pk]))
   

class SopInfraJsonExportsAdUsers(View):

    def get(self, request:HttpRequest, *args, **kwargs):

        contsdict:dict[int,dict[str,int]]=dict()
        conts=Contact.objects.filter(custom_field_data__ad_acct_disabled=False)\
            .filter(custom_field_data__ad_site_id__gt=1)\
            .values("custom_field_data__ad_site_id",  "custom_field_data__ad_site_name", "custom_field_data__ad_extAtt7")\
            .annotate(dcount=Count('custom_field_data__ad_site_id'))\
            .order_by()
        dc:dict[str,int]
        for v in conts.all(): 
            k=v.get('custom_field_data__ad_site_id')
            if k in contsdict.keys():
                dc=contsdict.get(k)
            else:
                dc=dict()
            collar=v.get("custom_field_data__ad_extAtt7")
            if collar in ['0','1']:
                dc[collar]=v.get("dcount")
                contsdict[k]=dc
        return JsonResponse(contsdict, safe=False)
    



class SopInfraJsonExportsAdSites(View):

    def get(self, request:HttpRequest, *args, **kwargs):

        # TODO : permettre de passer le status et le slug du role en arguments
        status:Q=Q(Q(status='active')|Q(status='noncompliant')|Q(status='decommissioning'))
        role:Q=Q(role__slug='usr')
        vrf:Q=Q(vrf_id=None)
        vlan:Q=~Q(vlan_id=None)
        visible:Q=Q(custom_field_data__meraki_visible=True)
        scope_type:Q=Q(scope_type_id=ContentType.objects.get_by_natural_key('dcim', 'site').pk)
        vlan_role:Q=Q(vlan__role__slug='usr')
        pfs=Prefix.objects.filter(status, role, vlan, vrf, visible, scope_type, vlan_role)

        exp:list[dict[str,str]]=[]
        for pf in pfs:
            d:dict[str,str]=dict()
            d['trigram']=pf.scope.slug
            d['vlan_id']=pf.vlan.vid
            d['prefix']=f"{pf.prefix}"
            d['vlan_role']=pf.vlan.role.slug
            d['tenant_group']=pf.scope.tenant.group.slug
            exp.append(d)
        return JsonResponse(exp, safe=False)


@register_model_view(Site, name="infra", detail=True)
class SopInfraSiteTabView(SopInfraRelatedModelsMixin, generic.ObjectView):
    """
    creates an "infrastructure" tab on the site page
    """
    tab = ViewTab(
        label="SOP Infra", permission=get_permission_for_model(SopInfra, "view")
    )
    template_name: str = "sop_infra/tab/sopinfra_on_site.html"
    # On s'affiche sur un site
    queryset = Site.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        context = super().get_extra_context(request, instance)
        if not instance:
            raise Http404(
            "No instance given."
        )
        context["site"] = instance
        if not instance.sopinfra:
            instance.sopinfra = SopInfra.objects.create(site=instance)
        context["infra"] = instance.sopinfra    
        return context

    
@register_model_view(Site, name="sopmeraki")
class SopMerakiSiteTabView(SopInfraRelatedModelsMixin, generic.ObjectView):
    """
    creates an "SOP Meraki" tab on the site page
    """
    tab = ViewTab(
        label="SOP Meraki", permission=get_permission_for_model(SopInfra, "view")
    )
    template_name: str = "sop_infra/tab/sopmeraki_on_site.html"
    queryset = Site.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        context = super().get_extra_context(request, instance)
        if not instance:
            raise Http404(
            "No instance given."
        )
        context["site"] = instance
        if not instance.sopinfra:
            instance.sopinfra = SopInfra.objects.create(site=instance)
        context["infra"] = instance.sopinfra    
        return context






# ____________________________
# SOP INFRA BASE MODEL VIEWS


class SopInfraDeleteView(generic.ObjectDeleteView):
    """
    deletes an existing SopInfra instance
    """

    queryset = SopInfra.objects.all()


class SopInfraEditView(generic.ObjectEditView):
    """
    edits an existing SopInfra instance
    """

    template_name: str = "sop_infra/tools/forms.html"
    queryset = SopInfra.objects.all()
    form = SopInfraForm

    def get_return_url(self, request, obj):
        if obj.site:
            return f"/dcim/sites/{obj.site.id}/infra"

    def get_extra_context(self, request, obj):
        context = super().get_extra_context(request, obj)
        if not obj:
            return context
        context["object_type"] = obj
        return context


class SopInfraAddView(generic.ObjectEditView):
    """
    adds a new SopInfra instance
    if the request is from the site page,
    -> the site id is passed as an argument (pk)
    """

    queryset = SopInfra.objects.all()
    form = SopInfraForm

    def get_object(self, **kwargs):
        """ """
        if "pk" in kwargs:
            site = get_object_or_404(Site, pk=kwargs["pk"])
            obj = self.queryset.model
            return obj(site=site)
        return super().get_object(**kwargs)

    def alter_object(self, obj, request, args, kwargs):
        """ """
        if "pk" in kwargs:
            site = get_object_or_404(Site, pk=kwargs["pk"])
            obj = self.queryset.model
            return obj(site=site)
        return super().alter_object(obj, request, args, kwargs)

    def get_return_url(self, request, obj):
        try:
            return f"/dcim/sites/{obj.site.id}/infra"
        except:
            return f"/plugins/sop_infra/list"



# ____________________________
# DETAIL VIEW

class SopInfraDetailView(generic.ObjectView):
    """
    detail view with changelog and journal
    """
    template_name: str = "sop_infra/sopinfra.html"
    queryset = SopInfra.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        context = super().get_extra_context(request, instance)
        if not instance:
            raise Http404(
            "No instance given."
        )
        context["infra"] = instance
        context["site"] = instance.site
        return context



# ____________________________
# LIST VIEWS

class SopInfraListView(generic.ObjectListView):
    """list of all SopInfra objects and instances"""

    queryset = SopInfra.objects.all()
    table = SopInfraTable
    filterset = SopInfraFilterset
    filterset_form = SopInfraFilterForm


class SopInfraRefreshView(View, SopInfraRefreshMixin, ObjectPermissionRequiredMixin):
    """
    refresh targeted sopinfra computed values
    """

    form = SopInfraRefreshForm
    template_name: str = "sop_infra/tools/refresh_form.html"

    def get(self, request, *args, **kwargs):

        # additional security
        if not request.user.has_perm(get_permission_for_model(SopInfra, "change")):
            return self.handle_no_permission()

        restrict_form_fields(self.form(), request.user)

        return render(
            request,
            self.template_name,
            {
                "form": self.form(),
                "return_url": reverse("plugins:sop_infra:sopinfra_list"),
            },
        )

    def post(self, request, *args, **kwargs):

        # additional security
        if not request.user.has_perm(get_permission_for_model(SopInfra, "change")):
            return self.handle_no_permission()

        return_url = reverse("plugins:sop_infra:sopinfra_list")
        form = self.form(data=request.POST, files=request.FILES)
        if form.is_valid():
            data: dict = form.cleaned_data
            return_url = data["return_url"]
            self.refresh_infra(data["infra"])
            return redirect(return_url)

        return render(
            request, self.template_name, {"form": self.form(), "return_url": return_url}
        )


class SopInfraRefreshNoForm(View, SopInfraRefreshMixin, ObjectPermissionRequiredMixin):

    def get_return_url(self, pk) -> str:

        return f"/dcim/sites/{pk}/infra/"

    def get(self, request, *args, **kwargs):

        # additional security
        if not request.user.has_perm(get_permission_for_model(SopInfra, "change")):
            return self.handle_no_permission()

        pk = request.GET.get("qs")
        self.refresh_infra(SopInfra.objects.filter(site__pk=pk))
        return redirect(self.get_return_url(pk))


# ____________________________
# bulk views


# class SopInfraBulkEditView(generic.BulkEditView):

#     queryset = SopInfra.objects.all()
# TODO should be a bulkeditform
#     form = SopInfraForm
#     table = SopInfraTable
#     # filterset = SopInfraFilterset
#     # filterset_form = SopInfraFilterForm


# class SopInfraBulkDeleteView(generic.BulkDeleteView):

#     queryset = SopInfra.objects.all()
#     table = SopInfraTable
#     # filterset = SopInfraFilterset
#     # filterset_form = SopInfraFilterForm

