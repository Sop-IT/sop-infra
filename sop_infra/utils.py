import requests as py_requests
from decimal import Decimal
import json

from django.contrib import messages
from django.conf import settings

from netbox.context import current_request

from sop_infra.validators import SopInfraSizingValidator
from sop_infra.models import SopInfra


__all__ = (
    'SopInfraRefreshMixin',
    'SopInfraRelatedModelsMixin',
    'PrismaAccessLocationRecomputeMixin'
)


class PrismaAccessLocationRecomputeMixin:

    request = current_request.get()

    def try_parse_configuration(self):
        infra_config = settings.PLUGINS_CONFIG.get('sop_infra', {})
        prisma_config = infra_config.get('prisma')

        self.payload = {
            'grant_type':'client_credentials',
            'tsg_id':prisma_config.get('tsg_id'),
            'client_id':prisma_config.get('client_id'),
            'client_secret':prisma_config.get('client_secret')
        }
        self.access_token_url = prisma_config.get('access_token_url')
        self.payload_url = prisma_config.get('payload_url')

    def try_api_response(self):
        response = py_requests.post(self.access_token_url, data=self.payload)
        token = response.json().get('access_token')
        headers = {
            'Accept':'application/json',
            'Authorization':f'Bearer {token}'
        }

        api_response = py_requests.get(self.payload_url, headers=headers, data={})
        return json.loads(api_response.text)

    def recompute_access_location(self, response):
        for item in response:
            if self.model.objects.filter(slug=item['value']).exists():
                continue
            obj = self.model(
                slug=item['value'],
                name=item['display'],
                latitude=Decimal(f"{float(item['latitude']):.6f}"),
                longitude=Decimal(f"{float(item['longitude']):.6f}")
            )
            obj.full_clean()
            obj.save()
            obj.snapshot()
            print('created', obj)

    def try_recompute_access_location(self):
        try:
            self.try_parse_configuration()
        except:
            messages.error(self.request, "ERROR: invalid parameters in PLUGIN_CONFIG -> script aborted.")
            return

        try:
            response = self.try_api_response()
        except:
            messages.error(self.request, "ERROR: invalid API response make sure you have the access -> script aborted")
            return

        #try:
        self.recompute_access_location(response)
        #except:
            #messages.error(self.request, "ERROR: invalid API response cannot recompute Access Location -> script aborted")


class SopInfraRefreshMixin:

    sizing = SopInfraSizingValidator()
    count:int = 0

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
        except:pass


class SopInfraRelatedModelsMixin:


    def normalize_queryset(self, obj):

        qs = [str(item) for item in obj]
        if qs == []:
            return None

        return f'id=' + '&id='.join(qs)


    def get_slave_sites(self, infra):
        '''
        look for slaves sites and join their id
        '''
        if not infra.exists():
            return None, None

        # get every SopInfra instances with master_site = current site
        # and prefetch the only attribute that matters to optimize the request
        sites = SopInfra.objects.filter(master_site=(infra.first()).site).prefetch_related('site')
        count = sites.count()

        target = sites.values_list('site__pk', flat=True)
        if not target:
            return None, None
        
        return self.normalize_queryset(target), count


    def get_slave_infra(self, infra):

        if not infra.exists():
            return None, None

        infras = SopInfra.objects.filter(master_site=(infra.first().site))
        count = infras.count()

        target = infras.values_list('id', flat=True)
        if not target:
            return None, None

        return self.normalize_queryset(target), count

