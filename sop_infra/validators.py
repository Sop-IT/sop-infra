from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


__all__ = (
    'SopInfraMasterValidator',
    'SopInfraSlaveValidator',
    'DC_status_site_fields',
)



def DC_status_site_fields(instance) -> None:

    instance.sdwanha = '-DC-'
    instance.site_user_count = '-DC'
    instance.site_sdwan_master_location = None
    instance.master_site = None
    instance.wan_reco_bw = None
    instance.wan_computed_users = None
    instance.criticity_stars = '****'
    instance.site_mx_model = 'mx450'



class SopInfraSizingValidator:
    '''
    SopInfra - sizing related auto-computes validator methods
    '''

    @staticmethod
    def get_wan_computed_users(instance) -> int:

        if instance.site.status in ['active', 'decommissioning']:
            return instance.ad_cumulative_users

        elif instance.site.status in ['candidate', 'planned', 'staging']:
            return instance.est_cumulative_users

        elif instance.site.status in ['starting']:
            wan = instance.ad_cumulative_users

            if wan is None:
                wan = 0

            if instance.est_cumulative_users is not None and instance.est_cumulative_users > wan:
                return instance.est_cumulative_users

            return instance.ad_cumulative_users

        return 0


    @staticmethod
    def get_mx_and_user_slice(wan:int) -> tuple[str]:

        if wan < 10 :
            return '<10', 'MX67'
        elif wan < 20 :
            return '10<20', 'MX67'
        elif wan < 50 :
            return '20<50', 'MX68'
        elif wan < 100 :
            return '50<100', 'MX85'
        elif wan < 200 :
            return '100<200', 'MX95'
        elif wan < 500 :
            return '200<500', 'MX95'
        return '>500', 'MX250'


    @staticmethod
    def get_recommended_bandwidth(wan:int) -> int:

        if wan > 100:
            return round(wan * 2.5)
        elif wan > 50:
            return round(wan * 3)
        elif wan > 10:
            return round(wan * 4)
        else:
            return round(wan * 5)



class SopInfraSlaveValidator:

    def __init__(self, instance):

        if instance.site_sdwan_master_location and instance.master_site is None:
            instance.master_site = instance.site_sdwan_master_location.site

        # if not slave -> return
        if instance.master_site is None:
            return

        self.check_master_exists(instance)
        self.check_no_loop(instance)
        self.compute_slave_sizing(instance)
        self.reset_slave_fields(instance)


    def check_master_exists(self, instance):

        from sop_infra.models import SopInfra
        target = SopInfra.objects.exclude(pk=instance.pk)

        if instance.site_sdwan_master_location is not None:
            if target.filter(site_sdwan_master_location=instance.site_sdwan_master_location).exists():
                raise ValidationError({
                    'site_sdwan_master_location': 'This location is already the MASTER location for other sites infrastructures.'
                })


    def check_no_loop(self, instance):

        if instance.site_sdwan_master_location is not None:
            if instance.site_sdwan_master_location.site == instance.site:
                raise ValidationError({
                    'site_sdwan_master_location': 'SDWAN MASTER site cannot be itself'
                 })

            if instance.site_sdwan_master_location.site != instance.master_site:
                 raise ValidationError({
                    'site_sdwan_master_location': 'SDWAN MASTER location site must be equal to MASTER site or leaved blank.'
                 })

        if instance.master_site == instance.site:
            raise ValidationError({
                'master_site': 'SDWAN MASTER site cannot be itself'
            })


    def compute_slave_sizing(self, instance):

        sizing = SopInfraSizingValidator()

        wan = sizing.get_wan_computed_users(instance)
        if wan is None:
            wan = 0
        instance.wan_computed_users = wan


    def reset_slave_fields(self, instance):

        instance.sdwanha = '-SLAVE SITE-'
        instance.sdwan1_bw = None
        instance.sdwan2_bw = None
        instance.migration_sdwan = None
        instance.site_type_vip = None
        instance.site_type_wms = None
        instance.site_type_red = None
        instance.site_phone_critical = None
        instance.site_infra_sysinfra = None
        instance.site_type_indus = None
#        instance.est_cumulative_users = None
        instance.wan_reco_bw = None
#        instance.wan_computed_users = None
        instance.criticity_stars = None
        instance.site_mx_model = None



class SopInfraMasterValidator:

    def __init__(self, instance):

        if self.is_slave(instance):
            return

        self.compute_master_sizing(instance)
        self.compute_sdwanha(instance)


    def is_slave(self, instance) -> bool:

        return instance.master_site is not None \
            or instance.site_sdwan_master_location is not None


    def compute_master_sizing(self, instance):

        sizing = SopInfraSizingValidator()

        # ad
        ad = instance.compute_ad_cumulative_users(instance)
        if ad is None:
            ad = 0
        instance.ad_cumulative_users = ad

        # wan
        wan = sizing.get_wan_computed_users(instance)
        if wan is None:
            wan = 0
        instance.wan_computed_users = wan

        # user slice
        user_slice, mx = sizing.get_mx_and_user_slice(wan)
        instance.site_user_count = user_slice
        instance.site_mx_model = mx

        # reco bw
        bw = sizing.get_recommended_bandwidth(wan)
        instance.wan_reco_bw = bw


    def compute_sdwanha(self, instance):

        if instance.site.status in [
            'no_infra', 'candidate', 'reserved',
            'template', 'inventory', 'teleworker']:
        # enforce no_infra constraints
            instance.sdwanha = '-NO NETWORK-'
            instance.sdwan1_bw = None
            instance.sdwan2_bw = None
            instance.criticity_stars = None
            instance.site_infra_sysinfra = None
        else:
            # compute sdwanha for normal sites
            instance.sdwanha = '-NHA-'
            instance.criticity_stars = '*'
            if instance.site_type_vip == 'true':
                instance.sdwanha = '-HA-'
                instance.criticity_stars = '***'
            # no -HAS- because there is no site_type_indus == IPL
            elif instance.site_type_indus == 'fac' \
                or instance.site_phone_critical == 'true' \
                or instance.site_type_red == 'true' \
                or instance.site_type_wms == 'true' \
                or instance.site_infra_sysinfra == 'sysclust' \
                or instance.site_user_count in ['50<100', '100<200', '200<500', '>500']:
                instance.sdwanha = '-HA-'
                instance.criticity_stars = '**'

