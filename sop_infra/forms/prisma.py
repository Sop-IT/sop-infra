from django import forms

from netbox.forms import NetBoxModelForm
from utilities.forms.fields import SlugField, DynamicModelChoiceField 

from sop_infra.models import (
    PrismaEndpoint, PrismaAccessLocation, PrismaComputedAccessLocation
)


__all__ = (
    'PrismaEndpointForm',
    'PrismaAccessLocationForm',
    'PrismaComputedAccessLocationForm',
)


class PrismaEndpointForm(NetBoxModelForm):

    name = forms.CharField(required=True)
    slug = SlugField()
    access_location = DynamicModelChoiceField(
        PrismaAccessLocation.objects.all(),
        required=True
    )

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
    compute_location = DynamicModelChoiceField(
        PrismaComputedAccessLocation.objects.all(),
        required=True
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

