from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views import View

from utilities.views import register_model_view, ViewTab
from dcim.models import Site

from ..models import *
from ..utils import get_object_or_create


__all__ = (
    'InfraSiteTabView',
)


@register_model_view(Site, name="infra")
class InfraSiteTabView(View):
    '''
    creates an "infrastructure" tab on the site page
    '''
    tab = ViewTab(label="Infrastructure")
    template: str = 'sop_infra/tab/tab.html'

    def get_extra_context(self, request, pk) -> dict:
        '''
        returns context for the tab
        '''
        context: dict = {}

        site = get_object_or_404(Site, pk=pk)
        classi = get_object_or_create(InfraClassification, site=site)
        
        sizing = get_object_or_create(InfraSizing, site=site)
        meraki = get_object_or_create(InfraMerakiSDWAN, site=site)

        context['classification'] = classi
        context['sizing'] = sizing
        context['meraki_sdwan'] = meraki

        return {'object': site, 'context': context}

    def get(self, request, pk):
        return render(request, self.template, self.get_extra_context(request, pk))
