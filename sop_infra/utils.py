from django.contrib import messages

from sop_infra.models import SopInfra


__all__ = (
    'SopInfraRefreshMixin',
    'SopInfraRelatedModelsMixin'
)


class SopInfraRefreshMixin:

    def update_master_instance(self, request, instance, ad):

        if instance.ad_cumulative_users == ad:
            messages.warning(request, f'{instance} has already been updated !')
            return

        instance.snapshot()
        instance.full_clean()
        instance.save()
        messages.success(request, f'{instance} successfully updated !')


    def update_child_instance(self, request, instance, ad):

        if instance.ad_cumulative_users == ad:
            messages.warning(request, f'{instance} has already been updated !')
            return

        instance.snapshot()
        instance.save()
        messages.success(request, f'{instance} successfully updated !')


    def pre_compute_queryset(self, request, queryset, parent=False):

        for instance in queryset:

            if parent is False:
                self.update_child_instance(
                    instance,
                    instance.compute_ad_cumulative_users(instance)
                )
                continue

            self.update_master_instance(
                instance,
                instance.compute_ad_cumulative_users(instance)
            )


    def refresh_infra(self, request, queryset):

        # cannot select DC because 
        queryset = queryset.exclude(site__status='dc')
        if queryset.first() is None:
            messages.warning(request, 'You cannot refresh -DC- status sites.')
            return

        slave = queryset.filter(master_site__isnull=False)
        maybe_master = queryset.filter(master_site__isnull=True)



class SopInfraRelatedModelsMixin:

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
        
        qs = [str(item) for item in target]
        if qs == []:
            return None, None

        return f'id=' + '&id'.join(qs), count


    def get_slave_infra(self, infra):

        if not infra.exists():
            return None

        return SopInfra.objects.filter(master_site=(infra.first().site))

