# from extras.validators import CustomValidator
# from extras.choices import LogLevelChoices
# from dcim.models import Device, Site

# from scripts.sop_utils import SopUtils, CheckResult, CheckResultList, ValidatorCheckResultLogger

# from .models import InfraMerakiSDWAN, InfraMerakiHubOrderChoices


# IGNORED_LOCATIONS = ['planned', 'retired']


# class DeviceRules():

#     @staticmethod
#     def check_device_location(device:Device, crl:CheckResultList):
#         if device.status not in IGNORED_LOCATIONS and device.location is None:
#             crl.append(CheckResult(LogLevelChoices.LOG_FAILURE, device,
#                 f'{device.site.group.name}:{device.name} : this device is missing a valid location', 'location'))
    
#     @staticmethod
#     def check_device_tenancy(device:Device, crl:CheckResultList):
#         if device.status not in IGNORED_LOCATIONS and device.tenant is None:
#             crl.append(CheckResult(LogLevelChoices.LOG_FAILURE, device,
#                 f'{device.site.group.name}:{device.name} : this device is missing a valid tenant', 'tenant'))
#         elif device.status not in IGNORED_LOCATIONS and device.tenant != device.site.tenant:
#             crl.append(CheckResult(LogLevelChoices.LOG_FAILURE, device,
#                 f'{device.site.group.name}:{device.name} : this device tenant and its site tenant do not match !', 'tenant'))



# class DeviceValidator(CustomValidator):

#     def validate(self, instance:Device request) -> None:
#         fail_prefix = f'{instance.name} -> '
#         crl = CheckResultList()
#         DeviceRules.check_device_location(instance, crl)
#         DeviceRules.check_device_tenancy(instance, crl)
#         crl.dump_to(ValidatorCheckResultLogger(self, fail_prefix))
#
