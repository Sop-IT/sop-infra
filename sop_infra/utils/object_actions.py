from django.db.models import ForeignKey
from django.template import loader
from django.urls.exceptions import NoReverseMatch
from django.utils.translation import gettext_lazy as _

from core.models import ObjectType
from extras.models import ExportTemplate
from netbox.object_actions import ObjectAction
from utilities.querydict import prepare_cloned_fields
from utilities.views import get_action_url, get_viewname

__all__ = (
    'MoveObject',
)

from django.urls import reverse
class MoveObject(ObjectAction):
    """
    Move a single object.
    """
    name = 'move'
    label = _('Move')
    permissions_required = {'move'}
    url_kwargs = ['pk']
    template_name = 'buttons/move.html'

    @classmethod
    def get_context(cls, context, model):
        object_type = ObjectType.objects.get_for_model(model)
        #user = context['request'].user
        url_params = super().get_url_params(context)
        return_url=context.get("return_url")
        if not return_url:
            return_url=get_action_url(model, None, False, kwargs={'pk': model.pk})
        #print(f"{return_url=} / {context.get("csrf_token")=}")
        return {
            'return_url': return_url,
            'object' : model,
            'csrf_token': context['csrf_token'],
            'form_data' : {
                'object_type': object_type.id,
                'object_id': model.pk,
            }
        }