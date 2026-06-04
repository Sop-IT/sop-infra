from extras.scripts import Script,  ObjectVar, MultiObjectVar, BooleanVar 
from sop_infra.utils.meraki_tools import MerakiToolMixin
from utilities.exceptions import AbortScript
import dcim.models
from dcim.models import Site, SiteGroup, Region
from sop_utils.dates import DateUtils
from sop_utils.misc import SopUtils
from sop_utils.mails import MailUtils

from sop_infra.utils.netbox_utils import SopInfraUtils

from extras.jobs import ScriptJob
import uuid
from utilities.request import NetBoxFakeRequest


def _get_script(module_name, script_name):
    from extras.models import Script, ScriptModule
    module = ScriptModule.objects.get(file_path=f'{module_name}.py')
    script = Script.objects.filter(module_id=module.pk).filter(name=script_name)[0]
    return script

def _enqueue_site_update(request, script_data, commit):
        script = _get_script("netbox2meraki_v6", "UpdateOneSite")
        import time
        time.sleep(0.1)
        from datetime import timedelta
        return ScriptJob.enqueue(
            instance=script,
            user=request.user,
            data=script_data,
            request=NetBoxFakeRequest({
                        'META': {},
                        'POST': script_data,
                        'GET': {},
                        'FILES': {},
                        'user': request.user,
                        'path': '',
                        'id': uuid.uuid4()
                    }),
            commit=commit,
            schedule_at=DateUtils.now()+timedelta(seconds=1),
            job_timeout=script.python_class.job_timeout
        )



# =======================================================================
class UpdateSitesGroups(MerakiToolMixin, Script):

    class Meta: # pyright: ignore[reportIncompatibleVariableOverride]
        name = "Update Site Groups - multiple tasks"
        description = "Push infos for all sites to Meraki"
        commit_default = True
        job_timeout = 1800  # seconds. default: 300
        scheduling_enabled = True
    
    group = ObjectVar(
        model= SiteGroup, 
        query_params={
            'id': [ x for x in SiteGroup.objects.get(pk=11).get_descendants().values_list("id")]
        },
        required=True
    )

    details = BooleanVar(
    )

    def run(self, data, commit):

        self.checkIsStaff(self.request.user.username) 

        details:bool=SopUtils.extract_script_param(data, 'details', False)
        group:SiteGroup=SopUtils.extract_script_param(data, 'group',  (lambda x: SiteGroup.objects.get(id=x)))
        if group is None:
            raise AbortScript("Missing site parameter...")
        
        if details:
            self.log_debug(f"UpdateSitesGroups run : {data}")
      
        self.__meraki_connect(simulate=not(commit))

        sites:list[Site]=[]
        sites.extend(Site.objects.filter(group_id=group.id).filter(sopinfra__master_site=None))
        for sg in group.get_descendants():
            sites.extend(Site.objects.filter(group_id=sg.id).filter(sopinfra__master_site=None))
        if details:
            self.log_debug(f"group={group} / descendants={group.get_descendants()} / sites : {sites}")
            
        for site in sites:
            if SopInfraUtils.get_sopinfra_site_master_site_id(site) is not None:
                self.log_info(f"Site {site} is slave -> no need to update ")
            else:
                data={"site":site, "details":details, "commit":commit}
                job=_enqueue_site_update(self.request, data, commit)
                self.log_success(f"Queued UpdateOneSite for site [{site.name}]({site.get_absolute_url()}) : [{job.pk}]({job.get_absolute_url()})")


# =======================================================================
class UpdateSitesGroupsSingleThread(MerakiToolMixin, Script):

    class Meta: # pyright: ignore[reportIncompatibleVariableOverride]
        name = "Update Site Groups - singele threaded"
        description = "Push infos for all sites to Meraki"
        commit_default = True
        job_timeout = 1800  # seconds. default: 300
        scheduling_enabled = True

    group = ObjectVar(
        model= SiteGroup, 
        query_params={
            'id': [ x for x in SiteGroup.objects.get(pk=11).get_descendants().values_list("id")]
        },
        required=True
    )

    details = BooleanVar(
    )

    def run(self, data, commit):

        self.checkIsStaff(self.request.user.username) 

        details:bool=SopUtils.extract_script_param(data, 'details', False)
        group:SiteGroup=SopUtils.extract_script_param(data, 'group',  (lambda x: SiteGroup.objects.get(id=x)))
        if group is None:
            raise AbortScript("Missing site parameter...")
        
        self.__meraki_connect(simulate=not(commit))

        sites:list[Site]=[]
        sites.extend(Site.objects.filter(group_id=group.id).filter(sopinfra__master_site=None))
        for sg in group.get_descendants():
            sites.extend(Site.objects.filter(group_id=sg.id).filter(sopinfra__master_site=None))
        if details:
            self.log_debug(f"group={group} / descendants={group.get_descendants()} / sites : {sites}")

        for site in sites:
            if SopInfraUtils.get_sopinfra_site_master_site_id(site) is not None:
                self.log_info(f"Site {site} is slave -> no need to update ")
            else :
                self.enforce_one_netbox_site(site, details)

        self.log_info("Done !")
        MailUtils.send_simple_report_email(self) 

        if self.raiseError:
            raise AbortScript("Some Meraki dashboard update failed, please review the logs and fix issues.")


# =======================================================================
class UpdateSitesRegions(MerakiToolMixin, Script):

    class Meta: # pyright: ignore[reportIncompatibleVariableOverride]
        name = "Update Site Regions - multiple tasks"
        description = "Push infos for all sites in this region to Meraki"
        commit_default = True
        job_timeout = 1800  # seconds. default: 300
        scheduling_enabled = True
    
    region = ObjectVar(
        model= Region, 
        required=True
    )

    details = BooleanVar(
    )

    def run(self, data, commit):

        self.checkIsStaff(self.request.user.username) 

        details:bool=SopUtils.extract_script_param(data, 'details', False)
        region:Region=SopUtils.extract_script_param(data, 'region',  (lambda x: SiteGroup.objects.get(id=x)))
        if region is None:
            raise AbortScript("Missing site parameter...")
        
        self.__meraki_connect(simulate=not(commit))

        sites:list[Site]=[]
        sites.extend(Site.objects.filter(region_id=region.id).filter(sopinfra__master_site=None))
        for reg in region.get_descendants():
            sites.extend(Site.objects.filter(region_id=reg.id).filter(sopinfra__master_site=None))
        if details:
            self.log_debug(f"region={region} / descendants={region.get_descendants()} / sites : {sites}")
            
        for site in sites:
            if SopInfraUtils.get_sopinfra_site_master_site_id(site) is not None:
                self.log_info(f"Site {site} is slave -> no need to update ")
            else:
                data={"site":site, "details":details, "commit":commit}
                job=_enqueue_site_update(self.request, data, commit)
                self.log_success(f"Queued UpdateOneSite for site [{site.name}]({site.get_absolute_url()}) : [{job.pk}]({job.get_absolute_url()})")


class UpdateSitesRegionsSingleThread(MerakiToolMixin, Script):

    class Meta: # pyright: ignore[reportIncompatibleVariableOverride]
        name = "Update Site Regions - singele threaded"
        description = "Push infos for all sites in this region to Meraki"
        commit_default = True
        job_timeout = 1800  # seconds. default: 300
        scheduling_enabled = True

    region = ObjectVar(
        model= Region, 
        required=True
    )

    details = BooleanVar(
    )

    def run(self, data, commit):

        self.checkIsStaff(self.request.user.username) 

        details:bool=SopUtils.extract_script_param(data, 'details', False)
        region:Region=SopUtils.extract_script_param(data, 'region',  (lambda x: Region.objects.get(id=x)))
        if region is None:
            raise AbortScript("Missing site parameter...")
        
        self.__meraki_connect(simulate=not(commit))

        sites:list[Site]=[]
        sites.extend(Site.objects.filter(region_id=region.id).filter(sopinfra__master_site=None))
        for reg in region.get_descendants():
            sites.extend(Site.objects.filter(region_id=reg.id).filter(sopinfra__master_site=None))
        if details:
            self.log_debug(f"region={region} / descendants={region.get_descendants()} / sites : {sites}")

        for site in sites:
            if SopInfraUtils.get_sopinfra_site_master_site_id(site) is not None:
                self.log_info(f"Site {site} is slave -> no need to update ")
            else :
                self.enforce_one_netbox_site(site, details)

        self.log_info("Done !")
        MailUtils.send_simple_report_email(self) 

        if self.raiseError:
            raise AbortScript("Some Meraki dashboard update failed, please review the logs and fix issues.")


# =======================================================================

class UpdateOneSite(MerakiToolMixin, Script):

    class Meta: # pyright: ignore[reportIncompatibleVariableOverride]
        name = "Update One Site"
        description = "Push infos for a single site to Meraki"
        commit_default = True
        job_timeout = 120  # seconds. default: 300
        scheduling_enabled = False

    group = ObjectVar(
        model= SiteGroup, 
        query_params={
            'id': [ x for x in SiteGroup.objects.get(pk=11).get_descendants().values_list("id")]
        },
        required=True
    )

    site = ObjectVar(
        model=dcim.models.Site,
        description="The site you want to push updates for",
        required=True,
        query_params={
            'group_id': '$group'
        }
    )

    details = BooleanVar(
    )

    def run(self, data, commit):

        if self.request:
            self.checkHasGroups(self.request.user.username, ["ALL_ITA_Netbox_Team_Infrastructure", "ALL_ITA_Netbox_Team_Helpdesk"]) 

        site:Site=SopUtils.extract_script_param(data, 'site', None, (lambda x: Site.objects.get(id=x)))
        if site is None:
            raise AbortScript("Missing site parameter...")
        self.log_info(f"Args : site_id={site}")

        if SopInfraUtils.get_sopinfra_site_master_site_id(site) is not None:
            self.log_info(f"Site {site} is slave -> no need to update ")
            return 

        details:bool=SopUtils.extract_script_param(data, 'details', False)

        self.__meraki_connect(simulate=not(commit))
        
        self.enforce_one_netbox_site(site, details)

        self.log_info("Done !")
        MailUtils.send_simple_report_email(self) 

        if self.raiseError or self.failed:
            raise AbortScript("Some Meraki dashboard update failed, please review the logs and fix issues.")


class UpdateSelectedSites(MerakiToolMixin, Script):

    class Meta: # pyright: ignore[reportIncompatibleVariableOverride]
        name = "Update Selected Sites - multiple tasks"
        description = "Push infos for several sites to Meraki, enqueuing multiple one site tasks"
        commit_default = True
        job_timeout = 120  # seconds. default: 300
        scheduling_enabled = False


    group = ObjectVar(
        model= SiteGroup, 
        query_params={
            'id': [ x for x in SiteGroup.objects.get(pk=11).get_descendants().values_list("id")]
        },
        required=True
    )


    sites = MultiObjectVar(
        model=dcim.models.Site,
        description="Sites you want to push updates for",
        required=True,
        query_params={
            'group_id': '$group'
        }
    )

    details = BooleanVar(
    )

    def run(self, data, commit):

        self.checkIsStaff(self.request.user.username) 

        sites:Site=SopUtils.extract_script_param(data, 'sites', None)
        if sites is None or len(sites)==0:
            raise AbortScript("Missing site parameter...")
        details:bool=SopUtils.extract_script_param(data, 'details', False)

        if details:
            self.log_debug(f"UpdateSelectedSites run : {data}")

        for site in sites:
            if SopInfraUtils.get_sopinfra_site_master_site_id(site) is not None:
                self.log_info(f"Site {site} is slave -> no need to update ")
            else:
                data={"site":site, "details":details, "commit":commit}
                job=_enqueue_site_update(self.request, data, commit)
                self.log_success(f"Queued UpdateOneSite for site [{site.name}]({site.get_absolute_url()}) : [{job.pk}]({job.get_absolute_url()})")


class UpdateSelectedSitesSingleThread(MerakiToolMixin, Script):

    class Meta: # pyright: ignore[reportIncompatibleVariableOverride]
        name = "Update Selected Sites - singlethreaded"
        description = "Push infos for several sites to Meraki, one by one"
        commit_default = True
        job_timeout = 3600  # seconds. default: 300
        scheduling_enabled = False

    group = ObjectVar(
        model= SiteGroup, 
        query_params={
            'id': [ x for x in SiteGroup.objects.get(pk=11).get_descendants().values_list("id")]
        },
        required=True
    )

    sites = MultiObjectVar(
        model=dcim.models.Site,
        description="Sites you want to push updates for",
        required=True,
        query_params={
            'group_id': '$group'
        }
    )

    details = BooleanVar(
    )

    def run(self, data, commit):

        self.checkIsStaff(self.request.user.username) 

        details:bool=SopUtils.extract_script_param(data, 'details', False)
        sites:Site=SopUtils.extract_script_param(data, 'sites', None)
        if sites is None or len(sites)==0:
            raise AbortScript("Missing site parameter...")
        
        # Load meraki API keys from local json file
        
        self.__meraki_connect(simulate=not(commit))
        
        for site in sites:
            if SopInfraUtils.get_sopinfra_site_master_site_id(site) is not None:
                self.log_info(f"Site {site} is slave -> no need to update ")
            else:
                self.enforce_one_netbox_site(site, details)

        self.log_info("Done !")
        MailUtils.send_simple_report_email(self) 

        if self.raiseError:
            raise AbortScript("Some Meraki dashboard update failed, please review the logs and fix issues.")




# =======================================================================


class HubReport(MerakiToolMixin, Script):

    class Meta: # pyright: ignore[reportIncompatibleVariableOverride]
        name = "HubReport"
        description = "Builds a hub report"
        commit_default = False
        job_timeout = 600  # seconds. default: 300
        scheduling_enabled = False

    def run(self, data, commit):

        self.__meraki_connect(simulate=not(commit))
        
        all_net_mer=[]
        for org in self.__get_dash().organizations.getOrganizations():
            self.log_info(f"Scanning Meraki organizations : id {org['id']}")
            all_net_mer.extend(self.__get_dash().organizations.getOrganizationNetworks(org['id'], total_pages=-1))
        self.log_info("Meraki organization scan finished OK")        
        
        hubrep=[]
        for net in all_net_mer:
            if not("appliance" in net['productTypes']):
                self.log_info(f"No appliance in {net['name']}")    
                continue
            if len(self.__get_dash().organizations.getOrganizationDevices(organizationId=net['organizationId'], networkIds=[net['id']], productTypes=['appliance'])) <= 0  :
                self.log_info(f"No appliance in {net['name']}")    
                continue
            x=self.__get_dash().appliance.getNetworkApplianceVpnSiteToSiteVpn(net["id"])
            if x['mode']!='spoke':
                self.log_info(f"Not a spoke {net['name']}")
                continue    
            ok=True
            for y in x['hubs']:
                if ok and not(y['useDefaultRoute']):
                    ok=False
                    hubrep.append(net['name'])
                    self.log_warning(f"--> {net['name']} <-- NOT ALL DEFAULT ROUTES")
        return hubrep





