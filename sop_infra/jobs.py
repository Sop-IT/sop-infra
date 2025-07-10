import traceback, ldap

from django.conf import settings
from django.db.models import Count

from core.choices import JobIntervalChoices

from netbox.jobs import JobRunner, Job, system_job

from dcim.models import Site
from sop_infra.utils.ad_utils import ADCountersUpd, user_info, user_infos
from sop_infra.utils.mixins import JobRunnerLogMixin
from tenancy.models import Contact, Tenant

from sop_infra.models import SopMerakiUtils
from sop_infra.utils.sop_utils import  SopUtils


class SopMerakiCreateNetworkJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Refresh Meraki dashboards"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            SopMerakiUtils.create_meraki_networks(self, False, kwargs.pop('site'), kwargs.pop('details'))
        except Exception as e:
            stacktrace = traceback.format_exc()
            text="An exception occurred: "+ f"`{type(e).__name__}: {e}`\n```\n{stacktrace}\n```"
            self.log_failure(text)
            self.job.error = text
            raise
        finally:
            self.job.data = self.get_job_data()       

    @staticmethod
    def launch_manual(site:Site, details:bool=False)->Job:
        if settings.DEBUG:
            return SopMerakiCreateNetworkJob.enqueue(immediate=True, site=site, details=details)
        return SopMerakiCreateNetworkJob.enqueue(site=site, details=details)
    

@system_job(interval=JobIntervalChoices.INTERVAL_MINUTELY*10)
class SopMerakiDashRefreshJob(JobRunnerLogMixin, JobRunner):

    class Meta: # type: ignore
        name = "Refresh Meraki dashboards"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            SopMerakiUtils.refresh_dashboards(self, settings.DEBUG)
        except Exception as e:
            stacktrace = traceback.format_exc()
            text="An exception occurred: "+ f"`{type(e).__name__}: {e}`\n```\n{stacktrace}\n```"
            self.log_failure(text)
            self.job.error = text
            raise
        finally:
            self.job.data = self.get_job_data()       

    @staticmethod
    def launch_manual()->Job:
        if settings.DEBUG:
            return SopMerakiDashRefreshJob.enqueue(immediate=True)
        return SopMerakiDashRefreshJob.enqueue()
    

@system_job(interval=JobIntervalChoices.INTERVAL_HOURLY)
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

            self.log_info(f"Updating site users ....")
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
                        self.log_warning(f"  - {ct.name} ")
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
        finally:
            self.job.data = self.get_job_data()  


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
        
