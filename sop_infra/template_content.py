
from django.contrib import messages
from django.db.models.signals import post_save
from django.dispatch import receiver

from netbox.context import current_request
from netbox.plugins import PluginTemplateExtension

from dcim.models import Region, Site, Device, SiteGroup
from tenancy.models import Tenant, TenantGroup

from sop_infra.models import SopInfra
from sop_infra.utils.meraki_utils import SopMerakiUtils
from sop_infra.models.sopmeraki import SopMerakiDash
from sop_infra.utils.netbox_utils import SopInfraUtils


# AUTO CREATE SOPINFRA WHEN A SITE IS SAVED
@receiver(post_save, sender=Site)
def create_or_update_sopinfra(sender, instance, created, **kwargs):
    """
    when creating or updating a Site
    create or update its related SopInfra instance
    """
    request = current_request.get()
    target = SopInfra.objects.filter(site=instance)

    # create
    infra: SopInfra
    if created and not target.exists():
        infra = SopInfra.objects.create(site=instance)
        infra.full_clean()
        infra.snapshot()
        infra.save()
        try:
            messages.success(request, f"Created {infra}")
        except:
            pass
        return

    # update
    infra = target.first()
    infra.snapshot()
    infra.full_clean()
    infra.save()
    try:
        messages.success(request, f"Updated {infra}")
    except:
        pass


# AUTO CREATE SOPDEVICESETTING WHEN SOME DEVICES ARE SAVED
@receiver(post_save, sender=Device)
def create_or_update_sopdevicesetting(sender, instance, created, **kwargs):
    """
    when creating or updating a Device
    create or update its related SopDeviceSettings instance
    IIF it's a device that supports setting via this system
    """
    SopMerakiUtils.check_create_sopdevicesetting(instance)



class RefreshBtnPluginExtension(PluginTemplateExtension):

    models = ['sop_infra.sopmerakidash', 'sop_infra.sopinfra']

    def list_buttons(self):
        if self.context.get("object"):
            if isinstance(self.context.get("object"), SopMerakiDash):
                return self.render("sop_infra/inc/refresh_dash.html", extra_context={})
            elif isinstance(self.context.get("object"), SopInfra):
                return self.render("sop_infra/inc/refresh_infra.html", extra_context={})
        return ""

    
class RecomputeSizingPluginExtension(PluginTemplateExtension):

    models = ['sop_infra.sopinfra']

    def list_buttons(self):
        if self.context.get("object"):
            if isinstance(self.context.get("object"), SopInfra):
                return self.render("sop_infra/inc/recompute_sizing.html", extra_context={})
        return ""


class NetboxDevicePluginExtension(PluginTemplateExtension):

    models = ['dcim.device']
    
    def left_page(self):
        object = self.context.get("object")
        if object is None:
            return ''
        if not isinstance(object, Device):
            return ''
        dt=object.device_type
        if not "cisco"==dt.manufacturer.slug:
            return ''
        if not dt.model.lower().startswith("meraki "):
            return ''
        return self.render("sop_infra/inc/cards/sopmerakinet_on_device.html", extra_context={})
    
    def alerts(self):
        ret=""
        # TODO : INFO and ALERT MESSAGES
        return ret        


class NetboxContactPluginExtension(PluginTemplateExtension):

    models = ['tenancy.contact']
    
    def alerts(self):
        ret=""
        warning_messages:list[str]=SopInfraUtils.list_contact_compliance_issues(self.context.get("object"))
        ret+=self.render("sop_infra/inc/alerts/warning.html", extra_context={"title": "COMPLIANCE ISSUES", "messages":warning_messages})
        return ret        






class TrigramSearch(PluginTemplateExtension):
    
    def navbar(self):
        return self.render("sop_infra/inc/trisearch.html", extra_context={})





# ==========================================================
#region MERAKI PUSH 

class MerakiPushPluginExtension(PluginTemplateExtension):

    models = ['dcim.site','dcim.region', 'dcim.sitegroup']

    def buttons(self):
        from utilities.permissions import get_permission_for_model
        request=self.context.get("request")
        if request is None:
            return ""
        object=self.context.get("object")
        if object is None:
            return ""
        if isinstance(object, Site):
            if request.user.has_perm(get_permission_for_model(object, "helper_push_site")):
                return self.render("sop_infra/inc/pushconf_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_push_site"})
        if isinstance(object, Region):
            if request.user.has_perm(get_permission_for_model(object, "helper_push_region")):
                return self.render("sop_infra/inc/pushconf_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_push_region"})
        if isinstance(object, SiteGroup):
            if request.user.has_perm(get_permission_for_model(object, "helper_push_group")):
                return self.render("sop_infra/inc/pushconf_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_push_group"})
        return ""
    

class MerakiLinkUmbrellaPluginExtension(PluginTemplateExtension):

    models = ['dcim.region', 'dcim.sitegroup', 'tenancy.tenant', 'tenancy.tenantgroup']

    def buttons(self):
        from utilities.permissions import get_permission_for_model
        request=self.context.get("request")
        if request is None:
            return ""
        object=self.context.get("object")
        if object is None:
            return ""
        if isinstance(self.context.get("object"), Region):
            if request.user.has_perm(get_permission_for_model(object, "helper_link_umbrella")):
                return self.render("sop_infra/inc/sopmeraki_linkumb_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_umblink_region"})
        if isinstance(self.context.get("object"), Tenant):
            if request.user.has_perm(get_permission_for_model(object, "helper_link_umbrella")):
                return self.render("sop_infra/inc/sopmeraki_linkumb_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_umblink_tenant"})
        if isinstance(self.context.get("object"), SiteGroup):
            if request.user.has_perm(get_permission_for_model(object, "helper_link_umbrella")):
                return self.render("sop_infra/inc/sopmeraki_linkumb_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_umblink_sitegroup"})
        if isinstance(self.context.get("object"), TenantGroup):
            if request.user.has_perm(get_permission_for_model(object, "helper_link_umbrella")):
                return self.render("sop_infra/inc/sopmeraki_linkumb_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_umblink_tenantgroup"})
        return ""
    

class MerakiEnableUmbrellaPluginExtension(PluginTemplateExtension):

    models = ['dcim.region', 'dcim.sitegroup', 'tenancy.tenant', 'tenancy.tenantgroup' ]

    def buttons(self):
        from utilities.permissions import get_permission_for_model
        request=self.context.get("request")
        if request is None:
            return ""
        object=self.context.get("object")
        if object is None:
            return ""
        if isinstance(self.context.get("object"), Region):
            if request.user.has_perm(get_permission_for_model(object, "helper_enable_umbrella")):
                return self.render("sop_infra/inc/sopmeraki_enableumb_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_umbenable_region"})
        if isinstance(self.context.get("object"), Tenant):
            if request.user.has_perm(get_permission_for_model(object, "helper_enable_umbrella")):
                return self.render("sop_infra/inc/sopmeraki_enableumb_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_umbenable_tenant"})
        if isinstance(self.context.get("object"), SiteGroup):
            if request.user.has_perm(get_permission_for_model(object, "helper_enable_umbrella")):
                return self.render("sop_infra/inc/sopmeraki_enableumb_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_umbenable_sitegroup"})
        if isinstance(self.context.get("object"), TenantGroup):
            if request.user.has_perm(get_permission_for_model(object, "helper_enable_umbrella")):
                return self.render("sop_infra/inc/sopmeraki_enableumb_btn.html", extra_context={"post_url":"plugins:sop_infra:sopmeraki_umbenable_tenantgroup"})
        return ""   



#endregion

class DHCPHelperPluginExtension(PluginTemplateExtension):

    models = ['dcim.site']

    def buttons(self):
        if self.context.get("object"):
            if isinstance(self.context.get("object"), Site):
                return self.render("sop_infra/inc/helper_dhcp_btn.html", extra_context={})
        return ""


template_extensions = list()
template_extensions.append(RefreshBtnPluginExtension)
template_extensions.append(RecomputeSizingPluginExtension)
template_extensions.append(NetboxDevicePluginExtension)
template_extensions.append(NetboxContactPluginExtension)


template_extensions.append(TrigramSearch)  
template_extensions.append(DHCPHelperPluginExtension)  
template_extensions.append(MerakiPushPluginExtension)
template_extensions.append(MerakiLinkUmbrellaPluginExtension)
template_extensions.append(MerakiEnableUmbrellaPluginExtension)
