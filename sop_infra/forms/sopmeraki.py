import re

from django.contrib import messages
from django.forms.fields import BooleanField
import django_filters
from django import forms
from django.http import HttpRequest
from django.urls import reverse
from jsonschema import ValidationError
from sop_infra.utils.meraki_utils import SopMerakiRegexps, SopMerakiUtils
from utilities.forms.fields import (
    CommentField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
)
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from netbox.context import current_request
from dcim.models import Site, DeviceType, Device
from sop_infra.models import (
    SopMerakiDash,
    SopMerakiOrg,
    SopMerakiNet,
    SopMerakiDevice,
    SopMerakiSwitchStack,
)
from utilities.forms.rendering import FieldSet


class SopMerakiDashForm(NetBoxModelForm):

    comments = CommentField()
    
    class Meta:
        model = SopMerakiDash
        fields = ("nom", "description", "api_url")


class SopMerakiOrgForm(NetBoxModelForm):

    comments = CommentField()

    class Meta:
        model = SopMerakiOrg
        fields = (
            "nom", "dash", "meraki_id", "meraki_url", 
            "vpnexclude_prefix", "vpnexclude_ipadd",
            "syslog_servers",
        )


class SopMerakiNetForm(NetBoxModelForm):

    comments = CommentField()

    class Meta:
        model = SopMerakiNet
        fields = ("nom", "site", "org", "meraki_id", "bound_to_template", "meraki_url")


class SopMerakiSwitchStackForm(NetBoxModelForm):

    comments = CommentField()

    class Meta:
        model = SopMerakiSwitchStack
        fields = (
            "nom",
            "net",
            "meraki_id",
        )


class SopMerakiDeviceForm(NetBoxModelForm):

    comments = CommentField()

    class Meta:
        model = SopMerakiDevice
        fields = ("nom", "serial", "site", "org")



##############  FILTER FORMS ################################


class SopMerakiDashFilterForm(NetBoxModelFilterSetForm):
    model = SopMerakiDash
    nom = forms.CharField(required=False)
    description = forms.CharField(required=False)
    api_url = forms.CharField(required=False)


class SopMerakiOrgFilterForm(NetBoxModelFilterSetForm):
    model = SopMerakiOrg
    nom = forms.CharField(required=False)
    dash = DynamicModelChoiceField(queryset=SopMerakiDash.objects.all(), required=False)
    description = forms.CharField(required=False)
    meraki_id = forms.CharField(required=False)
    meraki_url = forms.CharField(required=False)


class SopMerakiNetFilterForm(NetBoxModelFilterSetForm):
    model = SopMerakiNet
    nom = forms.CharField(required=False)
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False)
    org = DynamicModelChoiceField(queryset=SopMerakiOrg.objects.all(), required=False)
    bound_to_template = forms.BooleanField(required=False)
    meraki_url = forms.CharField(required=False)
    meraki_notes = forms.CharField(required=False)
    meraki_id = forms.CharField(required=False)
    # TODO ptypes
    # TODO meraki_tags
    dash = DynamicModelChoiceField(queryset=SopMerakiDash.objects.all(), required=False)
    # TODO vpnmode
    # TODO appliance_status
    # TODO "meraki_peers_reachability",
    # TODO "exp_subnets_count",
    # TODO "last_stats_change",
    # TODO "primary_mx",
    # TODO "secondary_mx",
    # TODO with a choice /dropdown
    supports_ptype = forms.CharField(required=False)



class SopMerakiSwitchStackFilterForm(NetBoxModelFilterSetForm):
    model = SopMerakiSwitchStack
    nom = forms.CharField(required=False)
    net = DynamicModelChoiceField(queryset=SopMerakiNet.objects.all(), required=False)
    meraki_id = forms.CharField(required=False)


class SopMerakiDeviceFilterForm(NetBoxModelFilterSetForm):
    model = SopMerakiDevice
    nom = forms.CharField(required=False)
    serial = forms.CharField(required=False)
    model_name = forms.CharField(required=False)
    mac = forms.CharField(required=False, label="MAC Address")
    org = DynamicModelMultipleChoiceField(
        queryset=SopMerakiOrg.objects.all(), required=False, label="Meraki Oraganization",
    )
    meraki_netid = forms.CharField(required=False, label="Meraki network ID")
    meraki_network = DynamicModelMultipleChoiceField(
        queryset=SopMerakiNet.objects.all(), required=False, label="Meraki network",
    )
    meraki_notes = forms.CharField(required=False)
    ptype =  forms.MultipleChoiceField(
        choices=list(SopMerakiUtils.PRODUCT_TYPE_CHOICES),
        label="Meraki product type",
        required=False,
    )
    meraki_tags = forms.CharField(required=False)
    meraki_details = forms.CharField(required=False)
    firmware = forms.CharField(required=False)
    site = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), required=False, label="Netbox Site")

    # netbox_device_type = DynamicModelMultipleChoiceField(
    #     queryset=DeviceType.objects.all(), required=False
    # )
    netbox_device = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(), required=False
    )
    stack = DynamicModelMultipleChoiceField(
        queryset=SopMerakiSwitchStack.objects.all(), required=False
    )
    has_netbox_device = forms.NullBooleanField(
        required=False,
        label="Netbox device exists ?",
    )
    has_netbox_device_in_same_site = forms.NullBooleanField(
        required=False, label="On the same site ?"
    )
    has_netbox_device_of_same_type = forms.NullBooleanField(
        required=False, label="With the same type/model ?"
    )
    wan1ip = forms.CharField(required=False)
    wan2ip = forms.CharField(required=False)
    wan1status = forms.CharField(required=False)
    wan2status = forms.CharField(required=False)
    last_reported_at = forms.DateTimeField(required=False)
    sku = forms.CharField(required=False)
    claimed_at = forms.DateTimeField(required=False)
    country_code = forms.CharField(required=False)
    eox_status = forms.CharField(required=False)
    eox_end_of_sale = forms.DateTimeField(required=False)
    eox_end_of_support = forms.DateTimeField(required=False)
    

##############  ACTION FORMS ################################


class SopMerakiDashRefreshForm(forms.Form):

    dash = DynamicModelChoiceField(queryset=SopMerakiDash.objects.all(), required=False)
    details = forms.BooleanField(required=False)

    def clean(self):
        data = super().clean()
        dashs = SopMerakiDash.objects.none()
        base_url = reverse("plugins:sop_infra:sopmerakidash_list")
        request: HttpRequest = current_request.get()  # type: ignore

        def normalize_queryset(obj):
            qs = [str(item) for item in obj]
            if qs == []:
                return None
            return f"id=" + "&id=".join(qs)

        if data["dash"]:
            dashs = SopMerakiDash.objects.filter(pk=data["dash"].pk)
        else:
            dashs = SopMerakiDash.objects.all()

        return_url = (
            f"{base_url}?{normalize_queryset(dashs.values_list('id', flat=True))}"
        )
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")

        details: bool = False
        if data["details"]:
            details = data["details"]

        return {
            "dashs": dashs,
            "details": details,
            "return_url": return_url,
        }


class SopMerakiOrgRefreshChooseForm(forms.Form):

    org = DynamicModelChoiceField(queryset=SopMerakiOrg.objects.all(), required=False)
    details = forms.BooleanField(required=False)

    def clean(self):
        data = super().clean()
        orgs = SopMerakiOrg.objects.none()
        base_url = reverse("plugins:sop_infra:sopmerakiorg_list")
        request: HttpRequest = current_request.get()  # type: ignore

        def normalize_queryset(obj):
            qs = [str(item) for item in obj]
            if qs == []:
                return None
            return f"id=" + "&id=".join(qs)

        if data["org"]:
            orgs = SopMerakiOrg.objects.filter(pk=data["org"].pk)
        else:
            orgs = SopMerakiOrg.objects.all()

        return_url = (
            f"{base_url}?{normalize_queryset(orgs.values_list('id', flat=True))}"
        )
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")

        details: bool = False
        if data["details"]:
            details = data["details"]

        return {
            "orgs": orgs,
            "details": details,
            "return_url": return_url,
        }


class SopMerakiNetRefreshChooseForm(forms.Form):

    net = DynamicModelChoiceField(queryset=SopMerakiNet.objects.all(), required=False)
    details = forms.BooleanField(required=False)

    def clean(self):
        data = super().clean()
        nets = SopMerakiNet.objects.none()
        base_url = reverse("plugins:sop_infra:sopmerakinet_list")
        request: HttpRequest = current_request.get()  # type: ignore

        def normalize_queryset(obj):
            qs = [str(item) for item in obj]
            if qs == []:
                return None
            return f"id=" + "&id=".join(qs)

        if data["net"]:
            nets = SopMerakiNet.objects.filter(pk=data["net"].pk)
        else:
            nets = SopMerakiNet.objects.all()

        return_url = (
            f"{base_url}?{normalize_queryset(nets.values_list('id', flat=True))}"
        )
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")

        details: bool = False
        if data["details"]:
            details = data["details"]

        return {
            "nets": nets,
            "details": details,
            "return_url": return_url,
        }


class SopMerakiOrgClaimForm(forms.Form):

    serials = forms.RegexField(
        widget=forms.Textarea,
        required=True,
        regex=SopMerakiRegexps.meraki_list_of_serials_txt,
        help_text="Input serial numbers (XXXX-XXXX-XXXX), separated by commas and/or whitespace",
    )

    fieldsets = (
        FieldSet("serials"),
    )

    def clean(self):
        data = super().clean()
        serials_txt = data.get("serials")
        if not serials_txt:
            raise forms.ValidationError(
                "Only Meraki serial numbers separated by commas are accepted"
            )
        return {
            "serials_list": SopMerakiUtils.clean_serials_txt(serials_txt),
        }

    
class SopMerakiDeviceMoveForm(forms.Form):

    ptype = forms.HiddenInput()
    destination = DynamicModelChoiceField(
        queryset=SopMerakiNet.objects.all(), 
        required=True,
        query_params={
            "ptypes__icontains": "$ptype",
        },
    )
    force = forms.BooleanField(required=False)
    
    def clean(self):
        data = super().clean()
        destination = SopMerakiNet.objects.none()
        request: HttpRequest = current_request.get()  # type: ignore

        if not "destination" in data.keys():
            raise ValidationError(
                "Missing key: %(key)s",
                code="missing",
                params={"key": "destination"},
            )
        
        destination = SopMerakiNet.objects.filter(pk=data["destination"].pk)
        if destination.count()!=1:
            raise ValidationError(
                "Wrong destination count : %(count)s",
                code="incorrect_count",
                params={"count": destination.count()},
            )        

        return_url = request.GET.get("return_url", "")

        return {
            "destination": destination[0],
            "force": data["force"],
            "return_url": return_url,
        }



# class SopMerakiDeviceBulkMoveForm(PrimaryModelBulkEditForm):
#     tenant = DynamicModelChoiceField(
#         label=_('Tenant'),
#         queryset=Tenant.objects.all(),
#         required=False
#     )
#     enforce_unique = forms.NullBooleanField(
#         required=False,
#         widget=BulkEditNullBooleanSelect(),
#         label=_('Enforce unique space')
#     )

#     model = VRF
#     fieldsets = (
#         FieldSet('tenant', 'enforce_unique', 'description'),
#     )
#     nullable_fields = ('tenant', 'description', 'comments')

