from django import forms

from timezone_field import TimeZoneFormField

from ipam.models import IPAddress
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms import add_blank_choice
from utilities.forms.rendering import FieldSet
from utilities.forms.fields import SlugField, DynamicModelChoiceField 

from sop_infra.models import (
    PrismaEndpoint, PrismaAccessLocation, PrismaComputedAccessLocation
)


__all__ = (
    'PrismaEndpointForm',
    'PrismaAccessLocationForm',
    'PrismaComputedAccessLocationForm',
    'PrismaEndpointFilterForm',
    'PrismaAccessLocationFilterForm',
    'PrismaComputedAccessLocationFilterForm'
)


class PrismaEndpointForm(NetBoxModelForm):

    name = forms.CharField(required=True)
    slug = SlugField()
    ip_address = forms.ModelChoiceField(
        queryset=IPAddress.objects.filter(address__endswith="/32"),
        required=True,
        label='IP Address'
    )
    access_location = DynamicModelChoiceField(
        PrismaAccessLocation.objects.all(),
        required=True
    )

    fieldsets = (
        FieldSet(
            'name', 'slug',
            name='Name',
        ),
        FieldSet(
            'ip_address', 'access_location',
            name='IP Address'
        )
    )

    FieldSet
    class Meta:
        model = PrismaEndpoint
        fields = [
            'name', 'slug', 'ip_address', 'access_location',
        ]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'tags' in self.fields:
            del self.fields['tags']




class PrismaAccessLocationForm(NetBoxModelForm):

    name = forms.CharField(required=True)
    slug = SlugField()
    time_zone = TimeZoneFormField(
        label='Time zone',
        choices=add_blank_choice(TimeZoneFormField().choices),
        required=False
    )
    compute_location = DynamicModelChoiceField(
        PrismaComputedAccessLocation.objects.all(),
        required=True
    )

    fieldsets = (
        FieldSet(
            'name', 'slug',
            name='Name',
        ),
        FieldSet(
            'physical_address', 'time_zone',
            'latitude', 'longitude', 'compute_location',
            name='Location',
        )
    )

    class Meta:
        model = PrismaAccessLocation
        fields = [
            'name', 'slug', 'physical_address',
            'time_zone', 'latitude', 'longitude', 'compute_location',
        ]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'tags' in self.fields:
            del self.fields['tags']




class PrismaComputedAccessLocationForm(NetBoxModelForm):

    name = forms.CharField(required=True)
    slug = SlugField()

    fieldsets = (
        FieldSet(
            'name', 'slug',
            name='Name',
        ),
        FieldSet(
            'strata_id', 'strata_name', 'bandwidth',
            name='Strata',
        ),
    )

    class Meta:
        model = PrismaComputedAccessLocation
        fields = [
            'name', 'slug', 'strata_id', 'strata_name',
            'bandwidth',
        ]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'tags' in self.fields:
            del self.fields['tags']



class PrismaEndpointFilterForm(NetBoxModelFilterSetForm):

    model = PrismaEndpoint

    name = forms.CharField(required=False)
    slug = forms.CharField(required=False)
    ip_address = forms.ModelChoiceField(
        IPAddress.objects.filter(address__endswith='/32'),
        required=False
    )
    access_location = DynamicModelChoiceField(
        queryset=PrismaAccessLocation.objects.all(),
        required=False
    )

    fieldsets = (
        FieldSet(
            'name', 'slug',
            name='Name',
        ),
        FieldSet(
            'ip_address', 'access_location',
            name='IP Address'
        )
    )



class PrismaAccessLocationFilterForm(NetBoxModelFilterSetForm):

    model = PrismaAccessLocation

    name = forms.CharField(required=False)
    slug = forms.CharField(required=False)
    physical_address = forms.CharField(required=False)
    time_zone = TimeZoneFormField(
        choices=add_blank_choice(TimeZoneFormField().choices),
        required=False,
        label='Time zone'
    )
    latitude = forms.IntegerField(required=False)
    longitude = forms.IntegerField(required=False)
    compute_location = DynamicModelChoiceField(
        queryset=PrismaComputedAccessLocation.objects.all(),
        required=False,
        label='Computed access location'
    )

    fieldsets = (
        FieldSet(
            'name', 'slug',
            name='Name',
        ),
        FieldSet(
            'physical_address', 'time_zone',
            'latitude', 'longitude', 'compute_location',
            name='Location',
        )
    )



class PrismaComputedAccessLocationFilterForm(NetBoxModelFilterSetForm):

    model = PrismaComputedAccessLocation

    name = forms.CharField(required=False)
    slug = forms.CharField(required=False)
    strata_id = forms.CharField(
        required=False,
        label='Strata ID'
    )
    strata_name = forms.CharField(
        required=False,
        label='Strata name'
    )
    bandwidth = forms.IntegerField(
        required=False,
        label='Bandwidth (Mbps)'
    )

    fieldsets = (
        FieldSet(
            'name', 'slug',
            name='Name',
        ),
        FieldSet(
            'strata_id', 'strata_name', 'bandwidth',
            name='Strata',
        ),
    )

