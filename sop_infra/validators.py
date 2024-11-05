from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


__all__ = (
    'SopInfraValidator',
)


class SopInfraValidator:

    @staticmethod
    def dc_site_reset_fields(instance) -> None:
        instance.sdwanha = '-DC-'
        instance.site_user_count = '-DC'
        instance.site_sdwan_master_location = None
        instance.wan_reco_bw = None
        instance.wan_computed_users = None
        instance.criticity_stars = '****'
        instance.site_mx_model = 'mx450'

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
        instance.criticity_stars = None
        instance.site_mx_model = None

    @staticmethod
    def count_wan_computed_users(instance) -> int:
        if instance.site.status in ['active', 'decommissioning']:
            return instance.ad_cumul_user

        elif instance.site.status in ['candidate', 'planned', 'staging']:
            return instance.est_cumulative_users

        elif instance.site.status in ['starting']:
            wan:int = instance.ad_cumul_user

            if instance.est_cumulative_users is not None and instance.est_cumulative_users > wan:
                return instance.est_cumulative_users

            return instance.ad_cumul_user

        return 0

    @staticmethod
    def count_and_fix_user_slice(wan:int|None) -> tuple[str]:
        if wan < 10 :
            return '<10', 'mx67'
        elif wan < 20 :
            return '10<20', 'mx67'
        elif wan < 50 :
            return '20<50', 'mx68'
        elif wan < 100 :
            return '50<100', 'mx85'
        elif wan < 200 :
            return '100<200', 'mx95'
        elif wan < 500 :
            return '200<500', 'mx95'
        return '>500', 'mx250'

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

