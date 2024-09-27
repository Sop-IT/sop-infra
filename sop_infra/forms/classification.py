from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import *


__all__ = (
    'ClassificationForm',
)


class ClassificationForm(forms.ModelForm):
    '''
    creates a form for a classification instance
    '''

    infrastructure = forms.ChoiceField(
        label=_('System Infrastructure'),
        required=False,
        choices=InfraTypeChoices
    )
    industrial = forms.ChoiceField(
        label=_('Industrial'),
        required=False,
        choices=InfraTypeIndusChoices
    )
    phone_critical = forms.ChoiceField(
        choices=InfraBoolChoices,
        label=_('Phone Critical'),
        required=False,
        help_text=_('Is the phone critical for this site ?')
    )
    r_and_d = forms.ChoiceField(
        choices=InfraBoolChoices,
        label=_('R&D'),
        required=False,
        help_text=_('Does the site have an R&D departement or a lab ?')
    )
    vip = forms.ChoiceField(
        choices=InfraBoolChoices,
        label=_('VIP'),
        required=False,
        help_text=_('Does the site host vips ?')
    )
    wms = forms.ChoiceField(
        choices=InfraBoolChoices,
        label=_('WMS'),
        required=False,
        help_text=_('Does the site run wms ?')
    )

    class Meta:
        model = InfraClassification
        fields = ('infrastructure', 'industrial', 'phone_critical', 'r_and_d', 'vip', 'wms')
