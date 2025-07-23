from django import template
from django.urls import reverse
from utilities.views import get_viewname

__all__ = (
    'refresh_button',
)

register = template.Library()

@register.inclusion_tag('buttons/refresh.html')
def refresh_button(instance):
    viewname = get_viewname(instance, 'refresh')
    url = reverse(viewname, kwargs={'pk': instance.pk})

    return {
        'url': url,
    }
