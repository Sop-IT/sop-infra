import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib import messages
from django.conf import settings

from netbox.plugins import PluginTemplateExtension
from netbox.context import current_request
from dcim.models import Site, Device, DeviceType
from ipam.models import VLAN

from sop_infra.models import SopInfra
from sop_infra.models.infra import SopDeviceSetting
from sop_infra.models.sopmeraki import SopMerakiDash, SopMerakiDevice, SopMerakiUtils
from sop_infra.utils.netbox_utils import NetboxUtils


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
                return self.render("sop_infra/inc/refresh_btn.html", extra_context={})
        return ""


class NetboxDevicePluginExtension(PluginTemplateExtension):

    models = ['dcim.device']
    
    def right_page(self):
        if self.context.get("object"):
            if isinstance(self.context.get("object"), Device):
                return self.render("sop_infra/inc/cards/sopmerakinet_on_device.html", extra_context={})
        return ""
    
    def alerts(self):
        ret=""
        # TODO : INFO and ALERT MESSAGES
        return ret        


class SopMerakiDevicePluginExtension(PluginTemplateExtension):

    models = ['sop_infra.sopmerakidevice']
    
    def alerts(self):
        ret=""
        danger_messages:list[str]=NetboxUtils.get_device_compliance_alert_messages(self.context.get("object"))
        ret+=self.render("sop_infra/inc/alerts/danger.html", extra_context={"title": "CRITICAL ISSUES", "messages":danger_messages})
        warning_messages:list[str]=NetboxUtils.get_device_compliance_warning_messages(self.context.get("object"))
        ret+=self.render("sop_infra/inc/alerts/warning.html", extra_context={"title": "NON COMPLIANT DEVICE", "messages":warning_messages})
        # TODO : INFO  MESSAGES
        return ret          


class SopMerakiSwitchStackPluginExtension(PluginTemplateExtension):

    models = ['sop_infra.sopmerakiswitchstack']
    
    def alerts(self):
        ret=""
        danger_messages:list[str]=NetboxUtils.get_switch_stack_alert_messages(self.context.get("object"))
        ret+=self.render("sop_infra/inc/alerts/danger.html", extra_context={"title": "CRITICAL ISSUES", "messages":danger_messages})
        # TODO : INFO  MESSAGES
        return ret          


class NetboxSitePluginExtension(PluginTemplateExtension):

    models = ['dcim.site']
    
    def alerts(self):
        ret=""
        danger_messages:list[str]=NetboxUtils.get_site_compliance_danger_messages(self.context.get("object"))
        ret+=self.render("sop_infra/inc/alerts/danger.html", extra_context={"title": "CRITICAL ISSUES", "messages":danger_messages})
        warning_messages:list[str]=NetboxUtils.get_site_compliance_warning_messages(self.context.get("object"))
        ret+=self.render("sop_infra/inc/alerts/warning.html", extra_context={"title": "COMPLIANCE ISSUES", "messages":warning_messages})
        # TODO : INFO  MESSAGES
        return ret        


class NetboxVlanPluginExtension(PluginTemplateExtension):

    models = ['ipam.vlan']
    
    def alerts(self):
        ret=""
        warning_messages:list[str]=NetboxUtils.get_vlan_compliance_warning_messages(self.context.get("object"))
        ret+=self.render("sop_infra/inc/alerts/warning.html", extra_context={"title": "NON COMPLIANT VLAN", "messages":warning_messages})
        # TODO : INFO and ALERT MESSAGES
        return ret   


class NetboxPrefixPluginExtension(PluginTemplateExtension):

    models = ['ipam.prefix']
    
    def alerts(self):
        ret=""
        warning_messages:list[str]=NetboxUtils.get_prefix_compliance_warning_messages(self.context.get("object"))
        ret+=self.render("sop_infra/inc/alerts/warning.html", extra_context={"title": "NON COMPLIANT PREFIX", "messages":warning_messages})
        # TODO : INFO and ALERT MESSAGES
        return ret   


class NetboxVlanGroupPluginExtension(PluginTemplateExtension):

    models = ['ipam.vlangroup']
    
    def alerts(self):
        ret=""
        warning_messages:list[str]=NetboxUtils.get_vlan_group_compliance_warning_messages(self.context.get("object"))
        ret+=self.render("sop_infra/inc/alerts/warning.html", extra_context={"title": "NON COMPLIANT VLAN GROUP", "messages":warning_messages})
        # TODO : INFO and ALERT MESSAGES
        return ret   

class TrigramSearch(PluginTemplateExtension):
    
    def navbar(self):
        return self.render("sop_infra/inc/trisearch.html", extra_context={})


template_extensions = list()
template_extensions.append(RefreshBtnPluginExtension)
template_extensions.append(NetboxDevicePluginExtension)
template_extensions.append(SopMerakiDevicePluginExtension)
template_extensions.append(SopMerakiSwitchStackPluginExtension)
template_extensions.append(NetboxSitePluginExtension)
template_extensions.append(NetboxVlanPluginExtension)
template_extensions.append(NetboxPrefixPluginExtension)
template_extensions.append(NetboxVlanGroupPluginExtension)
template_extensions.append(TrigramSearch)  

