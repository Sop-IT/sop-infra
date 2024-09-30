from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import *


__all__ = (
    'MerakiSDWANForm',
)


class MerakiSDWANForm(forms.ModelForm):
    '''
    creates a form for a MerakiSDWAN instance
    '''
    nha_target = forms.ChoiceField(
        label=_('HA(S) / NHA target'),
        required=False,
        help_text=_('Calculated target for this site.'),
        choices=InfraSdwanhaChoices,
        widget=forms.Select(
            attrs={
                'disabled':'disabled'
            }
        )
    )
    hub_order_setting = forms.ChoiceField(
        label=_('HUB order setting'),
        required=False,
        help_text=_('Choose one of the various supported combinations.'),
        choices=InfraMerakiHubOrderChoices
    )
    hub_default_route_setting = forms.ChoiceField(
        choices=InfraBoolChoices,
        label=_('HUB default route setting'),
        required=False,
        help_text=_('Set to true if the default route should be sent through the AutoVPN.')
    )
    wan1_bw = forms.CharField(
        label=_('WAN1 BW'),
        required=False,
        help_text=_('SDWAN > WAN1 Bandwidth (real link bandwidth).')
    )
    wan2_bw = forms.CharField(
        label=_('WAN2 BW'),
        required=False,
        help_text=_('SDWAN > WAN2 Bandwidth (real link bandwidth).')
    )
    master_location = forms.CharField(
        label=_('MASTER Location'),
        required=False,
        help_text=_('When this site is an SDWAN SLAVE, you have to materialize a location on the MASTER site and link it here.')
    )
    master_site = forms.CharField(
        label=_('MASTER Site'),
        required=False,
        help_text=_('Automatically derived from the SDWAN master location.'),
        widget=forms.Select(
            attrs={
                'disabled':'disabled'
            }
        )
        
    )
    migration_date = forms.CharField(
        label=_('Migration date'),
        required=False,
        help_text=_('SDWAN > Site migration date to SDWAN.')
    )
    monitor_in_starting = forms.ChoiceField(
        label=_('Monitor in starting'),
        required=False,
        help_text=_('Centreon > Start monitoring when starting the site.'),
        choices=InfraBoolChoices
    )

    class Meta:
        model = InfraMerakiSDWAN
        fields = ('nha_target', 'hub_order_setting', 'hub_default_route_setting',
            'wan1_bw', 'wan2_bw', 'master_location', 'master_site',
            'migration_date', 'monitor_in_starting')
