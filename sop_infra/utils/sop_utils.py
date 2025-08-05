import re, json, dateutil, smtplib

from django.http import HttpRequest
from requests import Session
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from django.core.cache import cache

from django.contrib import messages
from django.conf import settings

from netbox.config import get_config
from netbox.context import current_request

from utilities.exceptions import AbortScript
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from users.models import User
from dcim.models import Site

from extras.scripts import Script
from extras.reports import Report

from sop_infra.models import SopInfra

from utilities.permissions import get_permission_for_model

class SopRegExps:
    date_str = r"20[0-2][0-9]-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])"
    # TODO: trouver une lib pour récupérer la "vraie" liste de codes ISO3166 !
    iso3166a2_str = r"[A-Z][A-Z]"
    iso3166a2_re = re.compile(iso3166a2_str)
    meraki_sitename_str = r"^.*--(?:(STOCK-.*|[^ -]+)(|[ -]+[oO][lL][dD].*|[ -].*))$"
    meraki_sitename_re = re.compile(meraki_sitename_str)
    ip4_octet_str = r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])"
    ip4_str = r"%s(?:\.%s){3}" % (ip4_octet_str, ip4_octet_str)
    ip4_re = re.compile(ip4_str)
    one_ip4_str = r"^(" + ip4_str + r")$"
    mac_octet_str = r"(?:[0-9a-fA-F]{2})"
    mac_str = r"(?:%s:){5}%s" % (mac_octet_str, mac_octet_str)
    mac_re = re.compile(mac_str)
    one_mac_str = r"^(" + mac_str + r")$"
    one_mac_re = re.compile(one_mac_str)


class DateUtils:
    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def parse_date(txt: str|None) -> datetime:
        if txt is None:
            return None
        dt: datetime = dateutil.parser.isoparse(txt).astimezone(timezone.utc)
        return dt

    @staticmethod
    def fmt_date(dt: datetime) -> str:
        return datetime.isoformat(dt)

    @staticmethod
    def is_expired_date(date: datetime, expiry_seconds: int) -> bool:
        if expiry_seconds == -1:
            return False
        if date is None:
            return True
        now = DateUtils.now()
        # print(f"is_expired ({expiry_seconds} seconds) - date:{date} vs now:{now} --> {now>(date+timedelta(seconds=expiry_seconds))}")
        return now > (date + timedelta(seconds=expiry_seconds))

    @staticmethod
    def is_expired_date_string(
        date_str: str, expiry_seconds: int, dflt: bool = True
    ) -> bool:
        date = None
        try:
            date = DateUtils.parse_date(date_str)
        except Exception as err:
            print(f"Exception parsing date {date_str} : {err}")
            return dflt
        return DateUtils.is_expired_date(date, expiry_seconds)


class StringUtils:

    @staticmethod
    def is_none_or_empty(arg: str) -> bool:
        if arg is None:
            return True
        if arg == "":
            return True
        if arg.strip() == "":
            return True
        return False

    @staticmethod
    def empty_if_none(arg: str) -> str:
        if arg is None:
            return ""
        return arg


class ArrayUtils:

    @staticmethod
    def equal_arrays(arr1: list, arr2: list):
        if bool(arr1 is None) ^ bool(arr2 is None):
            return False
        if arr1 is None:
            return True
        if len(arr1) != len(arr2):
            return False
        for i in range(len(arr1)):
            # TODO : meilleure comparaison
            if not (arr1[i] == arr2[i]):
                return False
        return True

    @staticmethod
    def equal_sets(arr1: list, arr2: list):
        if bool(arr1 is None) ^ bool(arr2 is None):
            return False
        if arr1 is None:
            return True
        if len(arr1) != len(arr2):
            return False
        set1 = set(arr1)
        set2 = set(arr2)
        return set1 == set2


class SopUtils:

    _email_config = get_config().EMAIL
    _email_server = _email_config.get("SERVER")
    _email_port = _email_config.get("PORT")
    _email_from = _email_config.get("FROM_EMAIL")
    # TODO others ?

    _colors = {
        "failure": ' style="color: red;"',
        "warning": ' style="color: orange;"',
        "success": ' style="color: green;"',
    }

    @staticmethod
    def extract_script_param(data: dict, pname: str, dflt, if_int_lambda=None):
        print(
            f"extract_script_param data={data} / pname={pname} / dflt={dflt} /  if_int_lambda={if_int_lambda}"
        )
        if data is None:
            print(f"extract_script_param : data is None")
            return dflt
        if StringUtils.is_none_or_empty(pname):
            print(f"extract_script_param : StringUtils.is_none_or_empty(pname)")
            return dflt
        ret = data.get(pname)
        print(f"extract_script_param : extracted data = {ret}")
        if ret is None:
            print(f"extract_script_param : ret is none")
            return dflt
        if type(ret) is not int:
            print(f"extract_script_param : type(ret)={type(ret)}")
            return ret
        if if_int_lambda is not None:
            print(f"extract_script_param : if_int_lambda is not None")
            ret = if_int_lambda(ret)
        print(f"extract_script_param : final return")
        return ret

    @staticmethod
    def default_if_none(obj, dflt):
        if obj is not None:
            return obj
        return dflt

    @staticmethod
    def safe_equals(o1, o2):
        if bool(o1 is None) ^ bool(o2 is None):
            return False
        if o1 is None:
            return True
        return o1 == o2

    @staticmethod
    def equals_sets(set1: set, set2: set):
        if bool(set1 is None) ^ bool(set2 is None):
            return False
        if set1 is None:
            return True
        return set1 == set2

    @staticmethod
    def equals_dicts(dict1: dict, dict2: dict):
        if bool(dict1 is None) ^ bool(dict2 is None):
            return False
        if dict1 is None:
            return True
        return dict1 == dict2

    @staticmethod
    def expiry_reached(isodate: str, expiry_seconds: int):
        return DateUtils.is_expired_date_string(isodate, expiry_seconds)

    @staticmethod
    def deep_equals_json(o1, o2, ignore_case: bool = False) -> bool:
        if bool(o1 is None) ^ bool(o2 is None):
            return False
        if o1 is None:
            return True
        if o1 == o2:
            return True
        deep1 = json.dumps(o1, sort_keys=True, indent=2)
        deep2 = json.dumps(o2, sort_keys=True, indent=2)
        if ignore_case:
            return deep1.lower() == deep2.lower()
        return deep1 == deep2

    @staticmethod
    def deep_equals_json_ic(o1, o2) -> bool:
        return SopUtils.deep_equals_json(o1, o2, True)

    @staticmethod
    def is_staff_user(request):
        if request is None:
            return False
        realUsers = User.objects.filter(username__exact=request.user.username)
        if realUsers is None:
            raise AbortScript("Looks like you do not exist...")
        if len(realUsers) > 1:
            raise AbortScript("Looks like you are ubiquitious...")
        realUser: User = realUsers[0]
        return realUser.is_staff

    @staticmethod
    def send_simple_email(
        subject: str,
        sender: str,
        receivers: list[str],
        text: str,
        html: str | None = None,
    ):
        if sender is None or sender.strip() == "":
            sender = SopUtils._email_from
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = "; ".join(receivers)
        if html is None or html.strip() == "":
            html = (
                "<html><body><p>"
                + text.replace("\r\n", "<BR/>").replace("\n", "<BR/>")
                + "</p></body></html>"
            )
        # Turn these into plain/html MIMEText objects
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        message.attach(part1)
        message.attach(part2)
        smtp = smtplib.SMTP(SopUtils._email_server, SopUtils._email_port)
        smtp.sendmail(sender, receivers, message.as_string())

    @staticmethod
    def send_simple_report_email(rep):
        if not isinstance(rep, (Script, Report)):
            raise TypeError("rep must be either a Script or a Report")
        lsets = Script().load_json("local.json")
        BASE_URL = lsets.get("BASE_URL")
        CONTEXT = lsets.get("CONTEXT")
        if CONTEXT is None:
            CONTEXT = "unkwnon context"
        # TODO : cette logique doit être déportée et généralisée pour permettre un paramétrage hiérarchique des notifications mail
        NOTIFS = lsets.get("NOTIFS")
        if NOTIFS is None:
            return
        scriptname = f"{rep.__class__.__module__}.{rep.__class__.__name__}"
        NOTIFS = NOTIFS.get(scriptname)
        if NOTIFS is None:
            return
        receivers: list[str] = NOTIFS.get("receivers")
        if receivers is None:
            return
        levels: list[str] = NOTIFS.get("levels")
        if levels is None:
            levels = ["failure"]
        sender: str = NOTIFS.get("sender")
        # Handle scripts and reports differently
        # TODO : look to implement Jinja templating
        logs = []
        show_obj = False
        subject = "UNHANDLED CASE"
        if isinstance(rep, Script):
            loglst = rep.messages
            logs = [
                {"lvl": l.get("status"), "msg": l.get("message")}
                for l in loglst
                if l.get("status") in (levels)
            ]
            subject = f"NETBOX - {CONTEXT} - {scriptname} - Warnings or errors during script execution"
        elif isinstance(rep, Report):
            loglst = rep.tests[rep._current_test]["log"]
            logs = [
                {"ts": l[0], "lvl": l[1], "obj": l[2], "url": l[3], "msg": l[4]}
                for l in loglst
                if l[1] in (levels)
            ]
            subject = f"NETBOX - {CONTEXT} - {scriptname} - Warnings or errors during report execution"
            show_obj = True
        if len(logs) > 0:
            print(f"Sending email with {len(logs)} warnings/errors")
            text = (
                "Errors or warnings detected during execution of this report :"
                + scriptname
                + "\r\n\r\n"
                + "Please review and fix the following failures or errors :\r\n"
            )
            for l in logs:
                text += f"{SopUtils._txtfmt(l)} - \r\n"
            html = (
                "<html><body><p>Errors or warnings detected during execution of this script : "
                + scriptname
                + "<br/><br/>"
                + "<b>Please review and fix the following failures or errors</b></p><table border='1px'>"
            )
            for l in logs:
                html += SopUtils._htmlfmt(l, BASE_URL, show_obj)
            html += "</table>"
            SopUtils.send_simple_email(subject, sender, receivers, text, html)

    @staticmethod
    def _txtfmt(l: dict, show_obj: bool = False) -> str:
        ret = f"{l.get('lvl')}"
        if show_obj:
            x = l.get("obj")
            if x is not None:
                ret += f" - {x} "
        x = l.get("msg")
        if x is not None:
            ret += f" - {x} "
        return ret

    @staticmethod
    def _htmlfmt(l: dict, base_url: str, show_obj: bool = False) -> str:
        lvl = l.get("lvl")
        ret = f"<tr><td{SopUtils._colors.get(lvl)}>{lvl}</td>"  # type: ignore
        if show_obj:
            x = l.get("obj")
            if x is None:
                x = ""
            else:
                y = l.get("url")
                if y is not None:
                    x = f"<a href='{base_url}{y}'>{x}</a>"
            ret += f"<td>{x}</td>"
        x = l.get("msg")
        if x is not None:
            ret += f"<td>{x}</td>"
        return ret + "</tr>"

    @staticmethod
    def enqueue_script(
        func,
        instance,
        name: str = "",
        user=None,
        schedule_at=None,
        interval=None,
        **kwargs,
    ):

        import django_rq
        from core.models import Job
        from core.models import ObjectType
        from core.choices import JobStatusChoices
        from utilities.rqworker import get_queue_for_model
        import uuid

        object_type = ObjectType.objects.get_for_model(
            instance, for_concrete_model=False
        )
        rq_queue_name = get_queue_for_model(object_type.model)
        queue = django_rq.get_queue(rq_queue_name)  # type: ignore
        status = (
            JobStatusChoices.STATUS_SCHEDULED
            if schedule_at
            else JobStatusChoices.STATUS_PENDING
        )

        if schedule_at is None:
            schedule_at = DateUtils.now() + timedelta(seconds=1)

        if object_type is None:
            raise Exception("Object_type is None")

        job = Job.objects.create(
            object_type=object_type,
            object_id=instance.pk,
            name=name,
            status=status,
            scheduled=schedule_at,
            interval=interval,
            user=user,
            job_id=uuid.uuid1(),
        )

        if schedule_at:
            queue.enqueue_at(
                schedule_at, func, job_id=str(job.job_id), job=job, **kwargs
            )
        else:
            queue.enqueue(func, job_id=str(job.job_id), job=job, **kwargs)

        return job

    @staticmethod
    def check_permission(user, instance, action):
        permission = get_permission_for_model(instance, action)
        return user.has_perm(perm=permission, obj=instance)


#
# Job Handling
#


class PrismaAccessLocationRecomputeMixin:

    ACCESS_TOKEN_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
    PAYLOAD_URL = "https://api.sase.paloaltonetworks.com/sse/config/v1/locations"

    request: HttpRequest = current_request.get()  # type: ignore
    session = Session()
    model = None
    parent = None

    def try_parse_configuration(self):
        # parse all configuration.py informations
        infra_config = settings.PLUGINS_CONFIG.get("sop_infra", {})
        prisma_config = infra_config.get("prisma")

        self.payload = {
            "grant_type": "client_credentials",
            "tsg_id": prisma_config.get("tsg_id"),
            "client_id": prisma_config.get("client_id"),
            "client_secret": prisma_config.get("client_secret"),
        }

    def try_api_response(self):

        # get token
        response = self.session.post(self.ACCESS_TOKEN_URL, data=self.payload)
        response.raise_for_status()
        token = response.json().get("access_token")
        cache.set("prisma_access_token", token)

        # get payload
        headers = {"accept": "application/json", "authorization": f"bearer {token}"}
        api_response = self.session.get(self.PAYLOAD_URL, headers=headers)
        api_response.raise_for_status()

        return api_response.json()

    def _get_computed_location(self, name, slug):

        if name.strip() == "" or slug.strip() == "" or self.parent is None:
            return None

        target = self.parent.objects.filter(slug=slug)
        if target.exists():
            obj = target.first()
            if obj.name != name:
                obj.name = name
                obj.full_clean()
                obj.save()
            return obj

        obj = self.parent.objects.create(slug=slug, name=name)
        obj.full_clean()
        obj.save()
        return obj

    def recompute_access_location(self, response):

        if self.model is None or self.parent is None:
            return

        new_objects = []
        updates = []

        existing_object = self.model.objects.values(
            "slug", "name", "latitude", "longitude", "compute_location"
        )

        existing_data = {
            obj["slug"]: {
                "name": obj["name"],
                "latitude": obj["latitude"],
                "longitude": obj["longitude"],
                "location": obj["compute_location"],
            }
            for obj in existing_object  # type: ignore
        }

        for item in response:
            slug = item["value"]
            name = item["display"]
            latitude = Decimal(f"{float(item['latitude']):.6f}")
            longitude = Decimal(f"{float(item['longitude']):.6f}")
            location_slug = item["region"]
            location_name = item["aggregate_region"]

            computed = self._get_computed_location(location_name, location_slug)
            if slug in existing_data:
                existing = existing_data[slug]

                if (
                    existing["name"] != name
                    or existing["latitude"] != latitude
                    or existing["longitude"] != longitude
                ):
                    updates.append(
                        self.model(
                            slug=slug,
                            name=name,
                            latitude=latitude,
                            longitude=longitude,
                            compute_location=computed,
                        )
                    )
                continue

            new_objects.append(
                self.model(
                    slug=slug,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    compute_location=computed,
                )
            )

        if new_objects:
            self.model.objects.bulk_create(new_objects)
        if updates:
            self.model.objects.bulk_update(
                updates, fields=["name", "latitude", "longitude"]
            )

    def try_recompute_access_location(self) -> bool:
        try:
            self.try_parse_configuration()
        except:
            messages.error(self.request, f"ERROR: invalid parameters in PLUGIN_CONFIG")
            return False

        try:
            response = self.try_api_response()
        except:
            messages.error(self.request, f"ERROR: invalid API response")
            return False

        try:
            self.recompute_access_location(response)
        except:
            messages.error(
                self.request,
                f"ERROR: invalid API response: cannot recompute Access Location",
            )
            return False
        return True


class SopInfraRelatedModelsMixin:

    def normalize_queryset(self, obj):

        qs = [str(item) for item in obj]
        if qs == []:
            return None

        return f"id=" + "&id=".join(qs)

    def get_slave_sites(self, infra):
        """
        look for slaves sites and join their id
        """
        if not infra.exists():
            return None, None

        # get every SopInfra instances with master_site = current site
        # and prefetch the only attribute that matters to optimize the request
        sites = SopInfra.objects.filter(
            master_site=(infra.first()).site
        ).prefetch_related("site")
        count = sites.count()

        target = sites.values_list("site__pk", flat=True)
        if not target:
            return None, None

        return self.normalize_queryset(target), count

    def get_slave_infra(self, infra):

        if not infra.exists():
            return None, None

        infras = SopInfra.objects.filter(master_site=(infra.first().site))
        count = infras.count()

        target = infras.values_list("id", flat=True)
        if not target:
            return None, None

        return self.normalize_queryset(target), count
