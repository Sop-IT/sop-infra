from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _

from netbox.views import generic

from ..forms.sizing import *
from ..models import *


__all__ = (
    'SizingEditView',
    'SizingDetailView',
)


class SizingDetailView(generic.ObjectView):
    '''
    returns the sizing detail page with context
    '''
    queryset = InfraSizing.objects.all()


class SizingEditView(generic.ObjectEditView):
    '''
    edits a sizing instance
    '''
    queryset = InfraSizing.objects.all()
    form = InfraSizingForm

    def get_return_url(self, request, obj=None) -> str:
        try:
            return f'/dcim/sites/{obj.site.id}/infra'
        except:return f'/dcim/sites/'
