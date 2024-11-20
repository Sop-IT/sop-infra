from django.contrib import messages

from sop_infra.validators.model_validators import SopInfraSizingValidator
from sop_infra.models import SopInfra


__all__ = (
    'SopInfraRefreshMixin',
    'SopInfraRelatedModelsMixin'
)


class SopInfraRefreshMixin:

    def update_master_instance(self, instance, wan):

        if instance.wan_computed_users == wan:
            return

        instance.snapshot()
        instance.full_clean()
        instance.save()


    def update_child_instance(self, instance, wan):

        if instance.wan_computed_users == wan:
            return

        instance.snapshot()
        instance.full_clean()
        instance.save()


    def pre_compute_queryset(self, queryset, parent=False):

        sizing = SopInfraSizingValidator()

        for instance in queryset:

            if parent is False:
                self.update_child_instance(
                    instance,
                    sizing.get_wan_computed_users(instance)
                )
                continue

            wan = sizing.get_wan_computed_users(instance)
            instance.wan_computed_users = wan if wan is not None else 0
            self.update_master_instance(
                instance,
                instance.compute_wan_cumulative_users(instance)
            )


    def refresh_infra(self, request, queryset):

        if queryset.first() is None:
            messages.error(request, 'Please select at least one site to refresh.')
            return

        # cannot select DC because 
        queryset = queryset.exclude(site__status='dc')
        if queryset.first() is None:
            messages.error(request, 'You cannot recompute sizing on -DC- status sites.')
            return

        slave = queryset.filter(master_site__isnull=False)
        maybe_master = queryset.filter(master_site__isnull=True)

        self.pre_compute_queryset(slave, False)
        self.pre_compute_queryset(maybe_master, True)

        messages.success(request, f"Successfully updated {queryset.count()} infrastructures.")


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
            return None

        infras = SopInfra.objects.filter(master_site=(infra.first().site))
        count = infras.count()

        target = infras.values_list('id', flat=True)
        if not target:
            return None, None

        return self.normalize_queryset(target), count

