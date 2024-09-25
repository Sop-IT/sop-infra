from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import *


__all__ = (
    'InfraSizingForm',
)


class InfraSizingForm(forms.ModelForm):
    '''
    creates a form for a sizing instance
    '''
    ad_cumul_user = forms.CharField(label=_('AD cumul. users'), required=False)
    est_cumul_user = forms.CharField(label=_('EST cumul. users'), required=False)
    reco_bw = forms.CharField(label=_('Reco. BW (Mbps)'), required=False,
        help_text=_('Recommended bandwidth (Mbps)'))

    class Meta:
        model = InfraSizing
        fields = ('ad_cumul_user', 'est_cumul_user', 'reco_bw')
