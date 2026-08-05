import json
from django.db import transaction
from django.http import Http404, HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.urls import reverse
from django.db.models import Count
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import ValidationError

from utilities.views import register_model_view, ViewTab
from utilities.permissions import get_permission_for_model
from utilities.forms import restrict_form_fields
from utilities.exceptions import AbortScript

from netbox.jobs import Job, JobStatusChoices
from netbox.views import generic

from dcim.models import DeviceRole, Location, MACAddress
from ipam.models import IPAddress, Role
from tenancy.models import Contact
from extras.models import Tag

from sop_infra.forms.infra import SopInfraHelperDhcpForm, SopMerakiClaimForm
from sop_infra.jobs import SopMerakiClaimDevicesToInfraJob, SopMerakiCreateNetworkJob, SopSyncAdUsers
from sop_infra.utils.meraki_utils import SopMerakiUtils
from sop_infra.utils.netbox_utils import SopInfraConstants
from sop_infra.forms import *
from sop_infra.tables import *
from sop_infra.models import *
from sop_infra.filtersets import *
from sop_infra.utils.sop_utils import  SopInfraRelatedModelsMixin
from sop_utils.strings import  StringUtils
from sop_utils.netbox import NetboxConstants, NetboxUtils

import netaddr

__all__ = (
    "SopDeviceSettingTryManageInNetbox",
    "SopInfraSiteTabView",
    "SopMerakiSiteTabView",
    # "SopInfraAddView",
    "SopInfraEditView",
    "SopInfraListView",
    "SopInfraDeleteView",
    "SopInfraDetailView",
    "SopInfraRefreshView",
    # "SopInfraRefreshNoForm",
    # "SopInfraBulkEditView",
    # "SopInfraBulkDeleteView",
    "SopInfraJsonExportsAdSites",
    "SopInfraJsonExportsAdUsers",
    "SopSwitchTemplateDetailView",
    "SopSwitchTemplateEditView",
    "SopSwitchTemplateDeleteView",
    "SopSwitchTemplateListView",
    "SopDeviceSettingDetailView",
    "SopDeviceSettingEditView",
)


class SopDeviceSettingTryManageInNetbox(View):
    """
    Try to change the device settings management to Netbox
    """

    def get(self, request, pk, *args, **kwargs):

        # TODO permissions
        # if not request.user.has_perm(get_permission_for_model(SopInfra, "change")):
        #    return self.handle_no_permission()

        # restrict_form_fields(self.form(), request.user)

        return_url = reverse("plugins:sop_infra:sopdevicesetting_detail", args=(pk,))
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        
        sdss = SopDeviceSetting.objects.filter(pk=pk)
        if not sdss.exists():
            messages.error(request, f"Cannot find SopDeviceSetting !")
            return redirect(return_url)
        
        sds:SopDeviceSetting=sdss[0]
               
        if sds.manage_in_netbox:
            messages.error(request, f"Device management already done via Netbox !")
            return redirect(return_url)            
        
        if sds.needs_fix_before_mgmt_switch:
            messages.error(request, f"Cannot enable the device management via Netbox !")
            return redirect(return_url)            

        if sds.enable_netbox_management():
            messages.success(request, f"Device management via Netbox enbaled !")
        else:
            messages.error(request, "Could not enable the device management via Netbox !")
            
        return redirect(return_url)        
        


class SopInfraSyncAdUsers(View):
    """
    Sync the users from AD
    """

    def get(self, request, *args, **kwargs):

        # TODO permissions
        # if not request.user.has_perm(get_permission_for_model(SopInfra, "change")):
        #    return self.handle_no_permission()

        # restrict_form_fields(self.form(), request.user)

        j: Job = SopSyncAdUsers.launch_manual()
        return redirect(reverse("core:job", args=[j.pk]))


class SopInfraJsonExportsAdUsers(View):

    def get(self, request: HttpRequest, *args, **kwargs):

        contsdict: dict[int, dict[str, int]] = dict()
        conts = (
            Contact.objects.filter(custom_field_data__ad_acct_disabled=False)
            .filter(custom_field_data__ad_site_id__gt=1)
            .values(
                "custom_field_data__ad_site_id",
                "custom_field_data__ad_site_name",
                "custom_field_data__ad_extAtt7",
            )
            .annotate(dcount=Count("custom_field_data__ad_site_id"))
            .order_by()
        )
        dc: dict[str, int]
        for v in conts.all():
            k = v.get("custom_field_data__ad_site_id")
            if k in contsdict.keys():
                dc = contsdict.get(k)
            else:
                dc = dict()
            collar = v.get("custom_field_data__ad_extAtt7")
            if collar in ["0", "1"]:
                dc[collar] = v.get("dcount")
                contsdict[k] = dc
        return JsonResponse(contsdict, safe=False)


class SopInfraJsonExportsAdSites(View):

    def get(self, request: HttpRequest, *args, **kwargs):

        # TODO : permettre de passer le status et le slug du role en arguments
        status: Q = Q(
            Q(status="active") | Q(status="noncompliant") | Q(status="decommissioning")
        )
        role: Q = Q(role__slug="usr")
        vrf: Q = Q(vrf_id=None)
        vlan: Q = ~Q(vlan_id=None)
        visible: Q = Q(custom_field_data__meraki_visible=True)
        scope_type: Q = Q(
            scope_type_id=NetboxConstants.get_ct_dcim_site().pk
        )
        vlan_role: Q = Q(vlan__role__slug="usr")
        pfs = Prefix.objects.filter(
            status, role, vlan, vrf, visible, scope_type, vlan_role
        )

        exp: list[dict[str, str]] = []
        for pf in pfs:
            d: dict[str, str] = dict()
            d["trigram"] = pf.scope.slug
            d["vlan_id"] = pf.vlan.vid
            d["prefix"] = f"{pf.prefix}"
            d["vlan_role"] = pf.vlan.role.slug
            d["tenant_group"] = pf.scope.tenant.group.slug
            exp.append(d)
        return JsonResponse(exp, safe=False)

# ===========================================================================================
#region SITE TABS

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
            raise Http404("No instance given.")
        context["site"] = instance
        if not instance.sopinfra:
            instance.sopinfra = SopInfra.objects.create(site=instance)
        context["infra"] = instance.sopinfra
        return context


@register_model_view(Site, name="sopmeraki")
class SopMerakiSiteTabView(SopInfraRelatedModelsMixin, generic.ObjectView):
    """
    creates a "SOP Meraki" tab on the site page
    """

    tab = ViewTab(
        label="SOP Meraki", permission=get_permission_for_model(SopInfra, "view")
    )
    template_name: str = "sop_infra/tab/sopmeraki_on_site.html"
    queryset = Site.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        context = super().get_extra_context(request, instance)
        if not instance:
            raise Http404("No instance given.")
        context["site"] = instance
        if not instance.sopinfra:
            instance.sopinfra = SopInfra.objects.create(site=instance)
        context["infra"] = instance.sopinfra
        return context





# ===========================================================================================
#region BASE MODEL VIEWS

# ____________________________
# SOP INFRA 


class SopInfraDeleteView(generic.ObjectDeleteView):
    """
    deletes an existing SopInfra instance
    """

    queryset = SopInfra.objects.all()


class SopInfraEditView(generic.ObjectEditView):
    """
    edits an existing SopInfra instance
    """

    queryset = SopInfra.objects.all()
    form = SopInfraForm

    # def get_return_url(self, request, obj):
    #     return_url=f"{base_url}?{normalize_queryset(infra.values_list('id', flat=True))}"
    #     if request.GET.get("return_url"):
    #         return_url=request.GET.get("return_url")

    #     if obj.site:
    #         return f"/dcim/sites/{obj.site.id}/infra"

    # def get_extra_context(self, request, obj):
    #     context = super().get_extra_context(request, obj)
    #     if not obj:
    #         return context
    #     context["object_type"] = obj
    #     return context


class SopInfraDetailView(generic.ObjectView):
    """
    detail view with changelog and journal
    """

    template_name: str = "sop_infra/sopinfra.html"
    queryset = SopInfra.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        context = super().get_extra_context(request, instance)
        if not instance:
            raise Http404("No instance given.")
        context["infra"] = instance
        context["site"] = instance.site
        return context


class SopInfraListView(generic.ObjectListView):
    """list of all SopInfra objects and instances"""

    queryset = SopInfra.objects.all()
    table = SopInfraTable
    filterset = SopInfraFilterset
    filterset_form = SopInfraFilterForm

    actions = {
        "export": {"view"},
    }


class SopMerakiEditView(generic.ObjectEditView):
    """
    edits an existing SopInfra instance
    """

    queryset = SopInfra.objects.all()
    form = SopMerakiForm

#endregion BASE MODEL VIEWS


# ======================================================================
#region SWITCH TEMPLATES MODEL VIEWS 


class SopSwitchTemplateDeleteView(generic.ObjectDeleteView):
    """
    deletes an existing SopSwitchTemplate instance
    """
    queryset = SopSwitchTemplate.objects.all()


class SopSwitchTemplateEditView(generic.ObjectEditView):
    """
    edits an existing SopSwitchTemplate instance
    """
    queryset = SopSwitchTemplate.objects.all()
    form = SopSwitchTemplateForm


class SopSwitchTemplateDetailView(generic.ObjectView):
    """
    detail view with changelog and journal
    """
    template_name: str = "sop_infra/sopswitchtemplate.html"
    queryset = SopSwitchTemplate.objects.all()
    def get_extra_context(self, request, instance) -> dict:
        context = super().get_extra_context(request, instance)
        if not instance:
            raise Http404("No instance given.")
        context["swtmpl"] = instance
        return context


class SopSwitchTemplateListView(generic.ObjectListView):
    """
    list of all SopSwitchTemplate objects and instances
    """
    queryset = SopSwitchTemplate.objects.all()
    table = SopSwitchTemplateTable
    filterset = SopSwitchTemplateFilterset
    filterset_form = SopSwitchTemplateFilterForm

#endregion SWITCH TEMPLATES MODEL VIEWS 




# ======================================================================
#region DEVICE SETTINGS MODEL VIEWS


class SopDeviceSettingDetailView(generic.ObjectView):
    """
    detail view with changelog and journal
    """
    template_name: str = "sop_infra/sopdevicesetting.html"
    queryset = SopDeviceSetting.objects.all()
    # def get_extra_context(self, request, instance) -> dict:
    #     context = super().get_extra_context(request, instance)
    #     table = DeviceTable( instance.devices.all() )
    #     if not instance:
    #         raise Http404("No instance given.")
    #     context["swtmpl"] = instance
    #     context["devs_table"] = table
    #     return context


class SopDeviceSettingEditView(generic.ObjectEditView):
    """
    edits an existing SopSwitchTemplate instance
    """
    queryset = SopDeviceSetting.objects.all()
    form = SopDeviceSettingForm


@register_model_view(Device, name="sopdevicesetting", detail=True)
class DeviceSopDeviceSettingTabViewOnDevice(generic.ObjectView):
    """
    creates a "sopdevicesetting" tab on the device page
    """

    tab = ViewTab(
        label="SOP Device Settings", permission=get_permission_for_model(SopDeviceSetting, "view")
    )
    template_name: str = "sop_infra/tab/sopdevicesetting_on_device.html"
    # On s'affiche sur un site
    queryset = Device.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        context = super().get_extra_context(request, instance)
        if not instance:
            raise Http404("No instance given.")
        context["device"] = instance
        try:
            context["sopdevicesetting"] = instance.sopdevicesetting
        except SopDeviceSetting.DoesNotExist:
            context["sopdevicesetting"] =  None
        return context


@register_model_view(SopMerakiDevice, name="sopdevicesetting", detail=True)
class DeviceSopDeviceSettingTabViewOnMerakiDevice(generic.ObjectView):
    """
    creates a "sopdevicesetting" tab on the SopMerakiDevice detail page
    """

    tab = ViewTab(
        label="SOP Device Settings", permission=get_permission_for_model(SopDeviceSetting, "view")
    )
    template_name: str = "sop_infra/tab/sopdevicesetting_on_meraki_device.html"
    # On s'affiche sur un site
    queryset = SopMerakiDevice.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        context = super().get_extra_context(request, instance)
        if not instance:
            raise Http404("No instance given.")
        nd:Device|None
        if not isinstance(instance, SopMerakiDevice):
            raise Exception(f"instance must be either a SopMerakiDevice instance")
        try:
            nd = instance.netbox_device
        except Device.DoesNotExist:
            nd =  None
        if nd is None:
            context["device"] = None
            context["sopdevicesetting"] =  None
        else :
            context["device"] = nd
            try:
                context["sopdevicesetting"] = nd.sopdevicesetting # type: ignore
            except SopDeviceSetting.DoesNotExist:
                context["sopdevicesetting"] =  None
        return context    
#endregion DEVICE SETTINGS MODEL VIEWS


# ======================================================================
#region ACTION VIEWS


class SopMerakiClaimDevicesView(AccessMixin, View):
    """
    Claim Meraki network devices into an Organisation's inventory
    """

    form = SopMerakiClaimForm
    template_name: str = "sop_infra/actions/sopinfra_claim_meraki_devices.html"

    def get(self, request, pk:int, *args, **kwargs):
        # Fetch SopInfra from URL and get it from db
        soi = get_object_or_404(SopInfra, pk=pk)
        if soi.site is None:
            raise AbortScript("SopInfra site cannot be None")
        # Check perms
        if not request.user.has_perm(get_permission_for_model(Site, "claim_devices"), obj=soi.site):
            return self.handle_no_permission()
        # Check form
        restrict_form_fields(self.form(), request.user)
        # Build or fetch return URL
        return_url:str
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        else:
            return_url = reverse("plugins:sop_infra:sopinfra_detail", args=(pk,))
        # Display form
        return render(
            request,
            self.template_name,
            {
                "form": self.form(),
                "return_url": return_url,
                "infra": soi,
                "claim_net_mx": soi.claim_net_mx if soi else None,
                "claim_net_mr": soi.claim_net_mr if soi else None,
                "merorg": SopMerakiUtils.get_site_meraki_org(soi.site),
            },
        )

    def post(self, request, pk:int, *args, **kwargs):
        # Fetch SopInfra from URL and get it from db
        soi = get_object_or_404(SopInfra, pk=pk)
        if soi.site is None:
            raise AbortScript("SopInfra site cannot be None")
        # Check perms
        if not request.user.has_perm(get_permission_for_model(Site, "claim_devices"), obj=soi.site):
            return self.handle_no_permission()
        # Build or fetch return URL
        return_url : str
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        else: 
            return_url = reverse("plugins:sop_infra:sopinfra_detail", args=(pk,))
        # Check and validate form data
        form = self.form(data=request.POST, files=request.FILES)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": self.form(),
                    "return_url": return_url,
                    "infra": soi,
                    "claim_net_mx": soi.claim_net_mx if soi else None,
                    "claim_net_mr": soi.claim_net_mr if soi else None,
                    "merorg": SopMerakiUtils.get_site_meraki_org(soi.site),
                },
            )
        # Extract form data
        data: dict = form.cleaned_data
        serials = data["serials_list"]
        # Run job and redirect according to return status
        j: Job = SopMerakiClaimDevicesToInfraJob.launch_interactive(request, True, soi, serials)
        url:str
        if j.status==JobStatusChoices.STATUS_COMPLETED:
            url= reverse("plugins:sop_infra:sopinfra_detail",  args=(pk,))
        else:
            url = reverse("core:job", args=[j.pk])
        return redirect(url)


class SopMerakiCreateNetworksView(AccessMixin, View):

    def get(self, request, pk, *args, **kwargs):
        # Check perms
        group_names = ["ALL_ITA_Netbox_Team_Integration", "ALL_ITA_Netbox_Team_Network"]
        if request.user.is_superuser:
            pass
        elif not request.user.groups.filter(name__in=group_names):
            return self.handle_no_permission()
        # Fetch site
        site = get_object_or_404(Site, pk=pk)
        # Fetch details param
        details: bool = request.GET["details"] == "True"
        # Launch job
        j: Job = SopMerakiCreateNetworkJob.launch_interactive(request, message=True, site=site, details=details)
        # Send to script result
        url = reverse("core:job", args=[j.pk])
        if details:
            url += "?log_threshold=debug"
        return redirect(url)



class SopInfraRefreshView(AccessMixin, View):
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

    def refresh_infra(self, queryset):
        instance: SopInfra
        for instance in queryset:
            # on snappe pour être sûrs
            instance.snapshot()
            if instance.calc_cumul_and_propagate():
                # si ça a changé, on déclenche le recalcul
                instance.full_clean()
                # Puis on sauve
                instance.save()
        try:
            request: HttpRequest = current_request.get()  # type: ignore
            messages.success(request, f"Successfully recomputed SopInfra sizing.")
        except:
            pass

#endregion ACTION VIEWS


# ======================================================================
#region HELPER VIEWS



class SopInfraHelperDhcpReader:

    def __init__(self, qdict, flavor_config):
        self.__qdict=qdict
        self.__read_method=self.__read_direct
        if flavor_config is not None :
            self.__flavor_config=flavor_config
            self.__read_method=self.__read_override

    def __read_direct(self, key):
        return self.__qdict.get(key)
    
    def __read_override(self, key):
        return self.__flavor_config.get(key) or self.__read_direct(key)
    
    def get(self, key):
        return self.__read_method(key)



class SopInfraHelperDhcp(AccessMixin, View):
    """
    create DHCP reservation
    """

    form = SopInfraHelperDhcpForm
    template_name: str = "sop_infra/tools/helper_dhcp.html"

    __flavor_configs= {
        "printer": {
            "forced_prefix_role_slug" : "usr",
            "forced_device_role_slug": "prt-printer", 
            "forced_device_type_slug" : "generic-printer",
        },
        "user": {
            "forced_prefix_role_slug" : "usr",
            "forced_device_role_slug": "0u-unknown-network-device", 
            "forced_device_role_slug" : "ukn-unknown",
        },
        "wms": {
            "forced_prefix_role_slug" : "wms",
            "forced_device_type_tag_slug" : "wms",
            "forced_device_role_tag_slug" : "wms", 
            "auto_tags": {
                    "Device" : ["wms", "rbac-wms", ],
                    "IPAddress" : ["wms", "rbac-wms", ],
                }
            },
        "std": {
            "forced_prefix_role_tag_slug" : "std",
        },
        "lan": {
            "forced_prefix_role_tag_slug" : "lan",
        },
        "manual": None,
    }

    @staticmethod
    def __data_from_qdict(query_dict) -> dict:

        return_url = query_dict.get("return_url") or reverse("home")
        
        flavor = query_dict.get("flavor")
        # TODO : passer ça en config du module
        if not flavor in SopInfraHelperDhcp.__flavor_configs.keys():
                raise Exception(f"Unknown flavor {flavor} !")
        flavor_config=SopInfraHelperDhcp.__flavor_configs.get(flavor)
        qdict = SopInfraHelperDhcpReader(query_dict, flavor_config)

        forced_site_id = qdict.get("forced_site_id")
        site_id = forced_site_id or qdict.get("site_id")

        # forced params override the others
        forced_prefix_role_id = qdict.get("forced_prefix_role_id")
        forced_prefix_role_slug = qdict.get("forced_prefix_role_slug")
        forced_prefix_role_tag_slug = qdict.get("forced_prefix_role_tag_slug")
        if forced_prefix_role_tag_slug and not forced_prefix_role_slug:
            query=Role.objects.filter(tags__slug=forced_prefix_role_tag_slug)
            if query.count()==1:
                forced_prefix_role_slug = query[0].slug
        if forced_prefix_role_slug and not forced_prefix_role_id:
            if Role.objects.filter(slug=forced_prefix_role_slug).exists():
                forced_prefix_role_id = Role.objects.get(slug=forced_prefix_role_slug).pk
        prefix_role_id = forced_prefix_role_id or qdict.get("prefix_role_id")

        forced_device_role_id = qdict.get("forced_device_role_id")
        forced_device_role_slug = qdict.get("forced_device_role_slug")
        forced_device_role_tag_slug = qdict.get("forced_device_role_tag_slug")
        if forced_device_role_tag_slug and not forced_device_role_slug:
            query=DeviceRole.objects.filter(tags__slug=forced_device_role_tag_slug)
            if query.count()==1:
                forced_device_role_slug = query[0].slug
        if forced_device_role_slug and not forced_device_role_id:
            if DeviceRole.objects.filter(slug=forced_device_role_slug).exists():
                forced_device_role_id = DeviceRole.objects.get(slug=forced_device_role_slug).pk
        device_role_id = forced_device_role_id or qdict.get("device_role_id")

        forced_device_type_id = qdict.get("forced_device_type_id")
        forced_device_type_slug = qdict.get("forced_device_type_slug")
        forced_device_type_tag_slug = qdict.get("forced_device_type_tag_slug")
        if forced_device_type_tag_slug and not forced_device_type_slug:
            query=DeviceRole.objects.filter(tags__slug=forced_device_type_tag_slug)
            if query.count()==1:
                forced_device_type_slug = query[0].slug
        if forced_device_type_slug and not forced_device_type_id:
            if DeviceType.objects.filter(slug=forced_device_type_slug).exists():
                forced_device_type_id = DeviceType.objects.get(slug=forced_device_type_slug).pk
        device_type_id = forced_device_type_id or qdict.get("device_type_id")

        device_name = qdict.get("device_name")
        initial_device_name = qdict.get("initial_device_name")
        device_dns = qdict.get("device_dns")
        ip_address = qdict.get("ip_address")
        mac_address = qdict.get("mac_address")


        # Apply the only prefix choice when there's only one
        forced_prefix_id = qdict.get("forced_prefix_id")
        if not forced_prefix_id :
            pfxs=Prefix.objects.filter(status__in=SopInfraConstants.active_prefixes_status)
            if site_id:
                pfxs=pfxs.filter(scope_type_id=NetboxConstants.get_ct_dcim_site(), scope_id=site_id)
            if prefix_role_id:
                pfxs=pfxs.filter(role_id=prefix_role_id)
            if pfxs.count()==1:
                forced_prefix_id=pfxs[0].pk
        prefix_id = forced_prefix_id or qdict.get("prefix_id")

        return {
            "return_url": return_url,
            "forced_site_id": forced_site_id,
            "site_id": site_id,
            "forced_prefix_role_id": forced_prefix_role_id,
            "forced_prefix_role_slug": forced_prefix_role_slug,
            "forced_prefix_role_tag_slug" : forced_prefix_role_tag_slug,
            "prefix_role_id": prefix_role_id,
            "forced_prefix_id": forced_prefix_id,
            "prefix_id" : prefix_id,
            "forced_device_role_id": forced_device_role_id,
            "forced_device_role_slug": forced_device_role_slug,
            "forced_device_role_tag_slug" : forced_device_role_tag_slug,
            "device_role_id" : device_role_id, 
            "forced_device_type_id": forced_device_type_id,
            "forced_device_type_slug": forced_device_type_slug,
            "forced_device_type_tag_slug" : forced_device_type_tag_slug,
            "device_type_id" : device_type_id, 
            "initial_device_name": initial_device_name,
            "device_name" : device_name or initial_device_name, 
            "device_dns" : device_dns, 
            "ip_address" : ip_address,
            "mac_address" : mac_address,
            "flavor": flavor,
        }

    def __lock_field(self, fld:forms.Field, help_text:str|None=None):
        fld.disabled=True
        fld.help_text=help_text or ("FORCED - "+fld.help_text)

    def __lock_fields(self, frm:forms.Form, data):
        # Site
        if data["forced_site_id"]:
            self.__lock_field(frm.fields["site_id"])
        # Role
        if data["forced_prefix_role_id"]:
            self.__lock_field(frm.fields["prefix_role_id"])            
        # Prefix
        if data["forced_prefix_id"]:
            self.__lock_field(frm.fields["prefix_id"])            
        # Device Role
        if data["forced_device_role_id"]:
            self.__lock_field(frm.fields["device_role_id"])            
        # Device Type
        if data["forced_device_type_id"]:
            self.__lock_field(frm.fields["device_type_id"])            
        # Flavor special processing
        flavor=data["flavor"]
        if "printer"==flavor:
            namefld:forms.RegexField=frm.fields["device_name"] # type: ignore
            namefld.regex=r"^PRT[^.]+$"
            namefld.initial='PRT'
            namefld.help_text+=" (must start with PRT for this flavor)"
            self.__lock_field(frm.fields["device_dns"], "AUTOMATIC")
        elif "wms"==flavor:
            self.__lock_field(frm.fields["device_dns"], "IGNORED")

    def get(self, request,  *args, **kwargs):
        # Extract params
        get_data=SopInfraHelperDhcp.__data_from_qdict(request.GET)
        # additional security
        if not request.user.has_perm(get_permission_for_model(Site, f"helper_dhcp_{get_data.get('flavor')}")):
            return self.handle_no_permission()
        # Build form
        frm=self.form(initial=get_data)
        # Lock fields
        self.__lock_fields(frm, get_data)
        # Apply limits to values
        restrict_form_fields(frm, request.user)
        # Render when all is fine
        return render(
            request,
            self.template_name,
            {
                "form": frm,
                "return_url": get_data["return_url"],
            },
        )

    def post(self, request, *args, **kwargs):
        # Extract params
        get_data = SopInfraHelperDhcp.__data_from_qdict(request.GET)
        # additional security
        if not request.user.has_perm(get_permission_for_model(Site, f"helper_dhcp_{get_data.get('flavor')}")):
            return self.handle_no_permission()
        # Build form from post
        form = self.form(initial=get_data, data=request.POST, files=request.FILES)
        # Lock fields
        self.__lock_fields(form, get_data)
        # Check form data
        return_url = request.GET.get("return_url") or reverse("home")
        if form.is_valid():           
            # fetch clean data
            data: dict = form.cleaned_data
            # recheck security with cleaned data
            if not request.user.has_perm(get_permission_for_model(Site, f"helper_dhcp_{get_data.get('flavor')}")):
                return self.handle_no_permission()
            # extract returl url
            return_url= data["return_url"]
            # Try create and return 
            try: 
                self._do_create_netbox(
                    data["device_type_id"],
                    data["device_name"],
                    data["device_dns"],
                    data["prefix_id"],
                    self._get_root_location(data["prefix_id"].scope),
                    "active",
                    data["device_role_id"],
                    self._check_or_allocate(data["prefix_id"], data["ip_address"]),
                    data["mac_address"],
                    f"SOPInfra / DHCP Helper - flavor={data["flavor"]} - used by {self.request.user.username}",
                    data["flavor"],
                )
                # ALL IS WELL ==> RETURN
                return redirect(data["return_url"])
            except ValidationError as e:
                for k,v in e.message_dict.items():
                    for m in v:
                        form.add_error(k, m)
            except AbortScript as e:
                messages.error(request, f"{e}")
            # except Exception as e:
            #     messages.error(request, f"Unknown error : {e}")
        # Either the form was invalid or something went wrong
        # Render the form with error messages
        return render(
            request, self.template_name, {"form": form, "return_url": return_url}
        )


    @staticmethod
    def get_flavor_tag(flavor:str, objtype:str)->list[Tag]|None:
        flavor_config = SopInfraHelperDhcp.__flavor_configs.get(flavor)
        if flavor_config is None:
            return None
        auto_tags = flavor_config.get("auto_tags")
        if auto_tags is None:
            return None
        slugs=auto_tags.get(objtype)
        if slugs is None:
            return None
        ret:list[Tag]=[]
        for x in slugs:
            y=NetboxUtils.get_tag_from_tag_slug(x)
            if y:
                ret.append(y)
        return ret        

    @transaction.atomic
    def _do_create_netbox(
        self,
        dtype: DeviceType,
        device_name: str,
        dns_name: str,
        pref: Prefix,
        loc: Location,
        obj_status: str,
        device_role: DeviceRole,
        new_ip_add: str,
        mac_add: str,
        changelog_msg: str,
        flavor: str,
    ):

        apply_tags : list[Tag]|None

        # try to create the device
        # TODO : reuse if it exists
        nd = Device(
            device_type=dtype,
            name=device_name,
            site=pref.scope,
            location=loc,
            tenant=pref.tenant,
            status=obj_status,
            role=device_role,
        )
        if changelog_msg:
            nd._changelog_message = changelog_msg
        nd.full_clean()
        nd.save()
        # We need a PK to apply tags
        apply_tags=self.get_flavor_tag(flavor, "Device")
        if apply_tags is not None:
            for tag in apply_tags:
                nd.tags.add(tag)
            nd.full_clean()
            nd.save()

        # compute assigned interface
        if nd.interfaces_count < 1:
            raise AbortScript("Newly created device has no interfaces !")
        nint = nd.vc_interfaces()[0]
        if changelog_msg:
            nint._changelog_message = changelog_msg
        nint.full_clean()
        nint.save()

        # Create MAC Address
        mac = MACAddress()
        mac.mac_address = mac_add
        mac.assigned_object = nint
        if changelog_msg:
            mac._changelog_message = changelog_msg
        mac.full_clean()
        mac.save()
        # We need a PK to apply tags
        apply_tags=self.get_flavor_tag(flavor, "MACAddress")
        if apply_tags is not None:
            for tag in apply_tags:
                mac.tags.add(tag)
            mac.full_clean()
            mac.save()

        # primary mac
        nint.primary_mac_address = mac
        nint.full_clean()
        nint.save()

        # allocate the IP
        adds = IPAddress.objects.filter(address=new_ip_add)
        ipadd: IPAddress = None
        if adds.exists():
            ipadd = adds[0]
            ipadd.snapshot()
        else:
            ipadd = IPAddress()
            ipadd.address = new_ip_add
            ipadd.description = f"created by {self.request.user.username}"
        ipadd.status = obj_status
        ipadd.tenant = pref.tenant
        ipadd.dns_name = dns_name
        ipadd.assigned_object = nint
        if changelog_msg:
            ipadd._changelog_message = changelog_msg
        ipadd.full_clean()
        ipadd.save()
        # We need a PK to apply tags
        apply_tags=self.get_flavor_tag(flavor, "IPAddress")
        if apply_tags is not None:
            for tag in apply_tags:
                ipadd.tags.add(tag)
        nd.primary_ip4 = ipadd
        nd.full_clean()
        nd.save()

        try:
            request: HttpRequest = current_request.get()  # type: ignore
            messages.success(request, f"Successfully created reservation : {nd.name} - {nint.name} - {ipadd.address}")
        except:
            pass

    def _get_root_location(self, site: Site) -> Location:
        # find the main location of the site
        loc = Location.objects.filter(site=site)
        if len(loc) < 1:
            raise AbortScript("No locs on this site !")
        loc = loc[0]
        while loc.parent is not None:
            loc = loc.parent
        return loc

    def _check_or_allocate(self, pref: Prefix, ip_address: str) -> str:
        # Check if we need to find a free IP in the pools
        if StringUtils.is_none_or_empty(ip_address):
            # check if we have a fixed IP range
            pools = pref.get_child_ranges().filter(role__slug="fix")
            if pools is None or len(pools) < 1:
                raise AbortScript(
                    "This IP Range has no fixed IP allocation pool.\nEither allocate a FIX range in this prefix or input an IP address manualy."
                )
            # Find the first free IP address in the first pool
            ipset: netaddr.IPSet|None = None
            for p in pools:
                ipset = p.get_available_ips()
                if ipset is None or len(ipset) == 0:
                    continue
            naddint = 0
            if ipset:
                print(f"Pool : {ipset.iter_cidrs()}")
                cid: netaddr.IPNetwork
                for cid in ipset.iter_cidrs():
                    naddint = cid.first
                    break
            if naddint == 0:
                raise AbortScript(
                    "No more available IPs in the fixed allocation pools !"
                )
            print(f"IPAdd : {netaddr.IPAddress(naddint)}")
            # self.log_debug(f'Pref : {pref}')
            ret: str = f"{netaddr.IPAddress(naddint)}/{pref.mask_length}"
        else:
            ipadd = netaddr.IPNetwork(f"{ip_address}/{pref.mask_length}")
            if ipadd != pref.prefix.cidr:
                raise AbortScript(
                    f"this IP ({ip_address}) is not in the target network {pref.prefix}"
                )
            ret = f"{ip_address}/{pref.mask_length}"
        return ret


#endregion HELPER VIEWS
