import traceback, ldap

from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.db.models import Count

from netbox.jobs import JobRunner, Job, JobStatusChoices

from dcim.models import Site
from tenancy.models import Contact, Tenant
from extras.models import Notification

from sop_infra.models.sopmeraki import SopMerakiDash, SopMerakiNet, SopMerakiOrg

from sop_infra.utils.ad_utils import ADCountersUpd, user_info, user_infos
from sop_infra.utils.meraki_utils import SopMerakiUtils
from sop_infra.utils.mixins import JobRunnerLogMixin
from sop_infra.utils.meraki_tools import NetboxSiteMerakiUpdater
from sop_infra.utils.umbrella_utils import SopUmbrellaUtils


class SopMerakiCreateNetworkJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Refresh Meraki dashboards"

    def run(self, *args, **kwargs):
        SopMerakiUtils.create_meraki_networks(self, False, kwargs.pop('site'), kwargs.pop('details'))

    @staticmethod
    def launch_interactive(request, message:bool, site:Site, details:bool=False)->Job:
        job:Job=SopMerakiCreateNetworkJob.enqueue(user=request.user, immediate=True, site=site, details=details)
        if message:
            if job.status==JobStatusChoices.STATUS_COMPLETED:
                messages.success(request, f'Created Meraki Networks for site {site} !')
            else:
                messages.error(request, f'Failed to create Meraki Networks for site {site}, see logs for job #{job.pk} !')
        return job
    
    @staticmethod
    def launch_background(request, message:bool, site:Site, details:bool=False)->Job:    
        job:Job=SopMerakiCreateNetworkJob.enqueue(user=request.user, site=site, details=details)
        if message:
            messages.success(request, f'Started job #{job.pk} to create Meraki Networks for site {site} !')           
        return job
    



# --------------------------------------------------------------------------------------------------------
#region UMBRELLA JOBS

class SopMerakiLinkSiteToUmbrellaJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Link Meraki to Umbrella"

    def run(self, *args, **kwargs):
        #CHINA voir si spécifique à coder
        api_keys=SopUmbrellaUtils.get_legacy_api_key_for_dash_name('GLOBAL')
        SopMerakiUtils.connect_to_umbrella_dash(self, False, kwargs.pop('site'), api_keys, kwargs.pop('details'))

    @staticmethod
    def launch_interactive(request, message:bool, site:Site, details:bool=False)->Job:
        job:Job=SopMerakiLinkSiteToUmbrellaJob.enqueue(user=request.user, immediate=True, site=site, details=details)
        if message:
            if job.status==JobStatusChoices.STATUS_COMPLETED:
                messages.success(request, f'Linked site {site} to Umbrella !')
            else:
                messages.error(request, f'Failed to link site {site} to Umbrella, see logs for job #{job.pk} !')
        return job
    
    @staticmethod
    def launch_background(request, message:bool, site:Site, details:bool=False)->Job:    
        job:Job=SopMerakiLinkSiteToUmbrellaJob.enqueue(user=request.user, site=site, details=details)
        if message:
            messages.success(request, f'Started job #{job.pk} to link site {site} to Umbrella !')           
        return job
    

class SopMerakiEnableUmbrellaJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Enable Umbrella Protection"

    def run(self, *args, **kwargs):
        SopMerakiUtils.enable_umbrella_protection(self, False, kwargs.pop('site'), kwargs.pop('details'))   

    @staticmethod
    def launch_interactive(request, message:bool, site:Site, details:bool=False)->Job:
        job:Job=SopMerakiEnableUmbrellaJob.enqueue(user=request.user, immediate=True, site=site, details=details)
        if message:
            if job.status==JobStatusChoices.STATUS_COMPLETED:
                messages.success(request, f'Enabled Umbrella for site {site} !')
            else:
                messages.error(request, f'Failed to enable Umbrella protection for site {site}, see logs for job #{job.pk} !')
        return job
    
    @staticmethod
    def launch_background(request, message:bool, site:Site, details:bool=False)->Job:
        job:Job=SopMerakiEnableUmbrellaJob.enqueue(user=request.user, site=site, details=details)
        if message:
            messages.success(request, f'Started job #{job.pk} to enable Umbrella protection for site {site} !')           
        return job


#endregion


#region PULL FROM DASHBOARD
class SopMerakiDashRefreshJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Refresh Meraki dashboards"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            SopMerakiUtils.refresh_dashboards(self, settings.DEBUG, kwargs.pop('dashs', None), kwargs.pop('details', False))
        except Exception as e:
            stacktrace = traceback.format_exc()
            text="An exception occurred: "+ f"`{type(e).__name__}: {e}`\n```\n{stacktrace}\n```"
            self.log_failure(text)
            self.job.error = text
            raise
        # finally:
        #     self.job.data = self.get_job_data()       

    @staticmethod
    def launch_manual(dashs:list[SopMerakiDash], details:bool)->Job:
        if settings.DEBUG:
            return SopMerakiDashRefreshJob.enqueue(immediate=True, dashs=dashs, details=details)
        return SopMerakiDashRefreshJob.enqueue(dashs=dashs, details=details)


class SopMerakiOrgRefreshJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Refresh Meraki organisation"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            SopMerakiUtils.refresh_organizations(self, settings.DEBUG, kwargs.pop('orgs', None), kwargs.pop('details', False))
        except Exception as e:
            stacktrace = traceback.format_exc()
            text="An exception occurred: "+ f"`{type(e).__name__}: {e}`\n```\n{stacktrace}\n```"
            self.log_failure(text)
            self.job.error = text
            raise
        # finally:
        #     self.job.data = self.get_job_data()       

    @staticmethod
    def launch_manual(orgs:list[SopMerakiOrg], details:bool)->Job:
        if settings.DEBUG:
            return SopMerakiOrgRefreshJob.enqueue(immediate=True, orgs=orgs, details=details)
        return SopMerakiOrgRefreshJob.enqueue(orgs=orgs, details=details)


class SopMerakiNetRefreshJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Refresh Meraki network"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            nets=kwargs.pop('nets', None)
            details=kwargs.pop('details', False)
            SopMerakiUtils.refresh_networks(self, settings.DEBUG, nets, details)
        except Exception as e:
            stacktrace = traceback.format_exc()
            text="An exception occurred: "+ f"`{type(e).__name__}: {e}`\n```\n{stacktrace}\n```"
            self.log_failure(text)
            self.job.error = text
            raise
        # finally:
        #     self.job.data = self.get_job_data()       

    @staticmethod
    def launch_manual(nets:list[SopMerakiNet], details:bool)->Job:
        if settings.DEBUG:
            return SopMerakiNetRefreshJob.enqueue(immediate=True, nets=nets, details=details)
        return SopMerakiNetRefreshJob.enqueue(nets=nets, details=details)


class SopMerakiDashVpnStatusesJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Refresh Meraki VPN Statuses"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            SopMerakiUtils.vpnstatuses_dashboards(self, settings.DEBUG, kwargs.pop('dashs', None), kwargs.pop('details', False))
        except Exception as e:
            stacktrace = traceback.format_exc()
            text="An exception occurred: "+ f"`{type(e).__name__}: {e}`\n```\n{stacktrace}\n```"
            self.log_failure(text)
            self.job.error = text
            raise
        # finally:
        #     self.job.data = self.get_job_data()       

    @staticmethod
    def launch_manual(dashs:list[SopMerakiDash], details:bool)->Job:
        if settings.DEBUG:
            return SopMerakiDashVpnStatusesJob.enqueue(immediate=True, dashs=dashs, details=details)
        return SopMerakiDashVpnStatusesJob.enqueue(dashs=dashs, details=details)
    

class SopMerakiOrgVpnStatusesJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Refresh Meraki VPN Statuses"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            SopMerakiUtils.vpnstatuses_organizations(self, settings.DEBUG, kwargs.pop('orgs', None), kwargs.pop('details', False))
        except Exception as e:
            stacktrace = traceback.format_exc()
            text="An exception occurred: "+ f"`{type(e).__name__}: {e}`\n```\n{stacktrace}\n```"
            self.log_failure(text)
            self.job.error = text
            raise
        # finally:
        #     self.job.data = self.get_job_data()       

    @staticmethod
    def launch_manual(orgs:list[SopMerakiOrg], details:bool)->Job:
        if settings.DEBUG:
            return SopMerakiOrgVpnStatusesJob.enqueue(immediate=True, orgs=orgs, details=details)
        return SopMerakiOrgVpnStatusesJob.enqueue(orgs=orgs, details=details)





#endregion


#region PUSH TO DASHBOARD

class SopMerakiPushSiteJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Push configs to Meraki"

    def run(self, *args, **kwargs):
        site=kwargs.pop('site', None)
        details=kwargs.pop('details', False)
        simulate=kwargs.pop('simulate', False)
        NetboxSiteMerakiUpdater.push_to_meraki_dashboard(self, site, details, simulate)

    @staticmethod
    def launch_interactive(request, message:bool, site:Site, simulate:bool, details:bool=False)->Job:
        job:Job=SopMerakiPushSiteJob.enqueue(user=request.user, immediate=True, site=site, details=details, simulate=simulate)
        # url = reverse("core:job", args=[job.pk])
        if message:
            if job.status==JobStatusChoices.STATUS_COMPLETED:
                messages.success(request, f'Pushed {site} config to Meraki !')
            else:
                messages.error(request, f'Failed to push site {site} config to Meraki, see logs for job #{job.pk} !')
        return job
    
    @staticmethod
    def launch_background(request, message:bool, site:Site, simulate:bool, details:bool=False)->Job:    
        job:Job=SopMerakiPushSiteJob.enqueue(user=request.user, site=site, details=details, simulate=simulate)
        if message:
            messages.success(request, f'Started job #{job.pk} to link site {site} to Umbrella !')           
        return job
    
#endregion


#region AD SYNC

class SopSyncAdUsers(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Refresh AD Users"

    @staticmethod
    def launch_manual()->Job:
        if settings.DEBUG:
            return SopSyncAdUsers.enqueue(immediate=True)
        return SopSyncAdUsers.enqueue()


    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            # Only staff can run or schedule this script
            #self.checkIsStaff(self.request.user.username) 
            self.log_info(f"Starting global Netbox contacts update from AD")
            
            self.log_info(f"Connecting to LDAP server...")
            self.ldap_connect()

            self.log_info(f"Fetching UPN principals via LDAP...")
            self.ldap_fetch_upns()

            self.log_info(f"Preloading ISILOG site codes...")
            self.nb_load_isilog_codes()

            self.log_info(f"Preloading tenants domain names...")
            self.nb_load_tenants_domains() 

            self.log_info(f"Fetching LDAP users...")
            uinf = user_infos(self)
            self.ldap_fetch_users(uinf)

            self.log_info(f"Building AD user hierachy...")
            uinf.buildHierarchy()

            self.log_info(f"Fetching Netbox information to merge in...")
            uinf.enrichFromNetbox()
            
            self.log_info(f"Updating Netbox information...")
            uinf.pushNetboxUpdates()
            
            self.log_info(f"Marking deleted contacts in Netbox....")
            uinf.flagDeletedAccounts()

            self.log_info(f"Deactivating deleted users in Netbox....")
            uinf.deactivate_unknown_accounts()

            self.log_info(f"Updating site users counts ....")
            cnt_sit_upd=0
            sl:dict[int,ADCountersUpd]={}
            sits=Site.objects.all()
            # Prepare
            for s in sits:
                sl[s.pk]=ADCountersUpd(s)
            # Update direct user counts
            ucounts=Contact.objects.filter(custom_field_data__ad_acct_disabled=False)\
                .filter(custom_field_data__ad_acct_deleted=False)\
                .filter(custom_field_data__ad_objectsid__startswith="S")\
                .values('custom_field_data__ad_site_id','custom_field_data__ad_site_name','custom_field_data__ad_extAtt7')\
                .annotate(ucount=Count('custom_field_data__ad_samacct'))\
                .order_by()
            for uc in ucounts:
                sid=uc.get('custom_field_data__ad_site_id')
                sname=uc.get('custom_field_data__ad_site_name')
                t=uc.get('custom_field_data__ad_extAtt7')
                if t not in ['0','1','2']:
                    continue
                if sid is None:
                    self.log_warning(f"{uc.get('ucount')} AD  type {t} users assigned to inexistent NETBOX site (ISILOG=> «{sname}») :")
                    cts=Contact.objects.filter(custom_field_data__ad_acct_disabled=False)\
                        .filter(custom_field_data__ad_acct_deleted=False)\
                        .filter(custom_field_data__ad_extAtt7__iexact=t)\
                        .filter(custom_field_data__ad_objectsid__startswith="S")\
                        .filter(custom_field_data__ad_site_id=None)\
                        .filter(custom_field_data__ad_site_name=sname)
                    for ct in cts:
                        self.log_info(f"  - {ct.name} ")
                else:
                    sl.get(sid).update_direct(t, uc.get('ucount'))
            # Loop again to push to DB
            for s in sl.keys():
                cnt_sit_upd+=sl.get(s).push_to_db()

            self.log_success(f"AD sync actions recap :")
            self.log_success(f"  -> Updated {uinf.upd_cnt} contacts ")
            self.log_success(f"  -> Created {uinf.ins_cnt} contacts ")
            self.log_success(f"  -> Flagged {uinf.flg_cnt} contacts as deleted")
            self.log_success(f"  -> Deactivated  {uinf.flg_inact} users")
            self.log_success(f"  -> Updated  {cnt_sit_upd} sites")



            # Check for warnings
            if self.raiseWarning:
                self.log_warning("Some Netbox user updates have failed, please review the logs and fix issues.")
            if self.raiseError:
                self.log_failure("Some Netbox user updates have failed, please review the logs and fix issues.")
            self.log_success("Netbox refresh from AD done !")
            # SopUtils.send_simple_report_email(self)       


        except Exception:
            text=traceback.format_exc()
            self.failure(text)
            self.job.error = text
            raise
        # finally:
        #     self.job.data = self.get_job_data()  


    ldap_basedn = "DC=ad,DC=soprema,DC=com"
    #TODO init via recherche d'enregistrements SRV
    ldap_servers = "10.0.8.1"
    ldap_conn = None
    ldap_username = "CN=sa-netbox-ro,OU=Service Account,OU=Europe,OU=SopUsers,DC=ad,DC=soprema,DC=com"
    ldap_password = "H*Py5WKA#MRXaebZZT4CPHXW**AD8XA!SRa5b#zXBKAnwa"
    ldap_upns = None
    isi_codes = None


    def ldap_clean(self):
        try:
            self.ldap_conn.unbind_s()    
        finally:
            self.ldap_conn=None

    def ldap_connect(self):
        if self.ldap_conn is not None:
            raise Exception("LDAP connection is not None !")
        self.ldap_conn = ldap.initialize('ldap://' + self.ldap_servers)
        self.ldap_conn.protocol_version = 3
        self.ldap_conn.set_option(ldap.OPT_REFERRALS, 0)    
        self.ldap_conn.simple_bind_s(self.ldap_username, self.ldap_password)

    def ldap_fetch_users(self, uinf:user_infos):
        if self.ldap_conn is None:
            raise Exception("Not connected !")
        results = self.ldap_conn.search_ext_s(self.ldap_basedn,ldap.SCOPE_SUBTREE,"(&(objectClass=user)(objectClass=person)(objectCategory=CN=Person,CN=Schema,CN=Configuration,DC=ad,DC=soprema,DC=com))", user_info.attrList)
        cnt=0
        tcnt=0
        lst_ous=["OU=Users","OU=Guests","OU=Administrators","OU=External"]
        for dn,entry in results:
            if dn is not None :
                tcnt+=1
                dnspl=dn.split(',')
                #self.log_debug(f"Handling user {dn} -> {dnspl[1]}")
                if dnspl[1] in lst_ous:
                    uinf.addUserFlat(dn, entry)
                    cnt+=1
            #else:
            #    self.log_info(f"No dn for entry {entry}, skipping.")
        self.log_info(f"  --> {cnt}/{tcnt} AD users fetched")

    def ldap_fetch_upns(self):
        if self.ldap_conn is None:
            raise  Exception("Not connected !")
        results=self.ldap_conn.search_s("CN=Partitions,CN=Configuration,"+self.ldap_basedn,ldap.SCOPE_BASE)
        self.ldap_upns=[]
        dn,entry=results[0]
        for upn in entry["uPNSuffixes"]:
            self.ldap_upns.append(upn.decode('utf-8').lower())
        self.log_info(f"  --> {len(self.ldap_upns)} UPN domains found")

    def nb_load_isilog_codes(self):
        self.isi_codes={}
        for s in Site.objects.all():
            if s.sopinfra is not None :
                c=s.sopinfra.isilog_code
                if c is not None:
                    c=c.strip()
                    if c!="":
                        self.isi_codes[c]=s.pk 
        self.log_info(f"  --> {len(self.isi_codes.keys())} ISILOG codes loaded")

    def nb_load_tenants_domains(self):
        self.tenant_nonO365_domain_names={}
        for s in Tenant.objects.all():
            c=s.custom_field_data.get('tenant_nonO365_domain_names')
            if c is not None:
                for dns in c:
                    self.tenant_nonO365_domain_names[dns.lower()]=s
        self.log_info(f"  --> {len(self.tenant_nonO365_domain_names.keys())} domains loaded")
        
#endregion