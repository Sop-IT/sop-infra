from sop_infra.models import SopInfra


__all__ = (
    'SopInfraRelatedModelsMixin',
)

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

