from django import forms
from django.http import HttpRequest
from django.urls import reverse
from utilities.forms.fields import DynamicModelChoiceField
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from netbox.context import current_request
from dcim.models import Site
from sop_infra.models import SopMerakiDash, SopMerakiOrg, SopMerakiNet, SopMerakiDevice, SopMerakiSwitchStack


class SopMerakiDashForm(NetBoxModelForm):

    class Meta:
        model = SopMerakiDash
        fields = ('nom', 'description', 'api_url')


class SopMerakiOrgForm(NetBoxModelForm):

    class Meta:
        model = SopMerakiOrg
        fields = ('nom', 'dash', 'meraki_id', 'meraki_url')


class SopMerakiNetForm(NetBoxModelForm):

    class Meta:
        model = SopMerakiNet
        fields = ('nom', 'site', 'org', 'meraki_id', 'bound_to_template', 'meraki_url')


class SopMerakiSwitchStackForm(NetBoxModelForm):

    class Meta:
        model = SopMerakiSwitchStack
        fields = ('nom', 'net', 'meraki_id',)


class SopMerakiDeviceForm(NetBoxModelForm):

    class Meta:
        model = SopMerakiDevice
        fields = ('nom', 'serial', 'site', 'org', 'meraki_network')


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


class SopMerakiSwitchStackFilterForm(NetBoxModelFilterSetForm):
    model=SopMerakiSwitchStack
    nom=forms.CharField(
        required=False
    )
    net=DynamicModelChoiceField(
        queryset=SopMerakiNet.objects.all(),
        required=False
    )
    meraki_id=forms.CharField(
        required=False
    )


class SopMerakiDeviceFilterForm(NetBoxModelFilterSetForm):
    model=SopMerakiDevice
    nom=forms.CharField(
        required=False
    )




##############  ACTION FORMS ################################


class SopMerakiDashRefreshForm(forms.Form):

    dash = DynamicModelChoiceField(queryset=SopMerakiDash.objects.all(), required=False)
    details = forms.BooleanField(required=False)

    def clean(self):
        data = super().clean()
        dashs = SopMerakiDash.objects.none()
        base_url = reverse("plugins:sop_infra:sopmerakidash_list")
        request:HttpRequest = current_request.get() # type: ignore

        def normalize_queryset(obj):
            qs = [str(item) for item in obj]
            if qs == []:
                return None
            return f"id=" + "&id=".join(qs)

        if data["dash"]:
            dashs = SopMerakiDash.objects.filter(pk=data["dash"].pk)
        else: 
            dashs = SopMerakiDash.objects.all()

        return_url=f"{base_url}?{normalize_queryset(dashs.values_list('id', flat=True))}"
        if request.GET.get("return_url"):
            return_url=request.GET.get("return_url")

        details:bool=False
        if data["details"]:
            details=data["details"]

        return {
            "dashs": dashs, "details":details,
            "return_url": return_url,
        }


class SopMerakiOrgRefreshChooseForm(forms.Form):

    org = DynamicModelChoiceField(queryset=SopMerakiOrg.objects.all(), required=False)
    details = forms.BooleanField(required=False)

    def clean(self):
        data = super().clean()
        orgs = SopMerakiOrg.objects.none()
        base_url = reverse("plugins:sop_infra:sopmerakiorg_list")
        request:HttpRequest = current_request.get() # type: ignore

        def normalize_queryset(obj):
            qs = [str(item) for item in obj]
            if qs == []:
                return None
            return f"id=" + "&id=".join(qs)

        if data["org"]:
            orgs = SopMerakiOrg.objects.filter(pk=data["org"].pk)
        else: 
            orgs = SopMerakiOrg.objects.all()

        return_url=f"{base_url}?{normalize_queryset(orgs.values_list('id', flat=True))}"
        if request.GET.get("return_url"):
            return_url=request.GET.get("return_url")

        details:bool=False
        if data["details"]:
            details=data["details"]

        return {
            "orgs": orgs, "details":details,
            "return_url": return_url,
        }


class SopMerakiNetRefreshChooseForm(forms.Form):

    net = DynamicModelChoiceField(queryset=SopMerakiNet.objects.all(), required=False)
    details = forms.BooleanField(required=False)

    def clean(self):
        data = super().clean()
        nets = SopMerakiNet.objects.none()
        base_url = reverse("plugins:sop_infra:sopmerakinet_list")
        request:HttpRequest = current_request.get() # type: ignore

        def normalize_queryset(obj):
            qs = [str(item) for item in obj]
            if qs == []:
                return None
            return f"id=" + "&id=".join(qs)

        if data["net"]:
            orgs = SopMerakiNet.objects.filter(pk=data["net"].pk)
        else: 
            orgs = SopMerakiNet.objects.all()

        return_url=f"{base_url}?{normalize_queryset(orgs.values_list('id', flat=True))}"
        if request.GET.get("return_url"):
            return_url=request.GET.get("return_url")

        details:bool=False
        if data["details"]:
            details=data["details"]

        return {
            "nets": nets, "details":details,
            "return_url": return_url,
        }

