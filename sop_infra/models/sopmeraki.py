from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from netbox.models import NetBoxModel
from dcim.models import Site, Location


import meraki
from logging import Logger



__all__ = ("SopMerakiDash", "SopMerakiOrg", "SopMerakiNet","SopMerakiUtils",)



class SopMerakiUtils:
    
    __parsed : bool = False
    __meraki_api_keys : dict[str,str] = {}

    @classmethod
    def try_parse_configuration(cls):
        # parse all configuration.py informations
        from django.conf import settings
        infra_config = settings.PLUGINS_CONFIG.get("sop_infra")
        if infra_config is None :
            raise Exception("No sop_infra plugin config !")
        sopmeraki_config = infra_config.get("sopmeraki")
        if sopmeraki_config is None :
            raise Exception("No sopmeraki plugin config key !")
        cls.__meraki_api_keys=sopmeraki_config.get("api_keys")
        if cls.__meraki_api_keys is None :
            raise Exception("No sopmeraki/api_keys plugin config key !")
        cls.__parsed=True

    @classmethod
    def get_ro_api_key_for_dash_name(cls, name:str) -> str :
        return cls.get_api_key_for_dash_name(name, "RO")

    @classmethod
    def get_rw_api_key_for_dash_name(cls, name:str) -> str :
        return cls.get_api_key_for_dash_name(name, "RW")
    
    @classmethod
    def get_api_key_for_dash_name(cls, name:str, type:str) -> str :
        if type not in ("RO", "RW") : 
            raise Exception ("API key type must be 'RO' or 'RW'")
        if not cls.__parsed:
            cls.try_parse_configuration()
        keys:dict[str,str]=cls.__meraki_api_keys.get(name) # type: ignore
        if keys is None: 
            raise Exception(f"No keys for dashboard '{name}'")
        return keys.get(type, "")
    
    @classmethod
    def connect(cls, dash_name:str, api_url:str, simulate:bool=False):
        if simulate:
            api_key=cls.get_ro_api_key_for_dash_name(dash_name)  
        else :
            api_key=cls.get_rw_api_key_for_dash_name(dash_name)
        if api_key is None or api_key.strip()=="":
            raise Exception(f"APIKEY is empty ! ")
        return meraki.DashboardAPI(api_key=api_key, base_url=api_url, suppress_logging=True, simulate=simulate)
    
    @classmethod
    def refresh_dashboards(cls, log:Logger=None):
        for smd in SopMerakiDash.objects.all():
            if log : 
                log.info(f"Try to connect to {smd.nom} via url {smd.api_url}...")
            conn=cls.connect(smd.nom, smd.api_url, True)
            if log : 
                log.info(f"Try to refresh {smd.nom}")
            smd.refresh_from_meraki(conn, log)

    @staticmethod
    def extractSiteName(name):
        from ..utils import SopRegExps
        m=SopRegExps.meraki_sitename_re.match(f"{name}")
        if m is None:
            return None
        return m.group(1).lower()




class SopMerakiDash(NetBoxModel):

    nom=models.CharField(
        max_length=50, null=False, blank=False, unique=True, verbose_name="Name"
    )

    description=models.CharField(
        max_length=250, null=True, blank=True, unique=False, verbose_name="Description"
    )

    api_url=models.URLField(
        null=False, blank=False, verbose_name="API base URL"
    )
    
    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:sopmerakidash_detail", args=[self.pk])
    
    class Meta(NetBoxModel.Meta):
        verbose_name = "Meraki dashboard"
        verbose_name_plural = "Meraki dashboards"

    def refresh_from_meraki(self, conn:meraki.DashboardAPI, log:Logger=None):
        save=self.pk is None

        if save:
            self.full_clean()
            self.save()

        org_ids=[]
        smo:SopMerakiOrg
        if log: 
            log.info(f"Looping on {self.nom} organizations...")
        for org in conn.organizations.getOrganizations():
            org_ids.append(org['id'])
            if not SopMerakiOrg.objects.filter(meraki_id=org['id']).exists():
                if log: 
                    log.info(f"Creating Org on {org['name']}...")
                smo=SopMerakiOrg()
            else:
                smo=SopMerakiOrg.objects.get(meraki_id=org['id'])
            smo.refresh_from_meraki(conn, org, self)

        for smo in self.orgs.all():
            if smo.meraki_id not in org_ids:
                smo.delete()

        return save

class SopMerakiOrg(NetBoxModel):

    nom=models.CharField(
        max_length=50, null=False, blank=False, verbose_name="Name"
    )

    dash=models.ForeignKey(
        to=SopMerakiDash,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        verbose_name="Dashboard",
        related_name="orgs",
    )

    meraki_id = models.CharField(
        max_length=100, null=False, blank=False, unique=True, verbose_name="Meraki OrgID"
    )
    meraki_url=models.URLField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:sopmerakiorg_detail", args=[self.pk])

    
    class Meta(NetBoxModel.Meta):
        verbose_name = "Meraki Organisation"
        verbose_name_plural = "Meraki Organisations"
        constraints = [
            models.UniqueConstraint(
                fields=["nom","dash"],
                name="%(app_label)s_%(class)s_unique_dash_org",
                violation_error_message=_("This dashboard already has an org with this name."),
            ),
        ]

    def refresh_from_meraki(self, conn:meraki.DashboardAPI, org, dash:SopMerakiDash):
        save=self.pk is None
        # cf https://developer.cisco.com/meraki/api-v1/get-organizations/
        if self.nom != org['name'] :
            self.nom = org['name']
            save=True
        if self.meraki_id != org['id'] :
            self.meraki_id = org['id']
            save=True
        if  self.dash_id is None or self.dash != dash :
            self.dash = dash
            save=True
        if self.meraki_url != org['url']:
            self.meraki_url = org['url']
            save=True
        
        if save:
            self.full_clean()
            self.save()

        net_ids=[]
        smn:SopMerakiNet
        for net in conn.organizations.getOrganizationNetworks(org['id'], total_pages=-1) :
            net_ids.append(net['id'])
            if not SopMerakiNet.objects.filter(meraki_id=net['id']).exists():
                smn=SopMerakiNet()
            else:
                smn=SopMerakiNet.objects.get(meraki_id=net['id'])
            smn.refresh_from_meraki(conn, net, self)
        
        for smn in self.nets.all():
            if smn.meraki_id not in net_ids:
                smn.delete()

        return save


class SopMerakiNet(NetBoxModel):

    nom=models.CharField(
        max_length=150, null=False, blank=False, verbose_name="Name"
    )

    site = models.ForeignKey(
        to=Site,
        related_name="site",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Site",
    )

    org=models.ForeignKey(
        to=SopMerakiOrg,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        verbose_name="Organization",
        related_name="nets",
    )
    
    meraki_id = models.CharField(
        max_length=100, null=False, blank=False, unique=True, verbose_name="Meraki OrgID"
    )

    bound_to_template = models.BooleanField(default=False, null=True, blank=True)
    meraki_url=models.URLField(null=True, blank=True)
    meraki_notes=models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"{self.nom}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:sop_infra:sopmerakinet_detail", args=[self.pk])

    
    class Meta(NetBoxModel.Meta):
        verbose_name = "Meraki Network"
        verbose_name_plural = "Meraki Networks"
        constraints = [
            models.UniqueConstraint(
                fields=["nom","org"],
                name="%(app_label)s_%(class)s_unique_net_dash",
                violation_error_message=_("This org already has an net with this name."),
            ),
        ]
    
    def refresh_from_meraki(self, conn:meraki.DashboardAPI, net, org:SopMerakiOrg):
        # cf https://developer.cisco.com/meraki/api-v1/get-organization-networks/
        save=self.pk is None
        if self.nom != net['name'] :
            self.nom = net['name']
            save = True
        if self.meraki_id != net['id'] :
            self.meraki_id = net['id']
            save = True
        if self.org_id is None or self.org != org :
            self.org = org 
            save = True
        if self.bound_to_template != net['isBoundToConfigTemplate'] :
            self.bound_to_template = net['isBoundToConfigTemplate']
            save = True
        if self.meraki_url != net['url'] : 
            self.meraki_url = net['url']
            save = True
        if self.meraki_notes != net['notes'] :
            self.meraki_notes = net['notes']
            save = True
       
        slug = SopMerakiUtils.extractSiteName(self.nom)
        if slug is None : 
            val = None
        elif not Site.objects.filter(slug=slug).exists():
            val = None
        else:
            val = Site.objects.get(slug=slug)
        if self.site_id is None or self.site != val :
            self.site = val
        
        if save: 
            self.full_clean()
            self.save()

        return save
