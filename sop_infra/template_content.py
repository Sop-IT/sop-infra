import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib import messages
from django.conf import settings

from netbox.plugins import PluginTemplateExtension
from netbox.context import current_request
from dcim.models import Site, Device, DeviceType

from sop_infra.models import SopInfra
from sop_infra.models.infra import SopDeviceSetting
from sop_infra.models.sopmeraki import SopMerakiDash, SopMerakiUtils


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



class SopInfraPluginExtension(PluginTemplateExtension):
    def list_buttons(self):
        if self.context.get("object"):
            if isinstance(self.context.get("object"), SopMerakiDash):
                return self.render("sop_infra/inc/refresh_dash.html", extra_context={})
            elif isinstance(self.context.get("object"), SopInfra):
                return self.render("sop_infra/inc/refresh_btn.html", extra_context={})
        return ""


class TrigramSearch(PluginTemplateExtension):
    def navbar(self):
        return self.render("sop_infra/inc/trisearch.html", extra_context={})


template_extensions = list()
template_extensions.append(SopInfraPluginExtension)
template_extensions.append(TrigramSearch)  # type: ignore
