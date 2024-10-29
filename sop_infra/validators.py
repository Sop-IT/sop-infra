from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


__all__ = (
    'SopInfraValidator',
)


class SopInfraValidator:

    @staticmethod
    def slave_site_reset_fields(instance) -> None:
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
        instance.est_cumulative_users = None
        instance.wan_reco_bw = None
        instance.wan_computed_users = None

    @staticmethod
    def count_wan_computed_users(instance) -> int:
        wan:int|None = instance.wan_computed_users

        if instance.site.status in ['active', 'decommissioning']:
            wan = instance.ad_cumul_user
        elif instance.site.status in ['candidate', 'planned', 'staging']:
            wan = instance.est_cumulative_users
        elif instance.site.status in ['starting']:
            wan = instance.ad_cumul_user
            if instance.est_cumulative_users is not None and instance.est_cumulative_users > wan:
                wan = instance.est_cumulative_users
        else:
            wan = 0
        return wan

    @staticmethod
    def count_site_user(wan:int|None) -> str:
        if wan < 10 :
            return '<10'
        elif wan < 20 :
            return '10<20'
        elif wan < 50 :
            return '20<50'
        elif wan < 100 :
            return '50<100'
        elif wan < 200 :
            return '100<200'
        elif wan < 500 :
            return '200<500'
        return '>500'

    @staticmethod
    def set_recommended_bandwidth(wan:int) -> int:
        if wan > 100:
            return round(wan * 2.5)
        elif wan > 50:
            return round(wan * 3)
        elif wan > 10:
            return round(wan * 4)
        else:
            return round(wan * 5)

    @staticmethod
    def compute_sdwanha(instance):
        if instance.site.status in ['no_infra', 'candidate', 'reserved', 'template', 'inventory', 'teleworker']:
        # enforce no_infra constraints
            instance.sdwanha = '-NO NETWORK-'
            instance.sdwan1_bw = None
            instance.sdwan2_bw = None
            instance.site_infra_sysinfra = None
        else:
            # compute sdwanha for normal sites
            target_ha = '-NHA-'
            if instance.site_type_indus == 'ipl':
                target_ha = 'HAS-'
            elif instance.site_type_vip == True:
                target_ha = '-HA-'
            elif instance.site_type_indus == 'fac' \
                or instance.site_phone_critical == True \
                or instance.site_type_red == True \
                or instance.site_type_wms == True \
                or instance.site_infra_sysinfra == 'sysclust' \
                or instance.site_user_count in ['50<100', '100<200', '200<500', '>500']:
                target_ha = '-HA-'

            # changed stored HA status in necessary
            if instance.sdwanha != target_ha:
                instance.sdwanha == target_ha


