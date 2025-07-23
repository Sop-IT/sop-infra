from django import template

from sop_infra.utils.sop_utils import SopUtils

__all__ = (
    'can_refresh',
)

register = template.Library()



@register.filter()
def can_refresh(user, instance):
    return SopUtils.check_permission(user, instance, 'refresh')