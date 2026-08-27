from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from netbox.ui import actions, attrs, panels
from sop_infra.ui import attrs as sopattrs

#============================================================================================
#region SOPMERAKIDEVICE PANELS

class SopMerakiDevicePanel(panels.ObjectAttributesPanel):
    nom = attrs.TextAttr('nom', copy_button=True)
    ptype = attrs.TextAttr('ptype')
    model_name = attrs.TextAttr('model_name')
    serial = attrs.TextAttr('serial', copy_button=True) 
    mac = attrs.TextAttr('mac', copy_button=True) 
    firmware = attrs.TextAttr('firmware')
    meraki_notes = attrs.TextAttr('meraki_notes', copy_button=True)
    meraki_tags = attrs.TextAttr('meraki_tags')
    meraki_details = attrs.TextAttr('meraki_details')
    meraki_url = sopattrs.LinkAttr('meraki_url')
    lan_ip = attrs.TextAttr('lan_ip', label='LAN IP', copy_button=True)
    gps = attrs.GPSCoordinatesAttr(label='GPS')
    sku = attrs.TextAttr('sku')
    country_code = attrs.TextAttr('country_code')

class SopMerakiDeviceApplianceUplinkStatusPanel(panels.ObjectAttributesPanel):
    wan1ip = attrs.TextAttr('wan1ip', label='WAN 1 IP', copy_button=True)
    wan2ip = attrs.TextAttr('wan2ip', label='WAN 2 IP', copy_button=True)
    wan1status = attrs.TextAttr('wan1status', label='WAN 1 Status')
    wan2status = attrs.TextAttr('wan2status', label='WAN 2 Status')

class SopMerakiDeviceTimelinePanel(panels.ObjectAttributesPanel):
    cfg_updated_at = attrs.DateTimeAttr('cfg_updated_at')
    last_reported_at = attrs.DateTimeAttr('last_reported_at')
    claimed_at = attrs.DateTimeAttr('claimed_at')
    license_expiration_at = attrs.DateTimeAttr('license_expiration_at')
    eox_status = attrs.TextAttr('eox_status')
    eox_end_of_sale = attrs.DateTimeAttr('eox_end_of_sale')
    eox_end_of_support = attrs.DateTimeAttr('eox_end_of_support')

class SopMerakiDevicHierarchyPanel(panels.ObjectAttributesPanel):
    # MERAKI DASH
    org = attrs.RelatedObjectAttr('org', linkify=True)
    meraki_network = attrs.RelatedObjectAttr('meraki_network', linkify=True)
    meraki_netid = attrs.TextAttr('meraki_netid', copy_button=True) 

class SopMerakiDeviceRelatedPanel(panels.ObjectAttributesPanel):

    site = attrs.RelatedObjectAttr('site', linkify=True)
    netbox_device = attrs.RelatedObjectAttr('netbox_device', linkify=True)
    # CUR NB DEV TYPE
    # EXPECTED DEV TYP
    stack = attrs.RelatedObjectAttr('stack', linkify=True)

#endregion



class SopSyslogServerPanel(panels.ObjectAttributesPanel):
    nom = attrs.TextAttr('nom')
    server_address = attrs.RelatedObjectAttr('server_address', linkify=True)
    server_port = attrs.TextAttr('server_port')
    enabled = attrs.BooleanAttr('enabled')
