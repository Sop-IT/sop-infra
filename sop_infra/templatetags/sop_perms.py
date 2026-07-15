from django import template

from sop_utils.misc import SopUtils

__all__ = (
    'can_refresh',
    'can_vpnstatuses',
)

register = template.Library()



@register.filter()
def can_refresh(user, instance):
    return SopUtils.check_permission(user, instance, 'refresh')

@register.filter()
def can_vpnstatuses(user, instance):
    return SopUtils.check_permission(user, instance, 'vpnstatuses')
