from django import template
from django.http import QueryDict
from django.urls import reverse
from sop_infra.models.infra import SopInfra
from utilities.exceptions import AbortRequest
from utilities.views import get_viewname

__all__ = (
    'sopinfra_claim_meraki_devices_button',
    'sopinfra_create_meraki_networks_button',
)

register = template.Library()

@register.inclusion_tag('sop_infra/sopinfra/buttons/claim_meraki_devices.html', takes_context=True)
def sopinfra_claim_meraki_devices_button(context):
    instance=context['object']  
    viewname = get_viewname(instance, 'claim_meraki_devices')
    url = reverse(viewname, kwargs={'pk': instance.pk}, query={'details':True, 'return_url':context['request'].get_full_path()})
    return {
        'url': url,
    }

@register.inclusion_tag('sop_infra/sopinfra/buttons/create_meraki_networks.html', takes_context=True)
def sopinfra_create_meraki_networks_button(context):
    instance=context['object']  
    viewname = get_viewname(instance, 'create_meraki_networks')
    url = reverse(viewname, kwargs={'pk': instance.pk}, query={'details':True, 'return_url':context['request'].get_full_path()})
    return {
        'url': url,
    }
