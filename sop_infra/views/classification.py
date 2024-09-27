from django.utils.translation import gettext_lazy as _
from netbox.views import generic

from ..forms.classification import *
from ..models import *


__all__ = (
    'ClassificationDetailView',
    'ClassificationEditView',
)


class ClassificationDetailView(generic.ObjectView):
    '''
    returns the classification detail page with context
    '''
    queryset = InfraClassification.objects.all()


class ClassificationEditView(generic.ObjectEditView):
    '''
    edits a Classification instance
    '''
    queryset = InfraClassification.objects.all()
    form = ClassificationForm

    def get_return_url(self, request, obj=None) -> str:
        try:
            return f'/dcim/sites/{obj.site.id}/infra'
        except:return f'/dcim/sites/'
