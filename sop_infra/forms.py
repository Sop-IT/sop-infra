from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from utilities.forms.fields import DynamicModelChoiceField
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.widgets import DatePicker
from utilities.forms.rendering import FieldSet
from utilities.forms import add_blank_choice
from dcim.models import Site, Location

from .models import *


__all__ = (
    'SopInfraForm',
    'SopInfraMerakiForm',
    'SopInfraSizingForm',
    'SopInfraClassificationForm',
)


class SopInfraClassificationForm(NetBoxModelForm):

    site = DynamicModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        required=True
    )
    site_infra_sysinfra = forms.ChoiceField(
        label=_('Infrastructure'),
        choices=add_blank_choice(InfraTypeChoices),
        required=False
    )
    site_type_indus = forms.ChoiceField(
        label=_('Industrial'),
        choices=add_blank_choice(InfraTypeIndusChoices),
        required=False
    )
    site_phone_critical = forms.ChoiceField(
        label=_('Phone critical'),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
        help_text=_('Is the phone critical for this site ?')
    )
    site_type_red = forms.ChoiceField(
        label=_('R&D'),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
        help_text=_('Does the site have and R&D department or a lab ?')
    )
    site_type_vip = forms.ChoiceField(
        label=_('VIP'),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
        help_text=_('Does the site host VIPs ?')
    )
    site_type_wms = forms.ChoiceField(
        label=_('WMS'),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
        help_text=_('Does the site run WMS ?')
    )

    class Meta:
        model = SopInfra
        fields = ['site', 'site_infra_sysinfra', 'site_type_indus',
                'site_phone_critical', 'site_type_red', 'site_type_vip', 'site_type_wms']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'tags' in self.fields:
            del self.fields['tags']


class SopInfraMerakiForm(NetBoxModelForm):

    site = DynamicModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        required=True
    )
    sdwanha = forms.ChoiceField(
        label=_('HA(S) / NHA target'),
        help_text=_('Calculated target for this site'),
        widget=forms.Select(
            attrs={
                'disabled':'disabled'
            }
        ),
        required=False
    )
    hub_order_setting = forms.ChoiceField(
        label=_('HUB order setting'),
        choices=add_blank_choice(InfraHubOrderChoices),
        initial='',
        help_text=_('Choose one of the various supported combinations'),
        required=False
    )
    hub_default_route_setting = forms.ChoiceField(
        label=_('HUB default route setting'),
        choices=add_blank_choice(InfraBoolChoices),
        initial='',
        help_text=_('Set to true if the default route should be sent through the AutoVPN'),
        required=False
    )
    sdwan1_bw = forms.CharField(
        label=_('WAN1 BW'),
        help_text=_('SDWAN > WAN1 Bandwidth (real link bandwidth)'),
        required=False
    )
    sdwan2_bw = forms.CharField(
        label=_('WAN2 BW'),
        help_text=_('SDWAN > WAN2 Bandwidth (real link bandwidth)'),
        required=False
    )
    site_sdwan_master_location = DynamicModelChoiceField(
        label=_('MASTER Location'),
        queryset=Location.objects.all(),
        help_text=_('When this site is an SDWAN SLAVE, you have to materialize a location on the MASTER site and link it here'),
        required=False
    )
    sdwan_master_site = forms.CharField(
        label=_('MASTER Site'),
        help_text=_('Automatically derived from the SDWAN master location'),
        widget=forms.Select(
            attrs={
                'disabled':'disabled'
            }
        ),
        required=False
    )
    migration_sdwan = forms.DateField(
        label=_('Migration SDWAN'),
        widget=DatePicker(),
        help_text=_('SDWAN > Site migration date to SDWAN'),
        required=False
    )
    monitor_in_starting = forms.ChoiceField(
        label=_('Monitor in starting'),
        choices=add_blank_choice(InfraBoolChoices),
        help_text=_('Centreon > Start monitoring when starting the site'),
        required=False
    )

    class Meta:
        model = SopInfra
        fields = ['site', 'sdwanha', 'hub_order_setting', 'hub_default_route_setting',
                  'sdwan1_bw', 'sdwan2_bw', 'site_sdwan_master_location', 'sdwan_master_site',
                  'migration_sdwan', 'monitor_in_starting']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'tags' in self.fields:
            del self.fields['tags']


class SopInfraSizingForm(NetBoxModelForm):

    site = DynamicModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        required=True
    )
    est_cumulative_users = forms.IntegerField(
        label=_('EST cumul. users'),
        required=False
    )

    class Meta:
        model = SopInfra
        fields = ['site', 'est_cumulative_users']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'tags' in self.fields:
            del self.fields['tags']


class SopInfraForm(
    SopInfraClassificationForm,
    SopInfraMerakiForm,
    SopInfraSizingForm
):

    site = DynamicModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        required=True
    )
    fieldsets = (
        FieldSet(
            'site', name=_('Site')
        ),
        FieldSet(
            'site_infra_sysinfra', 'site_type_indus', 'site_phone_critical',
            'site_type_red', 'site_type_vip', 'site_type_wms',
            name=_('Classification')
        ),
        FieldSet(
            'est_cumulative_users',
            name=_('Sizing')
        ),
        FieldSet(
            'sdwanha', 'hub_order_setting', 'hub_default_route_setting',
            'sdwan1_bw', 'sdwan2_bw', 'site_sdwan_master_location',
            'sdwan_master_site', 'migration_sdwan', 'monitor_in_starting',
            name=_('Meraki SDWAN')
        )
    )

    class Meta:
        model = SopInfra
        fields = [
            'site', 'site_infra_sysinfra', 'site_type_indus', 'site_phone_critical',
            'site_type_red', 'site_type_vip', 'site_type_wms',
            'est_cumulative_users',
            'sdwanha', 'hub_order_setting', 'hub_default_route_setting',
            'sdwan1_bw', 'sdwan2_bw', 'site_sdwan_master_location',
            'sdwan_master_site', 'migration_sdwan', 'monitor_in_starting',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'tags' in self.fields:
            del self.fields['tags']

