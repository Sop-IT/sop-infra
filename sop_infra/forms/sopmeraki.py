from django import forms
from utilities.forms.fields import DynamicModelChoiceField
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm

from dcim.models import Site
from sop_infra.models import SopMerakiDash, SopMerakiOrg, SopMerakiNet


class SopMerakiDashForm(NetBoxModelForm):

    class Meta:
        model = SopMerakiDash
        fields = ('nom', 'description', 'api_url')


class SopMerakiOrgForm(NetBoxModelForm):

    class Meta:
        model = SopMerakiOrg
        fields = ('nom', 'description', 'dash', 'meraki_id', 'meraki_url')


class SopMerakiNetForm(NetBoxModelForm):

    class Meta:
        model = SopMerakiNet
        fields = ('nom', 'site', 'org', 'meraki_id', 'bound_to_template', 'meraki_url')


##############  FILTER FORMS ################################



class SopMerakiDashFilterForm(NetBoxModelFilterSetForm):
    model=SopMerakiDash
    nom=forms.CharField(
        required=False
    )
    description=forms.CharField(
        required=False
    )
    api_url=forms.CharField(
        required=False
    )


class SopMerakiOrgFilterForm(NetBoxModelFilterSetForm):
    model=SopMerakiOrg
    nom=forms.CharField(
        required=False
    )
    dash=DynamicModelChoiceField(
        queryset=SopMerakiDash.objects.all(),
        required=False
    )
    description=forms.CharField(
        required=False
    )
    meraki_id=forms.CharField(
        required=False
    )
    meraki_url=forms.CharField(
        required=False
    )

class SopMerakiNetFilterForm(NetBoxModelFilterSetForm):
    model=SopMerakiNet
    nom=forms.CharField(
        required=False
    )
    site=DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False
    )
    org=DynamicModelChoiceField(
        queryset=SopMerakiOrg.objects.all(),
        required=False
    )
    bound_to_template=forms.BooleanField(
        required=False
    )
    meraki_url=forms.CharField(
        required=False
    )
    meraki_notes=forms.CharField(
        required=False
    )
    meraki_id=forms.CharField(
        required=False
    )
