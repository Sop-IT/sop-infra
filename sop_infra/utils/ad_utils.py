import struct, re, ldap

from sop_infra.utils.sop_utils import DateUtils, NetboxUtils
from django.core.exceptions import ValidationError

from dcim.models import Site
from users.models import User
from tenancy.models import Contact


def convertSid(binary):
    version = struct.unpack("B", binary[0:1])[0]
    # I do not know how to treat version != 1 (it does not exist yet)
    assert version == 1, version
    length = struct.unpack("B", binary[1:2])[0]
    authority = struct.unpack(b">Q", b"\x00\x00" + binary[2:8])[0]
    string = "S-%d-%d" % (version, authority)
    binary = binary[8:]
    assert len(binary) == 4 * length
    for i in range(length):
        value = struct.unpack("<L", binary[4 * i : 4 * (i + 1)])[0]
        string += "-%d" % value
    return string


# =======================================================================


class user_info:

    dz = re.compile(r"^00[0.]*")
    mp = re.compile(r"\.\.+")
    forb = re.compile(r"[^0-9+.,*#]")
    area = re.compile(r"\(([0-9]+)\)")
    ctxt = r"\+(9[976]\d|8[987530]\d|6[987]\d|5[90]\d|42\d|3[875]\d|2[98654321]\d|9[8543210]|8[6421]|6[6543210]|5[87654321]|4[987654310]|3[9643210]|2[70]|7|1)"
    country = re.compile(ctxt)
    phoneFmt = re.compile(ctxt + r"\.[0-9.,*#]+$")
    defaultPhone = ""
    attrList = [
        "c",
        "sAMAccountName",
        "description",
        "manager",
        "extensionAttribute6",
        "proxyAddresses",
        "mail",
        "mobile",
        "userAccountControl",
        "objectSid",
        "title",
        "displayName",
        "userPrincipalName",
        "mobile",
        "telephoneNumber",
        "extensionAttribute7",
        "extensionAttribute8",
    ]

    def __init__(self, adtool, dn, entry):
        self.nb_mgr_id = None
        self.ad_site_id = None
        self.nb_usr_id = None
        self.adtool = adtool
        self.ad_dn = dn
        self.block_push = False
        self.collabs = []
        self.ad_emails = []
        self.ad_acctDeleted = False
        self.ad_sid = convertSid(entry["objectSid"][0])
        self.fill_in_ad_name(entry)
        self.ad_upn = self.read_single_value(entry, "userPrincipalName")
        self.ad_country = self.read_single_value(entry, "c")
        self.fill_in_emails(entry)
        self.fill_in_ad_site(entry)
        self.ad_manager_dn = self.read_single_value(entry, "manager")
        self.ad_extAtt6 = self.read_single_value(entry, "extensionAttribute6")
        self.ad_title = self.read_single_value(entry, "title")
        self.fill_in_phone(entry)
        self.ad_extAtt7 = self.read_single_value(entry, "extensionAttribute7")
        if self.ad_extAtt7 == "":
            self.ad_extAtt7 = "empty"

    def append_email(self, email):
        email = email.lower()
        if not (email in self.ad_emails):
            self.ad_emails.append(email)

    def fill_in_emails(self, entry):

        # Fetch main AD email
        self.ad_mail = self.read_single_value(entry, "mail")
        # Check if the mail is valid
        smpMail = self.ad_mail.lower()
        m = re.match(r"^\s*(([^@]+)@([^@]+))\s*$", smpMail)
        if m and m.group(3) != "ad.soprema.com":
            smpMail = m.group(1)
            self.append_email(smpMail)
        else:
            # Empty or invalid  or internal email
            if len(smpMail.strip()) > 0 and m and m.group(3) != "ad.soprema.com":
                self.adtool.log_warning(
                    f"AD email inconsitency found for user {self.ad_samacc} : invalid AD 'mail' attribute {smpMail} "
                )
            # try via the isilog email attribute
            smpMail = self.read_single_value(entry, "extensionAttribute8").lower()
            m = re.match(r"^\s*(([^@]+)@([^@]+))\s*$", smpMail)
            if m and m.group(3) != "ad.soprema.com":
                smpMail = m.group(1)
                self.append_email(smpMail)
            else:
                # Empty or invalid  or internal email
                if len(smpMail.strip()) > 0 and m and m.group(3) != "ad.soprema.com":
                    self.adtool.log_warning(
                        f"AD email inconsitency found for user {self.ad_samacc} : invalid AD 'extensionAttribute8' attribute {smpMail} "
                    )
                smpMail = None
        self.match_email = smpMail

        # CHECK IF THIS MAIL IS IN INTEGRATION
        if self.match_email is not None:
            # rely on m being the last regex matched
            if m.group(3).lower() in self.adtool.tenant_nonO365_domain_names.keys(): # type: ignore
                self.block_push = True
                self.nb_name_push = f"{self.ad_name} (--NOT YET-- {self.ad_samacc})"

        # Now handle the proxyAddresses
        self.ad_emails = []
        prxMail = []
        mainPrx = None
        if "proxyAddresses" in entry.keys():
            for s in entry["proxyAddresses"]:
                p = s.decode("utf-8")
                m = re.match("^smtp:(.+@(.+))$", p.lower())
                if m and m.group(2) != "ad.soprema.com":
                    prxMail.append(m.group(1))
                    self.append_email(m.group(1))
                    m = re.match("^SMTP:(.+@.+)$", p)
                    if m:
                        if mainPrx is not None:
                            # self.adtool.log_warning(f"AD email inconsitency found for user {self.ad_samacc} : several main proxyAdresses ")
                            pass
                        mainPrx = m.group(1).lower()
        if self.match_email is not None:
            if len(prxMail) > 0 and self.match_email not in prxMail:
                # self.adtool.log_warning(f"AD email inconsitency found for user {self.ad_samacc} : short email '{self.match_email}' not in proxies ({prxMail})")
                pass
        elif mainPrx is not None:
            # self.adtool.log_warning(f"AD email inconsitency found for user {self.ad_samacc} : main proxy '{prxMail}' exists without short mail")
            pass
        elif len(prxMail) > 0:
            # self.adtool.log_warning(f"AD email inconsitency found for user {self.ad_samacc} : No main proxy address and no short email (proxy={prxMail}) ")
            pass

    pcc = {
        "FR": 33,
        "US": 1,
        "CA": 1,
        "ES": 34,
        "NL": 31,
        "DE": 49,
        "IT": 39,
        "BE": 32,
        "PL": 48,
        "TR": 90,
        "BR": 56,
        "RO": 40,
        "PT": 351,
        "UK": 44,
        "CH": 41,
        "CZ": 42,
        "AE": 971,
    }

    def fill_in_phone(self, entry):
        # read proper fields
        self.ad_mobile = self.read_phone_number(entry, "mobile")
        self.ad_telephone_number = self.read_phone_number(entry, "telephoneNumber")
        # load our work field
        self.ad_phone = self.ad_mobile
        if self.ad_phone is None or self.ad_phone.strip() in ["", "_"]:
            self.ad_phone = self.ad_telephone_number
        if self.ad_phone is None or self.ad_phone.strip() in ["", "_"]:
            self.ad_phone = self.defaultPhone
            return
        # Try to match or cleanup the number
        m = self.phoneFmt.match(self.ad_phone)
        if not m:
            p = self.ad_phone
            # start by replacing the useless (0) with a point
            p = p.replace("(0)", ".")
            # then extract area codes (156)
            p = self.area.sub(r".\1.", p)
            # then replace leading double zeros with a '+' (allow more than 2 zeroes + points)
            p = self.dz.sub("+", p)
            # then replace any forbidden chars with a point
            p = self.forb.sub(".", p)
            # separate country code from the rest with a point
            p = self.country.sub(r"+\1.", p)
            # try to guess phone country code from the user country
            m = re.match("^0(.*)$", p)
            if m:
                # TODO map via countries in Netbox
                # TODO handle AD aliases in NB (eg : UK vs GB)
                if self.ad_country is None or "" == self.ad_country:
                    pass
                else:
                    x = self.pcc.get(self.ad_country)
                    if x is not None:
                        p = f"+{x}.{m.group(1)}"
                    else:
                        self.adtool.log_debug(
                            f"Missing phone country : {self.ad_country}"
                        )
            # finish with 2 points or more that end up being one point
            p = self.mp.sub(".", p)
            # return if we're good !
            m = self.phoneFmt.match(p)
            if m:
                self.ad_phone = p
                return

            # Log not good and fall back
            # self.adtool.log_debug(f"Couldn't fix the phone number for {self.ad_samacc} : {self.ad_country} -- {self.ad_phone} -> {p}")
            self.ad_phone = self.defaultPhone

    def fill_in_ad_name(self, entry):
        self.ad_samacc = self.read_single_value(entry, "sAMAccountName")
        self.ad_name = self.read_single_value(entry, "displayName")
        self.ad_userAccountControl = self.read_integer_value(
            entry, "userAccountControl", 2
        )
        self.ad_acctDisabled = (self.ad_userAccountControl & 2) == 2
        if self.ad_acctDisabled:
            self.nb_name_push = f"--DISABLED-- {self.ad_name} ({self.ad_samacc})"
        else:
            self.nb_name_push = f"{self.ad_name} ({self.ad_samacc})"

    def fill_in_ad_site(self, entry):
        # The ISILOG site code for the user is stored in the description field
        self.ad_site_name = self.read_single_value(entry, "description")
        # Rough format check
        m = re.match("^[A-Z]{2}-[A-Z]+-[A-Z]{3,4}$", self.ad_site_name)
        if not m:
            return
        # Use preloaded ISILOG site codes to avoid Netbox lookups
        if self.ad_site_name in self.adtool.isi_codes.keys():
            self.ad_site_id = self.adtool.isi_codes[self.ad_site_name]

    def read_integer_value(self, entry, key: str, defval: int = 0) -> int:
        if key in entry.keys():
            # print (f'{self.read_single_value(entry, "sAMAccountName")} -> {entry[key][0]} / {entry[key][0].decode("utf-8")} / big : {int.from_bytes(entry[key][0], "big")} / little : {int.from_bytes(entry[key][0], "little")}')
            # print(f'{ int(self.read_single_value(entry, key))}')
            return int(self.read_single_value(entry, key))
        return defval

    def read_single_value(self, entry, key, defval: str = ""):
        if key in entry.keys():
            return entry[key][0].decode("utf-8").strip()
        return defval

    def read_phone_number(self, entry, key):
        x = self.read_single_value(entry, key)
        return x.replace(" ", ".")

    def enrichFromNetbox(self, nbct):
        # if self.ad_samacc=="tstucki":
        #    self.adtool.log_debug(f"self : {vars(self)} - nbct : {vars(nbct)}")
        self.nb_contact = nbct
        self.nb_usr_id = nbct.id
        self.nb_email = nbct.email
        self.nb_name = nbct.name
        self.nb_title = nbct.title
        self.nb_phone = nbct.phone

    def copyToNetbox(self, nd):
        nd.custom_field_data["ad_last_refresh"] = DateUtils.fmt_date(DateUtils.now())
        nd.custom_field_data["ad_objectsid"] = self.ad_sid
        nd.custom_field_data["ad_samacct"] = self.ad_samacc
        nd.custom_field_data["ad_acct_disabled"] = self.ad_acctDisabled
        nd.custom_field_data["ad_acct_deleted"] = self.ad_acctDeleted
        nd.custom_field_data["ad_user_acct_ctrl"] = self.ad_userAccountControl
        nd.custom_field_data["ad_manager"] = self.nb_mgr_id
        nd.custom_field_data["ad_manager_dn"] = self.ad_manager_dn
        nd.custom_field_data["ad_upn"] = self.ad_upn
        nd.custom_field_data["ad_mail"] = self.ad_mail
        nd.custom_field_data["ad_proxyadd"] = self.ad_emails
        nd.custom_field_data["ad_site_name"] = self.ad_site_name
        nd.custom_field_data["ad_site_id"] = self.ad_site_id
        nd.custom_field_data["ad_mobile"] = self.ad_mobile
        nd.custom_field_data["ad_telephone_number"] = self.ad_telephone_number
        nd.custom_field_data["ad_country"] = self.ad_country
        nd.custom_field_data["ad_extAtt6"] = self.ad_extAtt6
        nd.custom_field_data["ad_extAtt7"] = self.ad_extAtt7
        nd.title = self.ad_title
        nd.name = self.nb_name_push
        nd.phone = self.ad_phone
        nd.email = self.match_email

    def preCopyCleanup(self):
        # Cleanup title
        self.ad_title = self.ad_title.strip()
        if len(self.ad_title) > 100:
            self.ad_title = self.ad_title[0:99]
        # Cleanup email TODO faire mieux
        m = re.match("^.+@.+$", f"{self.match_email}")
        if not m:
            self.match_email = None

    def needsUpdate(self):
        if self.block_push:
            return False
        if self.needsCreation():
            return False
        if not self.hasValidName():
            return False
        if (
            self.compareCF("ad_objectsid", self.ad_sid)
            or self.compareCF("ad_upn", self.ad_upn)
            or self.compareCF("ad_samacct", self.ad_samacc)
            or self.compareCF("ad_acct_disabled", self.ad_acctDisabled)
            or self.compareCF("ad_acct_deleted", self.ad_acctDeleted)
            or self.compareCF("ad_user_acct_ctrl", self.ad_userAccountControl)
            or self.compareCF("ad_manager", self.nb_mgr_id)
            or self.compareCF("ad_manager_dn", self.ad_manager_dn)
            or self.compareCF("ad_mobile", self.ad_mobile)
            or self.compareCF("ad_telephone_number", self.ad_telephone_number)
            or self.compareCF("ad_site_name", self.ad_site_name)
            or self.compareCF("ad_site_id", self.ad_site_id)
            or self.compareCF("ad_country", self.ad_country)
            or self.compareCF("ad_mail", self.ad_mail)
            or self.compareCF("ad_extAtt6", self.ad_extAtt6)
            or self.compareCF("ad_extAtt7", self.ad_extAtt7)
            or False
        ):
            return True
        # TODO        nd.custom_field_data['ad_proxyadd'] = self.ad_emails ?
        elif self.nb_title != self.ad_title:
            return True
        elif self.nb_name != self.nb_name_push:
            return True
        elif self.nb_phone != self.ad_phone:
            return True
        elif f"{self.nb_email}" != self.match_email:
            return True
        return False

    def compareCF(self, name, value):
        return (
            not (name in self.nb_contact.custom_field_data.keys())
            or self.nb_contact.custom_field_data[name] != value
        )

    def needsCreation(self):
        if self.block_push:
            return False
        return self.nb_usr_id is None and self.hasValidName()

    def hasValidName(self):
        if self.nb_name_push is None:
            return False
        if self.nb_name_push.strip() == "":
            return False
        return True


class user_infos:

    def __init__(self, adtool):
        self.adtool = adtool
        self.email_flat = {}
        self.dns_flat = {}
        self.sids_flat = {}
        self.sams_flat = {}
        self.users_hier = {}
        self.dupmails = []
        self.del_acct = {}
        self.upd_cnt = 0
        self.ins_cnt = 0
        self.flg_cnt = 0
        # self.upd_sams=[]
        # self.ins_sams=[]

    def addUserFlat(self, dn, entry):
        # self.adtool.log_debug(f"{entry.keys()}")
        inf = user_info(self.adtool, dn, entry)
        # Do not consider entries without email addresses
        if inf.match_email is None or inf.match_email == "None":
            return
        # Flag duplicates
        if inf.match_email in self.dupmails:
            self.adtool.log_failure(
                f"Another duplicate email for user '{inf.ad_samacc}' with duplicate email '{inf.match_email}'"
            )
        elif inf.match_email in self.email_flat.keys():
            dup = self.email_flat[inf.match_email]
            self.adtool.log_failure(
                f"Duplicate email detection for '{inf.ad_samacc}' and '{dup.ad_samacc}' :  '{inf.match_email}'"
            )
            self.dupmails.append(inf.match_email)
        else:
            self.email_flat[inf.match_email] = inf
        self.dns_flat[dn] = inf
        self.sids_flat[inf.ad_sid] = inf
        self.sams_flat[inf.ad_samacc] = inf

    def buildHierarchy(self):
        keys = self.sams_flat.keys()
        dns = self.dns_flat.keys()
        for k in keys:
            us: user_info = self.sams_flat[k]
            # Fix missing ext6 when AD manager is known
            if us.ad_extAtt6 is None or us.ad_extAtt6 == "":
                if us.ad_manager_dn is not None and us.ad_manager_dn in dns:
                    us.ad_extAtt6 = self.dns_flat[us.ad_manager_dn].ad_samacc
            # Build this users hierarchy
            if us.ad_extAtt6 is None or us.ad_extAtt6 == "":
                self.users_hier[us.ad_samacc] = us
            elif us.ad_extAtt6 == us.ad_samacc:
                self.users_hier[us.ad_samacc] = us
                # if us.ad_samacc!="peb":
                #    self.adtool.log_warning(f"User '{us.ad_samacc}/{us.ad_dn}' is his/her own manager ! ")
                #    self.adtool.raiseWarning=True
            elif us.ad_extAtt6 in keys:
                mgr = self.sams_flat[us.ad_extAtt6]
                mgr.collabs.append(us)
            else:
                # self.adtool.log_warning(f"Manager not found '{us.ad_extAtt6}' for user '{us.ad_samacc}/{us.ad_dn}' ! ")
                # self.adtool.raiseWarning=True
                self.users_hier[us.ad_samacc] = us

    def enrichFromNetbox(self):
        nbcts = Contact.objects.all()
        for nbct in nbcts:
            self.enrichOneFromNetbox(nbct)

    def enrichOneFromNetbox(self, nbct):
        # try to match via SID
        x = nbct.custom_field_data["ad_objectsid"]
        if x is not None and x.strip() != "":
            if x in self.sids_flat.keys():
                # self.adtool.log_debug(f"Enriching user {self.sids_flat[nbct.custom_field_data['ad_objectsid']].ad_samacc} via SID")
                self.sids_flat[nbct.custom_field_data["ad_objectsid"]].enrichFromNetbox(
                    nbct
                )
            else:
                self.del_acct[nbct.id] = nbct
            return
        # try to match via SAM
        x = nbct.custom_field_data["ad_samacct"]
        if x is not None and x.strip() != "":
            if x in self.sams_flat.keys():
                # self.adtool.log_debug(f"Enriching user {self.sams_flat[nbct.custom_field_data['ad_samacct']].ad_samacc} via SAM")
                self.sams_flat[nbct.custom_field_data["ad_samacct"]].enrichFromNetbox(
                    nbct
                )
            else:
                self.del_acct[nbct.id] = nbct
            return
        # try to match via AD emails
        email = nbct.email.lower()
        m = re.match("^(.+@(.+))$", email)
        if m:
            # self.adtool.log_debug(f"Enriching user via mail {email}")
            # check if there where no dupplicates
            if email in self.dupmails:
                return
            # Try match via the main email
            if email in self.email_flat.keys():
                self.email_flat[email].enrichFromNetbox(nbct)
            # IF not matched but was in our UPNs, should be flagged as deleted
            elif m.group(2) in self.adtool.ldap_upns:
                # BUT only if it doesn't exist in tenants domains that are not yet in 0365
                if m.group(2) in self.adtool.tenant_nonO365_domain_names.keys():
                    self.adtool.log_debug(
                        f"  Skipping user {nbct.name} from enrichment because of tenant domain status"
                    )
                    pass
                else:
                    self.del_acct[nbct.id] = nbct
            return

    max_upd = None

    def pushNetboxUpdates(self):
        keys = self.users_hier.keys()
        for k in keys:
            usr: user_info = self.sams_flat[k]
            self.recursivePushUpdates(usr)
            if self.max_upd is not None and self.upd_cnt > self.max_upd:
                return

    def recursivePushUpdates(self, usr: user_info):
        usr.preCopyCleanup()
        usr_id = usr.nb_usr_id
        if self.max_upd is not None and self.upd_cnt > self.max_upd:
            return
        if usr.needsUpdate():
            try:
                nd = usr.nb_contact
                if nd.pk and hasattr(nd, "snapshot"):
                    nd.snapshot()
                usr.copyToNetbox(nd)
                nd.full_clean()
                nd.save()
                self.upd_cnt = self.upd_cnt + 1
                # self.upd_sams.append(usr.ad_samacc)
                self.adtool.log_info(f"  Updated contact {nd.id} - {nd.name}")
            except ValidationError as valerr:
                self.adtool.log_failure(
                    f"Contact update validation error on {usr.ad_samacc} : {valerr}"
                )
                self.adtool.log_failure(
                    f"Current object :  {usr.ad_samacc} -> {vars(usr)} "
                )
            except Exception as err:
                self.adtool.log_failure(f"Contact update failure : {err}")
                self.adtool.log_failure(
                    f"Current object :  {usr.ad_samacc} -> {vars(usr)}  "
                )
                raise err
        elif usr.needsCreation():
            try:
                nd = Contact(name=usr.nb_name_push)
                usr.copyToNetbox(nd)
                nd.full_clean()
                nd.save()
                usr_id = Contact.objects.filter(name=usr.nb_name_push)[0].pk
                self.ins_cnt = self.ins_cnt + 1
                # self.inc_sams.append(usr.ad_samacc)
                self.adtool.log_info(f"  Created contact {nd.pk} - {nd.name}")
            except ValidationError as valerr:
                self.adtool.log_failure(
                    f"Contact creation validation error  on {usr.ad_samacc} : {valerr}"
                )
                self.adtool.log_failure(
                    f"Current object :  {usr.ad_samacc} -> {vars(usr)} "
                )
            except Exception as err:
                self.adtool.log_failure(f"Contact creation failure : {err}")
                self.adtool.log_failure(
                    f"Current object :  {usr.ad_samacc} -> {vars(usr)} "
                )
                raise err
        for c in usr.collabs:
            c.nb_mgr_id = usr_id
            self.recursivePushUpdates(c)

    # UPDATE NETBOX TO MARK ACCOUNT NOT FOUND ANYMORE IN AD AS BEING DELETED
    def flagDeletedAccounts(self):
        self.flg_cnt = 0
        for k in self.del_acct.keys():
            nd: Contact = self.del_acct[k]
            try:
                upd = False
                if nd.pk and hasattr(nd, "snapshot"):
                    nd.snapshot()
                if nd.custom_field_data["ad_objectsid"]:
                    if (not "ad_acct_disabled" in nd.custom_field_data.keys()) or (
                        not nd.custom_field_data["ad_acct_disabled"]
                    ):
                        nd.custom_field_data["ad_acct_disabled"] = True
                        # print("upd dis")
                        upd = True
                    if (not "ad_acct_deleted" in nd.custom_field_data.keys()) or (
                        not nd.custom_field_data["ad_acct_deleted"]
                    ):
                        nd.custom_field_data["ad_acct_deleted"] = True
                        # print("upd del")
                        upd = True
                # Cleanup phone number
                m = re.match("^\\+(1|[2-9][0-9]{1,2})\\.[0-9.]+$", nd.phone)
                if not m:
                    if "+33.3.88.79.85.55" != nd.phone:
                        nd.phone = "+33.3.88.79.85.55"
                        # print("upd phone")
                        upd = True
                # Cleanup email TODO faire mieux
                m = re.match("^.+@.+$", f"{nd.email}")
                if not m:
                    if "helpdesk@soprema.com" != nd.email:
                        nd.email = "helpdesk@soprema.com"
                        # print("upd mail")
                        upd = True
                # cleanup name
                m = re.match("^--[^-]+-- (.*)$", nd.name)
                tar = f"--DELETED-- {nd.name}"
                if m:
                    tar = f"--DELETED-- {m.group(1).strip()}"
                if tar != nd.name:
                    nd.name = tar
                    # print("upd tar")
                    upd = True
                # Clean and save
                if upd:
                    self.flg_cnt = self.flg_cnt + 1
                    self.adtool.log_info(
                        f"  Flag contact {nd.pk} - {nd.name} as deleted"
                    )
                    nd.full_clean()
                    nd.save()
            except ValidationError as valerr:
                self.adtool.log_failure(
                    f"Flag contact as deleted - validation error on {nd.pk} - {nd.name} : {valerr}"
                )
                self.adtool.log_failure(
                    f"Current object :  {nd.pk} - {nd.name} -> {vars(nd)} "
                )
            except Exception as err:
                self.adtool.log_failure(f"Flag contact as deleted - failure : {err}")
                self.adtool.log_failure(
                    f"Current object :  {nd.pk} - {nd.name} -> {vars(nd)}  "
                )
                raise err

    # UPDATE NETBOX TO INACTIVATE ACCOUNTS THAT ARE NOT FOUND IN THE CONTACTS
    def deactivate_unknown_accounts(self):
        self.flg_inact = 0
        valCts: list[str] = []
        for s in (
            Contact.objects.exclude(custom_field_data__ad_samacct=None)
            .filter(custom_field_data__ad_acct_disabled=False)
            .values_list("custom_field_data__ad_samacct", flat=True)
        ):
            valCts.append(f"{s}")
        usrs = (
            User.objects.exclude(is_staff=True)
            .exclude(username="admin")
            .exclude(username="abrand-tst")
            .filter(is_active=True)
            .exclude(username__in=valCts)
        )
        for nd in usrs:
            try:
                upd = False
                if nd.pk and hasattr(nd, "snapshot"):
                    nd.snapshot()  # type: ignore
                nd.is_active = False
                self.flg_inact = self.flg_inact + 1
                self.adtool.log_info(f"  Deactivate user {nd.pk} - {nd.username}")
                nd.full_clean()
                nd.save()
            except ValidationError as valerr:
                self.adtool.log_failure(
                    f"Deactivate user - validation error on {nd.pk} - {nd.username} : {valerr}"
                )
                self.adtool.log_failure(
                    f"Current object :  {nd.pk} - {nd.username} -> {vars(nd)} "
                )
            except Exception as err:
                self.adtool.log_failure(f"Deactivate user - failure : {err}")
                self.adtool.log_failure(
                    f"Current object :  {nd.pk} - {nd.username} -> {vars(nd)}  "
                )
                raise err


class ADCountersUpd:
    def __init__(self, site: Site):
        self.slug = site.slug
        self.direct_wc = 0
        self.direct_bc = 0
        self.direct_ext = 0
        self.direct_nom = 0
        self.site = site

    def update_direct(self, t: str, nb: int):
        if nb is None or nb < 0:
            nb = 0
        if t not in ["0", "1", "2"]:
            raise Exception(f"unsupported user type {t}")
        if t == "0":
            self.direct_wc = nb
        elif t == "1":
            self.direct_bc = nb
        elif t == "2":
            self.direct_ext = nb

    # Push to DB
    def push_to_db(self) -> int:
        site = self.site
        sopinfra = NetboxUtils.get_site_sopinfra(site)
        if sopinfra is None:
            return 0
        if (
            self.direct_wc != sopinfra.ad_direct_users_wc
            or self.direct_bc != sopinfra.ad_direct_users_bc
            or self.direct_ext != sopinfra.ad_direct_users_ext
            or self.direct_nom != sopinfra.ad_direct_users_nom
        ):
            sopinfra.snapshot()
            sopinfra.ad_direct_users_wc = self.direct_wc
            sopinfra.ad_direct_users_bc = self.direct_bc
            sopinfra.ad_direct_users_ext = self.direct_ext
            sopinfra.ad_direct_users_nom = self.direct_nom
            sopinfra.full_clean()
            sopinfra.save()
            return 1
        return 0

