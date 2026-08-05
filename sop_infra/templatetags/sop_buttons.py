from django import template
from django.urls import reverse
from utilities.views import get_viewname

__all__ = (
    'refresh_button',
    'update_connectivity_statuses_button',
)

register = template.Library()

@register.inclusion_tag('buttons/refresh.html')
def refresh_button(instance):
    # TODO : constantes
    viewname = get_viewname(instance, 'refresh')
    url = reverse(viewname, kwargs={'pk': instance.pk})
    return {
        'url': url,
    }

@register.inclusion_tag('buttons/update_connectivity_statuses.html')
def update_connectivity_statuses_button(instance):
    # TODO : constantes
    viewname = get_viewname(instance, 'update_connectivity_statuses')
    url = reverse(viewname, kwargs={'pk': instance.pk})
    return {
        'url': url,
    }
