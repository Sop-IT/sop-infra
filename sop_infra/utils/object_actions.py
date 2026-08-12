from django.db.models import ForeignKey
from django.template import loader
from django.urls.exceptions import NoReverseMatch
from django.utils.translation import gettext_lazy as _

from core.models import ObjectType
from extras.models import ExportTemplate
from netbox.object_actions import ObjectAction
from utilities.querydict import prepare_cloned_fields
from utilities.views import get_action_url

__all__ = (
    'MoveObject',
)


class MoveObject(ObjectAction):
    """
    Move a single object.
    """
    name = 'move'
    label = _('Move')
    permissions_required = {'move'}
    url_kwargs = ['pk']
    template_name = 'buttons/move.html'