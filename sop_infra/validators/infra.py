from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


__all__ = (
    'SopInfraSlaveValidator',
)


class SopInfraSlaveValidator:

    def __init__(self, instance):
        if instance.master_site is None:
            return
        # Exec slave validators
        self.check_master_exists(instance)
        self.check_no_loop(instance)

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
                    'site_sdwan_master_location': 'SDWAN MASTER location site must be equal to MASTER site or left blank.'
                 })
        if instance.master_site == instance.site:
            raise ValidationError({
                'master_site': 'SDWAN MASTER site cannot be itself'
            })










