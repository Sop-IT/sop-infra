import time
from requests import Session
from decimal import Decimal

from django.core.cache import cache
from django.contrib import messages
from django.conf import settings

from netbox.context import current_request

from sop_infra.validators import SopInfraSizingValidator
from sop_infra.models import SopInfra


__all__ = (
    "PrismaAccessLocationRecomputeMixin",
    "SopInfraRelatedModelsMixin",
    "SopInfraRefreshMixin",
)


class PrismaAccessLocationRecomputeMixin:

    ACCESS_TOKEN_URL = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
    PAYLOAD_URL = "https://api.sase.paloaltonetworks.com/sse/config/v1/locations"

    request = current_request.get()
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
            for obj in existing_object
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


class SopInfraRefreshMixin:

    sizing = SopInfraSizingValidator()
    count: int = 0

    def recompute_instance(self, instance):

        instance.snapshot()
        instance.full_clean()
        instance.save()
        self.count += 1

    def recompute_parent_if_needed(self, instance):

        # compare current with wan cumul
        wan = instance.wan_computed_users
        instance.wan_computed_users = self.sizing.get_wan_computed_users(instance)
        cumul = instance.compute_wan_cumulative_users(instance)

        # if wan cumul is != current -> recompute sizing.
        if wan != cumul:
            self.recompute_instance(instance)

    def recompute_child(self, queryset):

        if not queryset.exists():
            return

        # parse all queryset
        for instance in queryset:

            # compare computed wan users with current
            wan = self.sizing.get_wan_computed_users(instance)
            if wan != instance.wan_computed_users:
                self.recompute_instance(instance)

            # check if the parent is valid and recompute it if needed
            parent = SopInfra.objects.filter(site=instance.master_site)
            if parent.exists():
                self.recompute_parent_if_needed(parent.first())

    def recompute_maybe_parent(self, queryset):

        if not queryset.exists():
            return

        # parse all queryset
        for instance in queryset:

            # if this is a parent, check that child are up to date
            maybe_child = SopInfra.objects.filter(master_site=instance.site)
            if maybe_child.exists():
                self.recompute_child(maybe_child)

            self.recompute_parent_if_needed(instance)

    def refresh_infra(self, queryset):

        if queryset.first() is None:
            return

        # get children
        self.recompute_child(queryset.filter(master_site__isnull=False))
        # get maybe_parent
        self.recompute_maybe_parent(queryset.filter(master_site__isnull=True))

        try:
            request = current_request.get()
            messages.success(request, f"Successfully recomputed {self.count} sizing.")
        except:
            pass


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
