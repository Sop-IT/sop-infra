from django.contrib import messages
from django.db.models import Count
from django.shortcuts import render, redirect
from django.views import View
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpRequest, JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import AccessMixin


from core.choices import JobStatusChoices
from sop_infra.forms.sopmeraki import SopMerakiDeviceMoveForm, SopMerakiOrgClaimForm
from sop_infra.utils.meraki_utils import SopMerakiOrgUtils
from sop_infra.utils.netbox_utils import SopInfraUtils
from sop_infra.utils.object_actions import MoveObject
from utilities.views import ConditionalLoginRequiredMixin, ObjectPermissionRequiredMixin, register_model_view
from utilities.permissions import get_permission_for_model
from utilities.forms import restrict_form_fields

from netbox.views import generic
from netbox.jobs import Job
from netbox.object_actions import BulkDelete, BulkEdit, CloneObject, DeleteObject, EditObject

from dcim.models import Region, Site, SiteGroup
from ipam.models import IPAddress, Prefix
from tenancy.models import Tenant, TenantGroup

from sop_infra.jobs import (
    SopMerakiClaimDevicesToInventoryJob,
    SopMerakiCreateNetworkJob,
    SopMerakiDashRefreshJob,
    SopMerakiDashUpdateConnectivyStatusesJob,
    SopMerakiEnableUmbrellaJob,
    SopMerakiLinkSiteToUmbrellaJob,
    SopMerakiMoveDevicesToNetwork,
    SopMerakiNetConnectivityStatusesJob,
    SopMerakiOrgRefreshJob,
    SopMerakiNetRefreshJob,
    SopMerakiOrgConnectivityStatusesJob,
    SopMerakiPushSiteJob,
)

from sop_utils.misc import SopUtils
from sop_infra.forms import SopMerakiDashForm, SopMerakiDashFilterForm, SopMerakiDashRefreshForm, SopMerakiOrgForm, SopMerakiOrgFilterForm, SopMerakiOrgRefreshChooseForm, SopMerakiNetForm, SopMerakiNetFilterForm, SopMerakiNetRefreshChooseForm, SopMerakiDeviceForm, SopMerakiDeviceFilterForm, SopMerakiSwitchStackForm, SopMerakiSwitchStackFilterForm
from sop_infra.tables import SopMerakiDashTable, SopMerakiOrgTable, SopMerakiNetTable, SopMerakiDeviceTable, SopMerakiSwitchStackTable
from sop_infra.models import SopMerakiDash, SopMerakiOrg, SopMerakiNet, SopMerakiDevice, SopMerakiSwitchStack
from sop_infra.filtersets import SopMerakiDashFilterSet, SopMerakiOrgFilterSet, SopMerakiNetFilterSet, SopMerakiDeviceFilterSet, SopMerakiSwitchStackFilterSet


class SiteHierarchicalTaskMixin():

    # TODO refactor out of here

    def get_sites_for_tenant(self, pk)->tuple[Tenant,list[Site]]:
        # Fetch region and build a site list
        tenant = get_object_or_404(Tenant, pk=pk)
        sites:list[Site]=[]
        sites.extend(Site.objects.filter(tenant_id=tenant.id).filter(sopinfra__master_site=None))
        if settings.DEBUG:
            print(f"tenant={tenant} / sites : {sites}")
        return tenant,sites
    
    def get_sites_for_tenantgroup(self, pk)->tuple[TenantGroup,list[Site]]:
        # Fetch region and build a site list
        group = get_object_or_404(TenantGroup, pk=pk)
        sites:list[Site]=[]
        sites.extend(Site.objects.filter(tenant_id__in=group.tenants.all()).filter(sopinfra__master_site=None))
        for tg in group.get_descendants():
            sites.extend(Site.objects.filter(tenant_id__in=tg.tenants.all()).filter(sopinfra__master_site=None))
        if settings.DEBUG:
            print(f"tenantgroup={group} / descendants={group.get_descendants()} / sites : {sites}")
        return group,sites
    
    def get_sites_for_sitegroup(self, pk)->tuple[SiteGroup,list[Site]]:
        # Fetch region and build a site list
        group = get_object_or_404(SiteGroup, pk=pk)
        sites:list[Site]=[]
        sites.extend(Site.objects.filter(group_id=group.id).filter(sopinfra__master_site=None))
        for sg in group.get_descendants():
            sites.extend(Site.objects.filter(group_id=sg.id).filter(sopinfra__master_site=None))
        if settings.DEBUG:
            print(f"sitegroup={group} / descendants={group.get_descendants()} / sites : {sites}")
        return group,sites
    
    def get_sites_for_region(self, pk)->tuple[Region,list[Site]]:
        # Fetch region and build a site list
        region = get_object_or_404(Region, pk=pk)
        sites:list[Site]=[]
        sites.extend(Site.objects.filter(region_id=region.id).filter(sopinfra__master_site=None))
        for reg in region.get_descendants():
            sites.extend(Site.objects.filter(region_id=reg.id).filter(sopinfra__master_site=None))
        if settings.DEBUG:
            print(f"region={region} / descendants={region.get_descendants()} / sites : {sites}")
        return region,sites
    


class SopMerakiJsonConnectivityStatusSite(View):
    """
    Returns json with site connectivy statuses for the site based on the management IP address
    """
    def get(self, request: HttpRequest, ip:str, *args, **kwargs):
        d: dict[str, str] = dict()
        try:
            exp: list[dict[str, str]] = []
            preflst=Prefix.objects.filter(vrf=None).filter(prefix__net_contains=f"{ip}/32").filter(_children=0)
            if preflst.count()==0:
                raise Exception(f"No leaf prefix found for this IP : {ip} !")
            if preflst.count()>1:
                raise Exception(f"We expected a single prefix for this IP : {ip}, got {preflst.count()} !")
            pref:Prefix=preflst[0]
            vpn_modes=["spoke","hub"]
            smnlst=pref.scope.meraki_nets.filter(vpn_mode__in=vpn_modes).filter(exp_subnets_count__gt=0)
            if smnlst.count()==0:
                raise Exception(f"No Meraki network is announcing this IP : {ip} !")
            if smnlst.count()>1:
                raise Exception(f"We expected a single announcing SopMerakiNet for this IP : {ip}, got {smnlst.count()} !")
            smn:SopMerakiNet=smnlst[0]
            d["net_name"] = smn.nom
            d["net_appliance_status"] = smn.appliance_status
            d["last_statuses_change"] = smn.last_stats_change
            d["mx1wan1ip"] = smn.primary_mx.wan1ip if smn.primary_mx else "none"
            d["mx1wan2ip"] = smn.primary_mx.wan2ip if smn.primary_mx else "none"
            d["mx1wan1status"] = smn.primary_mx.wan1status if smn.primary_mx else "none"
            d["mx1wan2status"] = smn.primary_mx.wan2status if smn.primary_mx else "none"
            d["mx2wan1ip"] = smn.secondary_mx.wan1ip if smn.secondary_mx else "none"
            d["mx2wan2ip"] = smn.secondary_mx.wan2ip if smn.secondary_mx else "none"
            d["mx2wan1status"] = smn.secondary_mx.wan1status if smn.secondary_mx else "none"
            d["mx2wan2status"] = smn.secondary_mx.wan2status if smn.secondary_mx else "none"
        except Exception as e:
            d["exception"]=f"{type(e).__name__}: {e}"
        return JsonResponse(d, safe=False)
    

# ========================================================================
#region MERAKI PUSH VIEWS



class SopMerakiPushGroupView(SiteHierarchicalTaskMixin, View):
    """
    Push Meraki configurations for a whole sitegroup
    """
    def post(self, request, pk, *args, **kwargs):
        # check perms
        if not request.user.has_perm(get_permission_for_model(SiteGroup, "helper_push_group")):
            return self.handle_no_permission()
        # return url when done
        return_url = "/dcim/site-groups"
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Calc sites
        group,sites = self.get_sites_for_sitegroup(pk)
        # Let's queue updates
        messages.info(request, f"Starting to queue Umbrella site linking jobs for site group {group} : {sites}")
        for site in sites:
                j: Job = SopMerakiPushSiteJob.launch_background(request, message=False, site=site, details=True, simulate=settings.DEBUG)
                print(f"Queued UpdateOneSite for site [{site.name}]({site.get_absolute_url()}) : [{j.pk}]({j.get_absolute_url()})")
        # report and return
        messages.success(request, f"Queued {len(sites)} site config pushes for site group {group}")
        return redirect(return_url)


class SopMerakiPushRegionView(SiteHierarchicalTaskMixin, View):
    """
    Push Meraki configurations for a whole region
    """
    def post(self, request, pk, *args, **kwargs):
        # check perms
        if not request.user.has_perm(get_permission_for_model(Region, "helper_push_region")):
            return self.handle_no_permission()
        # return url when done
        return_url = "/dcim/regions"
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Calc sites
        region,sites = self.get_sites_for_region(pk)
        # Let's queue updates
        messages.info(request, f"Starting to queue Umbrella site linking jobs for region {region} : {sites}")
        for site in sites:
                j: Job = SopMerakiPushSiteJob.launch_background(request, message=False, site=site, details=True, simulate=settings.DEBUG)
                print(f"Queued UpdateOneSite for site [{site.name}]({site.get_absolute_url()}) : [{j.pk}]({j.get_absolute_url()})")
        # report and return
        messages.success(request, f"Queued {len(sites)} site pushes for region {region}")
        return redirect(return_url)
    
    
class SopMerakiPushSiteView(View):

    """
    Push Meraki configurations
    """

    # POST is blocking -> avoids to have several times the same job running
    # But we need to be able to test and override some params for easier debugging/testing
    def get(self, request, pk, *args, **kwargs):
        # This is only allowed in debug mode
        if not settings.DEBUG:
            return self.handle_no_permission()
        # pk needs to be passed in the querystring
        #pk: str|None = request.GET.get("pk")
        # then we can exec the POST logic
        return self.post(request, pk, *args, *kwargs)

    def post(self, request, pk, *args, **kwargs):
        # Fetch site
        instance = get_object_or_404(Site, pk=pk)
        # Check perms
        if not SopUtils.check_permission(request.user, instance, "helper_push_site"):
            return self.handle_no_permission()
        # Simulate ?
        simulate:bool=False
        if settings.DEBUG:
            simulate=("yes"==request.GET.get("simulate"))
        # Launch job
        j: Job = SopMerakiPushSiteJob.launch_interactive(request, message=True, site=instance, details=True, simulate=simulate)
        # Send to return url or script result
        url = request.GET.get("return_url") or reverse("core:job", args=[j.pk])
        return redirect(url)
    

#endregion




# ========================================================================
#region MERAKI UMBRELLA

    

class SopMerakiLinkUmbrellaTenantView(SiteHierarchicalTaskMixin, View):
    """
    Link an Umbrella dashboard to Meraki Networks for a whole Tenant
    """
    def post(self, request, pk, *args, **kwargs):
        # check perms
        if not request.user.has_perm(get_permission_for_model(Tenant, "helper_link_umbrella")):
            return self.handle_no_permission()
        # return url when done
        return_url = f"/tenancy/tenants"
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Calc sites
        tenant,sites = self.get_sites_for_tenant(pk)
        # Let's queue updates
        messages.info(request, f"Starting to queue Umbrella site linking jobs for tenant {tenant} : {sites}")
        for site in sites:
            j: Job = SopMerakiLinkSiteToUmbrellaJob.launch_background(request, message=False, site=site, details=True)
            print(f"Queued SopMerakiLinkSiteToUmbrellaJob for site [{site.name}]({site.get_absolute_url()}) : [{j.pk}]({j.get_absolute_url()})")
        # report and return
        messages.success(request, f"Queued {len(sites)} Umbrella site linking jobs for tenant {tenant}")
        return redirect(return_url)


class SopMerakiLinkUmbrellaTenantGroupView(SiteHierarchicalTaskMixin, View):
    """
    Link an Umbrella dashboard to Meraki Networks for a whole TenantGroup
    """
    def post(self, request, pk, *args, **kwargs):
        # check perms
        if not request.user.has_perm(get_permission_for_model(TenantGroup, "helper_link_umbrella")):
            return self.handle_no_permission()
        # return url when done
        return_url = f"/tenancy/tenant-groups"
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Calc sites
        group,sites = self.get_sites_for_tenantgroup(pk)
        # Let's queue updates
        messages.info(request, f"Starting to queue Umbrella site linking jobs for tenant group {group} : {sites}")
        for site in sites:
            j: Job = SopMerakiLinkSiteToUmbrellaJob.launch_background(request, message=False, site=site, details=True)
            print(f"Queued SopMerakiLinkSiteToUmbrellaJob for site [{site.name}]({site.get_absolute_url()}) : [{j.pk}]({j.get_absolute_url()})")
        # report and return
        messages.success(request, f"Queued {len(sites)} Umbrella site linking jobs for tenant group {group}")
        return redirect(return_url)
    

class SopMerakiLinkUmbrellaSiteGroupView(SiteHierarchicalTaskMixin, View):
    """
    Link an Umbrella dashboard to Meraki Networks for a whole SiteGroup
    """
    def post(self, request, pk, *args, **kwargs):
        # check perms
        if not request.user.has_perm(get_permission_for_model(SiteGroup, "helper_link_umbrella")):
            return self.handle_no_permission()
        # return url when done
        return_url = "/dcim/site-groups"
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Calc sites
        group,sites = self.get_sites_for_sitegroup(pk)
        # Let's queue updates
        messages.info(request, f"Starting to queue Umbrella site linking jobs for site group {group} : {sites}")
        for site in sites:
            j: Job = SopMerakiLinkSiteToUmbrellaJob.launch_background(request, message=False, site=site, details=True)
            print(f"Queued SopMerakiLinkSiteToUmbrellaJob for site [{site.name}]({site.get_absolute_url()}) : [{j.pk}]({j.get_absolute_url()})")
        # report and return
        messages.success(request, f"Queued {len(sites)} Umbrella site linking jobs for site group {group}")
        return redirect(return_url)


class SopMerakiLinkUmbrellaRegionView(SiteHierarchicalTaskMixin, View):
    """
    Link an Umbrella dashboard to Meraki Networks for a whole region
    """
    def post(self, request, pk, *args, **kwargs):
        # check perms
        if not request.user.has_perm(get_permission_for_model(Region, "helper_link_umbrella")):
            return self.handle_no_permission()
        # return url when done
        return_url = "/dcim/regions"
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Calc sites
        region,sites = self.get_sites_for_region(pk)
        # Let's queue updates
        messages.info(request, f"Starting to queue Umbrella site linking jobs for region {region} : {sites}")
        for site in sites:
            j: Job = SopMerakiLinkSiteToUmbrellaJob.launch_background(request, message=False, site=site, details=True)
            print(f"Queued SopMerakiLinkSiteToUmbrellaJob for site [{site.name}]({site.get_absolute_url()}) : [{j.pk}]({j.get_absolute_url()})")
        # report and return
        messages.success(request, f"Queued {len(sites)} Umbrella site linking jobs for region {region}")
        return redirect(return_url)


class SopMerakiLinkUmbrellaSiteView(View):
    """
    Link an Umbrella dashboard to Meraki Networks for a Site
    """
    def post(self, request, pk, *args, **kwargs):
        # Fetch site
        instance = get_object_or_404(Site, pk=pk)
        # Check perms
        if not SopUtils.check_permission(request.user, instance, "helper_link_umbrella"):
            return self.handle_no_permission()
        # Launch job
        j: Job = SopMerakiLinkSiteToUmbrellaJob.launch_interactive(request, message=True, site=instance, details=True)
        # Send to return url or script result
        url = request.GET.get("return_url") or reverse("core:job", args=[j.pk])
        return redirect(url)


class SopMerakiEnableUmbrellaTenantView(SiteHierarchicalTaskMixin, View):
    """
    Enable Umbrella protection for Meraki Networks for a whole Tenant
    """
    def post(self, request, pk, *args, **kwargs):
        # check perms
        if not request.user.has_perm(get_permission_for_model(Tenant, "helper_enable_umbrella")):
            return self.handle_no_permission()
        # return url when done
        return_url = "/tenancy/tenants"
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Calc sites
        tenant,sites = self.get_sites_for_tenant(pk)
        # Let's queue updates
        messages.info(request, f"Starting to queue Umbrella protection enable jobs for tenant {tenant} ({len(sites)} sites)")
        for site in sites:
            j: Job = SopMerakiEnableUmbrellaJob.launch_background(request, message=False, site=site, details=True)
            print(f"Queued SopMerakiEnableUmbrellaJob for site [{site.name}]({site.get_absolute_url()}) : [{j.pk}]({j.get_absolute_url()})")
        # report and return
        messages.success(request, f"Queued {len(sites)} Umbrella protection enable jobs for tenant {tenant}")
        return redirect(return_url)
    

class SopMerakiEnableUmbrellaTenantGroupView(SiteHierarchicalTaskMixin, View):
    """
    Enable Umbrella protection for Meraki Networks for a whole TenantGroup
    """
    def post(self, request, pk, *args, **kwargs):
        # check perms
        if not request.user.has_perm(get_permission_for_model(TenantGroup, "helper_enable_umbrella")):
            return self.handle_no_permission()
        # return url when done
        return_url = "/tenancy/tenant-groups"
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Calc sites
        group,sites = self.get_sites_for_tenantgroup(pk)
        # Let's queue updates
        messages.info(request, f"Starting to queue Umbrella protection enable jobs for tenant group {group} ({len(sites)} sites)")
        for site in sites:
            j: Job = SopMerakiEnableUmbrellaJob.launch_background(request, message=False, site=site, details=True)
            print(f"Queued SopMerakiEnableUmbrellaJob for site [{site.name}]({site.get_absolute_url()}) : [{j.pk}]({j.get_absolute_url()})")
        # report and return
        messages.success(request, f"Queued {len(sites)} Umbrella protection enable jobs for tenant group {group}")
        return redirect(return_url)


class SopMerakiEnableUmbrellaSiteGroupView(SiteHierarchicalTaskMixin, View):
    """
    Enable Umbrella protection for Meraki Networks for a whole SiteGroup
    """
    def post(self, request, pk, *args, **kwargs):
        # check perms
        if not request.user.has_perm(get_permission_for_model(SiteGroup, "helper_enable_umbrella")):
            return self.handle_no_permission()
        # return url when done
        return_url = "/dcim/site-groups"
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Calc sites
        group,sites = self.get_sites_for_sitegroup(pk)
        # Let's queue updates
        messages.info(request, f"Starting to queue Umbrella protection enable jobs for site group {group} ({len(sites)} sites)")
        for site in sites:
            j: Job = SopMerakiEnableUmbrellaJob.launch_background(request, message=False, site=site, details=True)
            print(f"Queued SopMerakiEnableUmbrellaJob for site [{site.name}]({site.get_absolute_url()}) : [{j.pk}]({j.get_absolute_url()})")
        # report and return
        messages.success(request, f"Queued {len(sites)} Umbrella protection enable jobs for site group {group}")
        return redirect(return_url)


class SopMerakiEnableUmbrellaRegionView(SiteHierarchicalTaskMixin, View):
    """
    Enable Umbrella protection for Meraki Networks for a whole region
    """
    def post(self, request, pk, *args, **kwargs):
        # check perms
        if not request.user.has_perm(get_permission_for_model(Region, "helper_enable_umbrella")):
            return self.handle_no_permission()
        # return url when done
        return_url = "/dcim/regions"
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Calc sites
        region,sites = self.get_sites_for_region(pk)
        # Let's queue updates
        messages.info(request, f"Starting to queue Umbrella protection enable jobs for region {region} ({len(sites)} sites)")
        for site in sites:
            j: Job = SopMerakiEnableUmbrellaJob.launch_background(request, message=False, site=site, details=True)
            print(f"Queued SopMerakiEnableUmbrellaJob for site [{site.name}]({site.get_absolute_url()}) : [{j.pk}]({j.get_absolute_url()})")
        # report and return
        messages.success(request, f"Queued {len(sites)} Umbrella protection enable jobs for region {region}")
        return redirect(return_url)


class SopMerakiEnableUmbrellaSiteView(View):
    """
    Enable Umbrella protection for Meraki Networks for a Site
    """
    def post(self, request, pk, *args, **kwargs):
        # Fetch site
        instance = get_object_or_404(Site, pk=pk)
        # Check perms
        if not SopUtils.check_permission(request.user, instance, "helper_enable_umbrella"):
            return self.handle_no_permission()
        # Launch job
        j: Job = SopMerakiEnableUmbrellaJob.launch_interactive(request, message=True, site=instance, details=True)
        # Send to return url or script result
        url = request.GET.get("return_url") or reverse("core:job", args=[j.pk])
        return redirect(url)



#endregion

# ========================================================================


class SopMerakiTriSearchView(View):
    
    """
    Send to the site or to the filtered site search page
    """

    def get(self, request: HttpRequest, *args, **kwargs):

        tri: str|None = request.GET.get("q")
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
#region SopMerakiDash


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
    # TODOPERM
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
            url = reverse("core:job", args=[j.pk])
            return redirect(url)


class SopMerakiDashRefreshView(View, ObjectPermissionRequiredMixin):
    # TODOPERM
    def post(self, request, pk, *args, **kwargs):

        instance = get_object_or_404(SopMerakiDash, pk=pk)

        if not SopUtils.check_permission(request.user, instance, "refresh"):
            return self.handle_no_permission()

        # Launch job
        j: Job = SopMerakiDashRefreshJob.launch_manual(dashs=[instance], details=False)

        # Send to script result
        url = reverse("core:job", args=[j.pk])
        return redirect(url)


class SopMerakiDashConnectivityStatusesView(View, ObjectPermissionRequiredMixin):
    # TODOPERM
    def post(self, request, pk, *args, **kwargs):

        instance = get_object_or_404(SopMerakiDash, pk=pk)

        if not SopUtils.check_permission(request.user, instance, "update_connectivity_statuses"):
            return self.handle_no_permission()

        # Launch job
        j: Job = SopMerakiDashUpdateConnectivyStatusesJob.launch_manual(dashs=[instance], details=False)

        # Send to script result
        url = reverse("core:job", args=[j.pk])
        return redirect(url)


#endregion

# ========================================================================
#region SopMerakiOrg


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
            url = reverse("core:job", args=[j.pk])

            return redirect(url)


class SopMerakiOrgRefreshView(AccessMixin, View):

    def post(self, request, pk, *args, **kwargs):

        instance = get_object_or_404(SopMerakiOrg, pk=pk)

        if not SopUtils.check_permission(request.user, instance, "refresh"):
            return self.handle_no_permission()

        # Launch job
        j: Job = SopMerakiOrgRefreshJob.launch_manual(orgs=[instance], details=False)

        # Send to script result
        url = reverse("core:job", args=[j.pk])
        return redirect(url)


class SopMerakiOrgUpdateConnectivityStatusesView(AccessMixin, View):

    def post(self, request, pk, *args, **kwargs):

        instance = get_object_or_404(SopMerakiOrg, pk=pk)

        if not SopUtils.check_permission(request.user, instance, "update_connectivity_statuses"):
            return self.handle_no_permission()

        # Launch job
        j: Job = SopMerakiOrgConnectivityStatusesJob.launch_manual(orgs=[instance], details=False)

        # Send to script result
        url = reverse("core:job", args=[j.pk])
        return redirect(url)


class SopMerakiOrgClaimView(AccessMixin, View):
    """
    Claim Meraki network devices into an Organisation's inventory
    """

    form = SopMerakiOrgClaimForm
    template_name: str = "sop_infra/actions/sopmerakiorg_claim_devices.html"

    def get(self, request, pk:int, *args, **kwargs):
        # Fetch SopmerakiOrg from URL and get it from db
        smo = get_object_or_404(SopMerakiOrg, pk=pk)
        # Check perms
        if not request.user.has_perm(get_permission_for_model(SopMerakiOrg, "claim_meraki_devices"), obj=smo):
            return self.handle_no_permission()
        # Check form
        restrict_form_fields(self.form(), request.user)
        # Build or fetch return URL
        return_url:str
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        else:
            return_url = reverse("plugins:sop_infra:sopmerakiorg_detail", args=(pk,))
        # Display form
        return render(
            request,
            self.template_name,
            {
                "form": self.form(),
                "return_url": return_url,
            },
        )

    def post(self, request, pk:int, *args, **kwargs):
        # Fetch SopmerakiOrg from URL and get it from db
        smo = get_object_or_404(SopMerakiOrg, pk=pk)
        # Check perms
        if not request.user.has_perm(get_permission_for_model(SopMerakiOrg, "claim_meraki_devices"), obj=smo):
            return self.handle_no_permission()
        # Build or fetch return URL
        return_url : str
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        else: 
            return_url = reverse("plugins:sop_infra:sopmerakiorg_detail", args=(pk,))
        # Check and validate form data
        form = self.form(data=request.POST, files=request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "return_url": return_url})
        # Extract form data
        data: dict = form.cleaned_data
        serials = data["serials_list"]
        # Run job and redirect according to return status
        j: Job = SopMerakiClaimDevicesToInventoryJob.launch_interactive(request, True, smo, serials)
        url:str
        if j.status==JobStatusChoices.STATUS_COMPLETED:
            url= reverse("plugins:sop_infra:sopmerakidevice_list", query={"serial":j.data})
        else:
            url = reverse("core:job", args=[j.pk])
        return redirect(url)

#endregion


# ============================================================================================================================
#region SopMerakiNet


@register_model_view(SopMerakiNet)
class SopMerakiNetView(generic.ObjectView):
    queryset = SopMerakiNet.objects.all().annotate(
        devs_count=Count("devices", distinct=True)
    )



@register_model_view(SopMerakiNet, 'list', path='', detail=False)
class SopMerakiNetListView(generic.ObjectListView):
    queryset = SopMerakiNet.objects.all().annotate(
        devs_count=Count("devices", distinct=True)
    )
    table = SopMerakiNetTable
    filterset = SopMerakiNetFilterSet
    filterset_form = SopMerakiNetFilterForm



@register_model_view(SopMerakiNet, 'add', detail=False)
@register_model_view(SopMerakiNet, 'edit')
class SopMerakiNetEditView(generic.ObjectEditView):
    queryset = SopMerakiNet.objects.all()
    form = SopMerakiNetForm



@register_model_view(SopMerakiNet, 'delete')
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
            url = reverse("core:job", args=[j.pk])
            return redirect(url)
        


@register_model_view(SopMerakiNet, 'refresh')
class SopMerakiNetRefreshView(AccessMixin, View):

    def post(self, request, pk, *args, **kwargs):

        instance = get_object_or_404(SopMerakiNet, pk=pk)

        if not SopUtils.check_permission(request.user, instance, "refresh"):
            return self.handle_no_permission()

        # Launch job
        j: Job = SopMerakiNetRefreshJob.launch_manual(nets=[instance], details=False)

        # Send to script result
        url = reverse("core:job", args=[j.pk])
        return redirect(url)
    


class SopMerakiNetUpdateConnectivityStatusesView(AccessMixin, View):

    def post(self, request, pk, *args, **kwargs):

        instance = get_object_or_404(SopMerakiNet, pk=pk)

        if not SopUtils.check_permission(request.user, instance, "update_connectivity_statuses"):
            return self.handle_no_permission()

        # Launch job
        j: Job = SopMerakiNetConnectivityStatusesJob.launch_manual(nets=[instance], details=False)

        # Send to script result
        url = reverse("core:job", args=[j.pk])
        return redirect(url)

#endregion











# ============================================================================================================================
#region SopMerakiSwitchStack

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
#endregion















# ============================================================================================================================
#region SopMerakiDevice


@register_model_view(SopMerakiDevice)
class SopMerakiDeviceView(generic.ObjectView):
    actions = [MoveObject]
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



@register_model_view(SopMerakiDevice, 'move')
class SopMerakiDeviceMoveView(ConditionalLoginRequiredMixin, View):

    form = SopMerakiDeviceMoveForm
    template_name: str = "sop_infra/sopinfra/actions/sopmerakidevice_move.html"

    def get(self, request, pk, *args, **kwargs):
        # Fetch from DB
        instance = get_object_or_404(SopMerakiDevice, pk=pk)
        # Check perms
        # - can move the device
        if not SopUtils.check_permission(request.user, instance, "move"):
            raise PermissionDenied(f"You do not have 'move' permission on this device ({instance}) !")
        # - can move on source network
        if instance.meraki_network is not None and not SopUtils.check_permission(request.user, instance.meraki_network, "move"):
            raise PermissionDenied(f"You do not have 'move' permission on the source network {instance.meraki_network} !")
        # Build or fetch return URL
        return_url : str = request.get_full_path()
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        # Prepare form (give ptype to filter possible networks)
        frm=self.form(initial={"ptype":instance.ptype})
        fld=frm.fields.get("destination")
        fld.help_text=f"Filtered by product_type={instance.ptype}"
        fld.widget.add_query_params({"ptypes__icontains": instance.ptype})
        # Filter out networks where the user has move rights 
        #restrict_form_fields(frm, request.user, "move")
        # render
        return render(
            request,
            self.template_name,
            {
                "form": frm,
                "return_url": return_url,
            },
        )


    def post(self, request, pk, *args, **kwargs):
        # Fetch from DB
        instance = get_object_or_404(SopMerakiDevice, pk=pk)
        # Check perms
        # - can move the device
        if not SopUtils.check_permission(request.user, instance, "move"):
            raise PermissionDenied(f"You do not have 'move' permission on this device ({instance}) !")
        # - can move on source network
        if instance.meraki_network is not None and not SopUtils.check_permission(request.user, instance.meraki_network, "move"):
            raise PermissionDenied(f"You do not have 'move' permission on the source network {instance.meraki_network} !")
        # Build or fetch return URL
        return_url : str
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")
        else: 
            return_url = request.get_full_path()
        # Check and validate form data
        form = self.form(data=request.POST, files=request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "return_url": return_url})
        # Extract form data
        data: dict = form.cleaned_data
        destination:SopMerakiNet = data["destination"]
        force:bool=data["force"]
        # Check perms
        # - can move to destination network
        if destination is not None and not SopUtils.check_permission(request.user, destination, "move"):
            raise PermissionDenied(f"You do not have 'move' permission on the destination network {destination} !")
        # Run job and redirect according to return status
        j: Job = SopMerakiMoveDevicesToNetwork.launch_interactive(request, True, [instance], destination, force)
        url:str
        if j.status==JobStatusChoices.STATUS_COMPLETED:
            url= return_url
        else:
            url = reverse("core:job", args=[j.pk])
        return redirect(url)



#endregion