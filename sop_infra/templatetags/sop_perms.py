from django import template

from sop_utils.misc import SopUtils

__all__ = (
    'can_refresh',
    'can_update_connectivity_statuses',
    'can_claim_meraki_devices',
    'can_recompute_sizing',
)

register = template.Library()


@register.filter()
def can_refresh(user, instance):
    # TODO: constante
    return SopUtils.check_permission(user, instance, 'refresh')

@register.filter()
def can_update_connectivity_statuses(user, instance):
    # TODO: constante
    return SopUtils.check_permission(user, instance, 'update_connectivity_statuses')

@register.filter()
def can_claim_meraki_devices(user, instance):
    # TODO: constante
    return SopUtils.check_permission(user, instance, 'claim_meraki_devices')

@register.filter()
def can_recompute_sizing(user, instance):
    # TODO: constante
    return SopUtils.check_permission(user, instance, 'recompute_sizing')


