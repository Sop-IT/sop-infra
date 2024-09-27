from django.utils.translation import gettext_lazy as _

from netbox.views import generic

from ..forms.meraki_sdwan import *
from ..models import *


__all__ = (
    'MerakiSDWANDetailView',
    'MerakiSDWANEditView',
)


class MerakiSDWANDetailView(generic.ObjectView):
    '''
    returns the MerakiSDWAN detail page with context
    '''
    queryset = InfraMerakiSDWAN.objects.all()


class MerakiSDWANEditView(generic.ObjectEditView):
    '''
    edits a MerakiSDWAN instance
    '''
    queryset = InfraMerakiSDWAN.objects.all()
    form = MerakiSDWANForm

    def get_return_url(self, request, obj=None) -> str:
        try:
            return f'/dcim/sites/{obj.site.id}/infra'
        except:return f'/dcim/sites/'
