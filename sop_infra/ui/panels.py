from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from netbox.ui import actions, attrs, panels


class SopSyslogServerPanel(panels.ObjectAttributesPanel):
    nom = attrs.TextAttr('nom')
    server_address = attrs.RelatedObjectAttr('server_address', linkify=True)
    server_port = attrs.TextAttr('server_port')
    enabled = attrs.BooleanAttr('enabled')
