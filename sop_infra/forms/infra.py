import re
from django import forms
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from utilities.forms.fields import DynamicModelChoiceField
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.widgets import DatePicker
from utilities.forms.rendering import FieldSet
from netbox.context import current_request
from utilities.forms import add_blank_choice
from dcim.models import Site, Location, Region, SiteGroup
from dcim.choices import SiteStatusChoices

from sop_infra.models import *


__all__ = (
    "SopInfraForm",
    "SopMerakiForm",
    "SopInfraMerakiFilterForm",
    "SopInfraFilterForm",
    "SopInfraSizingFilterForm",
    "SopInfraClassificationFilterForm",
    "SopInfraRefreshForm",
)


class SopInfraForm(NetBoxModelForm):

    endpoint = DynamicModelChoiceField(
        label=_("Endpoint"), queryset=PrismaEndpoint.objects.all(), required=False
    )
    enabled = forms.ChoiceField(
        label=_("Enabled ?"),
        choices=add_blank_choice(InfraBoolChoices),
        initial=None,
        required=False,
    )

    est_cumulative_users_wc = forms.IntegerField(
        label=_("EST white collar users"), required=False
    )
    est_cumulative_users_bc = forms.IntegerField(
        label=_("EST blue collar users"), required=False
    )
    est_cumulative_users_ext = forms.IntegerField(
        label=_("EST external users"), required=False
    )
    est_cumulative_users_nom = forms.IntegerField(
        label=_("EST nomad users"), required=False
    )

    hub_order_setting = forms.ChoiceField(
        label=_("HUB order setting"),
        choices=add_blank_choice(InfraHubOrderChoices),
        initial="",
        help_text=_("Choose one of the various supported combinations"),
        required=False,
    )
    hub_default_route_setting = forms.ChoiceField(
        label=_("HUB default route setting"),
        choices=add_blank_choice(InfraBoolChoices),
        initial="",
        help_text=_(
            "Set to true if the default route should be sent through the AutoVPN"
        ),
        required=False,
    )
    sdwan1_bw = forms.CharField(
        label=_("WAN1 BW"),
        help_text=_("SDWAN > WAN1 Bandwidth (real link bandwidth)"),
        required=False,
    )
    sdwan2_bw = forms.CharField(
        label=_("WAN2 BW"),
        help_text=_("SDWAN > WAN2 Bandwidth (real link bandwidth)"),
        required=False,
    )
    site_sdwan_master_location = DynamicModelChoiceField(
        label=_("MASTER Location"),
        queryset=Location.objects.all(),
        help_text=_(
            "When this site is an SDWAN SLAVE, you have to materialize a location on the MASTER site and link it here"
        ),
        required=False,
    )
    master_site = DynamicModelChoiceField(
        label=_("MASTER Site"),
        queryset=Site.objects.all(),
        help_text=_("Or select the MASTER site."),
        required=False,
    )
    migration_sdwan = forms.DateField(
        label=_("Migration SDWAN"),
        widget=DatePicker(),
        help_text=_("SDWAN > Site migration date to SDWAN"),
        required=False,
    )
    monitor_in_starting = forms.BooleanField(
        label=_("Monitor in starting"),
        help_text=_("Centreon > Start monitoring when starting the site"),
        required=False,
    )
    site_infra_sysinfra = forms.ChoiceField(
        label=_("Infrastructure"),
        choices=add_blank_choice(InfraTypeChoices),
        required=False,
    )
    site_type_indus = forms.ChoiceField(
        label=_("Industrial"),
        choices=add_blank_choice(InfraTypeIndusChoices),
        required=False,
    )
    site_phone_critical = forms.ChoiceField(
        label=_("Phone critical"),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
        help_text=_("Is the phone critical for this site ?"),
    )
    site_type_red = forms.ChoiceField(
        label=_("R&D"),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
        help_text=_("Does the site have and R&D department or a lab ?"),
    )
    site_type_vip = forms.ChoiceField(
        label=_("VIP"),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
        help_text=_("Does the site host VIPs ?"),
    )
    site_type_wms = forms.ChoiceField(
        label=_("WMS"),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
        help_text=_("Does the site run WMS ?"),
    )

    fieldsets = (
        FieldSet(
            "site_infra_sysinfra",
            "site_type_indus",
            "site_phone_critical",
            "site_type_red",
            "site_type_vip",
            "site_type_wms",
            name=_("Sizing information"),
        ),
        FieldSet(
            "monitor_in_starting",
            name=_("Centreon"),
        ),
        FieldSet("endpoint", "enabled", name=_("PRISMA")),
        FieldSet("sdwan1_bw", "sdwan2_bw", name=_("Current link info")),
        FieldSet(
            "est_cumulative_users_wc",
            "est_cumulative_users_bc",
            "est_cumulative_users_ext",
            "est_cumulative_users_nom",
            "site_sdwan_master_location",
            "master_site",
            name=_("Site, user count & master/slave"),
        ),
        FieldSet(
            "hub_order_setting",
            "hub_default_route_setting",
            "migration_sdwan",
            name=_("Meraki deployment"),
        ),
    )

    class Meta:
        model = SopInfra
        fields = [
            "site_infra_sysinfra",
            "site_type_indus",
            "site_phone_critical",
            "site_type_red",
            "site_type_vip",
            "site_type_wms",
            "est_cumulative_users_wc",
            "est_cumulative_users_bc",
            "est_cumulative_users_ext",
            "est_cumulative_users_nom",
            "hub_order_setting",
            "hub_default_route_setting",
            "sdwan1_bw",
            "sdwan2_bw",
            "site_sdwan_master_location",
            "master_site",
            "migration_sdwan",
            "monitor_in_starting",
            "endpoint",
            "enabled",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "tags" in self.fields:
            del self.fields["tags"]


class SopMerakiForm(NetBoxModelForm):

    claim_net_mx = DynamicModelChoiceField(
        label=_("MX claim network"),
        # TODO filter by site org
        queryset=SopMerakiNet.objects.all(),
        query_params={
            "ptypes__contains": SopMerakiUtils.DEV_TYPE_MX,
            "bound_to_template": False,
        },
        required=False,
    )
    claim_net_ms = DynamicModelChoiceField(
        label=_("MS claim network"),
        # TODO filter by site org
        queryset=SopMerakiNet.objects.all(),
        query_params={
            "ptypes__contains": SopMerakiUtils.DEV_TYPE_MS,
            "bound_to_template": True,
        },
        required=False,
    )
    claim_net_mr = DynamicModelChoiceField(
        label=_("MR claim network"),
        # TODO filter by site org
        queryset=SopMerakiNet.objects.all(),
        query_params={
            "ptypes__contains": SopMerakiUtils.DEV_TYPE_MR,
            "bound_to_template": True,
        },
        required=False,
    )
    # claim_net_mv = DynamicModelChoiceField(
    #     label=_("MV claim network"),
    #     # TODO filter by site org
    #     queryset=SopMerakiNet.objects.all(),
    #     query_params={
    #         "ptypes__contains": SopMerakiUtils.DEV_TYPE_MR,
    #     },
    #     required=False,
    # )

    fieldsets = (
        FieldSet(
            "claim_net_mx",
            "claim_net_ms",
            "claim_net_mr",
            # "claim_net_mv",
            name=_("Claiming information"),
        ),
    )

    class Meta:
        model = SopInfra
        fields = [
            "claim_net_mx",
            "claim_net_ms",
            "claim_net_mr",
            # "claim_net_mv",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "tags" in self.fields:
            del self.fields["tags"]


# _____________
# filter forms


# _____________
# template to avoid code-repetition
class SopInfraBaseFilterForm(NetBoxModelFilterSetForm):
    model = SopInfra

    site_id = DynamicModelChoiceField(
        queryset=Site.objects.all(), required=False, label=_("Site")
    )
    region_id = DynamicModelChoiceField(
        queryset=Region.objects.all(), required=False, label=_("Region")
    )
    group_id = DynamicModelChoiceField(
        queryset=SiteGroup.objects.all(), required=False, label=_("Site group")
    )
    status = forms.ChoiceField(
        choices=add_blank_choice(SiteStatusChoices),
        initial=None,
        required=False,
        label=_("Status"),
    )


class SopInfraMerakiFilterForm(SopInfraBaseFilterForm):
    sdwanha = forms.ChoiceField(
        label=_("HA(S) / NHA target"),
        choices=add_blank_choice(InfraSdwanhaChoices),
        required=False,
    )
    hub_order_setting = forms.ChoiceField(
        label=_("HUB order setting"),
        choices=add_blank_choice(InfraHubOrderChoices),
        initial="",
        required=False,
    )
    hub_default_route_setting = forms.ChoiceField(
        label=_("HUB default route setting"),
        choices=add_blank_choice(InfraBoolChoices),
        initial="",
        required=False,
    )
    sdwan1_bw = forms.CharField(label=_("WAN1 BW"), required=False)
    sdwan2_bw = forms.CharField(label=_("WAN2 BW"), required=False)
    site_sdwan_master_location = DynamicModelChoiceField(
        label=_("MASTER Location"), queryset=Location.objects.all(), required=False
    )
    master_site = DynamicModelChoiceField(
        label=_("MASTER Site"), queryset=Site.objects.all(), required=False
    )
    migration_sdwan = forms.DateField(
        label=_("Migration SDWAN"), widget=DatePicker(), required=False
    )
    monitor_in_starting = forms.BooleanField(
        label=_("Monitor in starting"),
        required=False,
    )

    fieldsets = (
        FieldSet("region_id", "group_id", "site_id", name=_("Location")),
        FieldSet("status", name=_("Status")),
        FieldSet(
            "sdwanha",
            "hub_order_setting",
            "hub_default_route_setting",
            "sdwan1_bw",
            "sdwan2_bw",
            "site_sdwan_master_location",
            "master_site",
            "migration_sdwan",
            "monitor_in_starting",
            name=_("Attributes"),
        ),
    )


class SopInfraClassificationFilterForm(SopInfraBaseFilterForm):
    site_infra_sysinfra = forms.ChoiceField(
        label=_("Infrastructure"),
        choices=add_blank_choice(InfraTypeChoices),
        required=False,
    )
    site_type_indus = forms.ChoiceField(
        label=_("Industrial"),
        choices=add_blank_choice(InfraTypeIndusChoices),
        required=False,
    )
    site_phone_critical = forms.ChoiceField(
        label=_("Phone critical"),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
    )
    site_type_red = forms.ChoiceField(
        label=_("R&D"),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
    )
    site_type_vip = forms.ChoiceField(
        label=_("VIP"),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
    )
    site_type_wms = forms.ChoiceField(
        label=_("WMS"),
        choices=add_blank_choice(InfraBoolChoices),
        required=False,
    )

    fieldsets = (
        FieldSet("region_id", "group_id", "site_id", name=_("Location")),
        FieldSet("status", name=_("Status")),
        FieldSet(
            "site_infra_sysinfra",
            "site_type_indus",
            "site_phone_critical",
            "site_type_red",
            "site_type_vip",
            "site_type_wms",
            name=_("Attributes"),
        ),
    )


class SopInfraSizingFilterForm(SopInfraBaseFilterForm):
    ad_direct_users_wc = forms.IntegerField(
        required=False,
        label=_("AD direct. white collar users"),
        help_text=_("Numbers only"),
    )
    ad_direct_users_bc = forms.IntegerField(
        required=False,
        label=_("AD direct. blue collar users"),
        help_text=_("Numbers only"),
    )
    ad_direct_users_ext = forms.IntegerField(
        required=False,
        label=_("AD direct. external users"),
        help_text=_("Numbers only"),
    )
    ad_direct_users_nom = forms.IntegerField(
        required=False, label=_("AD direct. nomad users"), help_text=_("Numbers only")
    )
    est_cumulative_users_wc = forms.IntegerField(
        required=False,
        label=_("EST white collar users"),
        help_text=_("Numbers only"),
    )
    est_cumulative_users_bc = forms.IntegerField(
        required=False,
        label=_("EST blue collar users"),
        help_text=_("Numbers only"),
    )
    est_cumulative_users_ext = forms.IntegerField(
        required=False, label=_("EST users"), help_text=_("Numbers only")
    )
    est_cumulative_users_nom = forms.IntegerField(
        required=False, label=_("EST nomad users"), help_text=_("Numbers only")
    )
    site_user_count = forms.CharField(
        required=False, label=_("Site user count"), help_text=_("Example: 50<100")
    )
    site_mx_model = forms.CharField(
        required=False, label=_("Reco. MX Model"), help_text=_("Example: MX85")
    )
    wan_reco_bw = forms.IntegerField(
        required=False, label=_("Reco. BW (Mbps)"), help_text=_("Numbers only")
    )
    wan_computed_users_wc = forms.IntegerField(
        required=False,
        label=_("WAN computed white collar users"),
        help_text=_("Numbers only"),
    )
    wan_computed_users_bc = forms.IntegerField(
        required=False,
        label=_("WAN computed blue collar users"),
        help_text=_("Numbers only"),
    )

    fieldsets = (
        FieldSet("region_id", "group_id", "site_id", name=_("Location")),
        FieldSet("status", name=_("Status")),
        FieldSet(
            "ad_direct_users_wc",
            "ad_direct_users_bc",
            "ad_direct_users_ext",
            "ad_direct_users_nom",
            "est_cumulative_users_wc",
            "est_cumulative_users_bc",
            "est_cumulative_users_ext",
            "est_cumulative_users_nom",
            "wan_computed_users_wc",
            "wan_computed_users_bc",
            "wan_reco_bw",
            "site_user_count",
            "site_mx_model",
            name=_("Attributes"),
        ),
    )


class SopInfraFilterForm(
    SopInfraClassificationFilterForm, SopInfraMerakiFilterForm, SopInfraSizingFilterForm
):
    endpoint = forms.ModelChoiceField(
        queryset=PrismaEndpoint.objects.all(),
        required=False,
        label=_("Prisma Access Tunnel EP"),
    )
    enabled = forms.ChoiceField(
        choices=add_blank_choice(InfraBoolChoices), required=False, label=_("Enabled ?")
    )
    valid = forms.ChoiceField(
        choices=add_blank_choice(InfraBoolChoices), required=False, label=_("Valid ?")
    )

    fieldsets = (
        FieldSet("region_id", "group_id", "site_id", "status", name=_("Location")),
        FieldSet(
            "site_infra_sysinfra",
            "site_type_indus",
            "site_phone_critical",
            "site_type_red",
            "site_type_vip",
            "site_type_wms",
            name=_("Classification"),
        ),
        FieldSet(
            "ad_direct_users_wc",
            "ad_direct_users_bc",
            "ad_direct_users_ext",
            "ad_direct_users_nom",
            "est_cumulative_users_wc",
            "est_cumulative_users_bc",
            "est_cumulative_users_ext",
            "est_cumulative_users_nom",
            "wan_computed_users_wc",
            "wan_computed_users_bc",
            "wan_reco_bw",
            "site_user_count",
            "site_mx_model",
            name=_("Sizing"),
        ),
        FieldSet(
            "sdwanha",
            "hub_order_setting",
            "hub_default_route_setting",
            "sdwan1_bw",
            "sdwan2_bw",
            "site_sdwan_master_location",
            "master_site",
            "migration_sdwan",
            "monitor_in_starting",
            name=_("Meraki SDWAN"),
        ),
        FieldSet("endpoint", "enabled", "valid", name=_("Prisma Access Tunnel EP")),
    )


class SopInfraRefreshForm(forms.Form):

    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False)
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False)
    group = DynamicModelChoiceField(queryset=SiteGroup.objects.all(), required=False)

    def clean(self):
        data = super().clean()
        sites = Site.objects.none()
        base_url = reverse("plugins:sop_infra:sopinfra_list")
        request = current_request.get()

        def get_group_sites(obj):

            ids = (obj.get_descendants()).values_list("sites", flat=True)
            sites = Site.objects.filter(group=obj.pk)
            if ids.exists():
                sites |= Site.objects.filter(id__in=ids)

            if not sites.exists():
                messages.error(
                    request,
                    f"No sites has been found on {(obj._meta.verbose_name).title()} : {obj}",
                )
                raise forms.ValidationError(
                    {"site": f"No sites has been found on {obj}"}
                )

            return sites

        def get_region_sites(obj):

            ids = (obj.get_descendants()).values_list("sites", flat=True)
            sites = Site.objects.filter(region=obj.pk)
            if ids.exists():
                sites |= Site.objects.filter(id__in=ids)

            if not sites.exists():
                messages.error(
                    request,
                    f"No sites has been found on {(obj._meta.verbose_name).title()} : {obj}",
                )
                raise forms.ValidationError(
                    {"site": f"No sites has been found on {obj}"}
                )

            return sites

        def normalize_queryset(obj):

            qs = [str(item) for item in obj]
            if qs == []:
                return None

            return f"id=" + "&id=".join(qs)

        if data["region"]:
            sites |= get_region_sites(data["region"])

        if data["group"]:
            sites |= get_group_sites(data["group"])

        if data["site"]:
            sites |= Site.objects.filter(pk=data["site"].pk)

        if sites.filter(status="dc").exists():
            messages.warning(
                request,
                f"{' '.join(str(site.name) for site in sites.filter(status='dc'))} \
 skipped: You cannot recompute sizing on -DC- status site.",
            )

        infra = SopInfra.objects.filter(
            site__in=(sites.exclude(status="dc").distinct())
        )

        return_url = (
            f"{base_url}?{normalize_queryset(infra.values_list('id', flat=True))}"
        )
        if request.GET.get("return_url"):
            return_url = request.GET.get("return_url")

        return {
            "infra": infra,
            "return_url": return_url,
        }


class SopMerakiClaimForm(forms.Form):

    serials = forms.RegexField(
        widget=forms.Textarea,
        required=True,
        regex=r"^(?:[\s,]*[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}[\s,]*)+$",
        help_text="Input serial numbers (XXXX-XXXX-XXXX), separated by commas and/or whitespace",
    )
    status = forms.ChoiceField(
        choices=(
            ("active", "Active"),
            ("planned", "Planned"),
            ("staged", "Staged"),
            ("inventory", "Inventory"),
        ),
        required=True,
        initial="staged",
        help_text="Netbox status you want to assign to the claimed devices",
    )
    allow_netbox_site_change = forms.BooleanField(
        initial=False, required=False,
        label="Change netbox site ?",
        help_text="If the device exists on another netbox site, should we move it or leave it there ?",
    )
    allow_netbox_status_change = forms.BooleanField(
        initial=False, required=False,
        label="Change netbox device status ?",
        help_text="If the device exists with a different status, should we override it or leave be ?",
    )

    fieldsets = (
        FieldSet("serials", "status", name=""),
        FieldSet(
            "allow_netbox_site_change",
            "allow_netbox_status_change",
            name="Existing NETBOX devices",
        ),
    )

    def clean(self):
        data = super().clean()

        serials_txt = data.get("serials")
        if not serials_txt:
            try:
                request: HttpRequest = current_request.get()  # type: ignore
                messages.error(
                    request,
                    f"Only Meraki serial numbers separated by commas are accepted",
                )
            except:
                pass
            raise forms.ValidationError(
                "Only Meraki serial numbers separated by commas are accepted"
            )

        serials_txt = re.sub(r"\s+", ",", serials_txt)
        serials_list = re.split(r",+", serials_txt)

        return {
            "serials_list": serials_list,
            "status": data.get("status", "inventory"),
            "allow_netbox_site_change": data.get("allow_netbox_site_change", False),
            "allow_netbox_status_change": data.get("allow_netbox_status_change", False),
        }
