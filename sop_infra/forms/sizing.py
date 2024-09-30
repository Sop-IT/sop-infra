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
    est_cumul_user = forms.IntegerField(
        label=_('EST cumul. users'),
        required=False
    )

    class Meta:
        model = InfraSizing
        fields = ('est_cumul_user',)
