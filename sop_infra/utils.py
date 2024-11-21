from django.contrib import messages

from netbox.context import current_request

from sop_infra.validators.model_validators import SopInfraSizingValidator
from sop_infra.models import SopInfra


__all__ = (
    'SopInfraRefreshMixin',
    'SopInfraRelatedModelsMixin'
)


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

