from django.conf import settings
from core.choices import JobIntervalChoices
from netbox.jobs import system_job
from core.exceptions import JobFailed
from netbox.jobs import JobRunner, Job, JobStatusChoices
from sop_infra.jobs import SopSyncAdUsers, SopSyncMgmtInterfaces
from sop_infra.utils.mixins import JobRunnerLogMixin

@system_job(interval=JobIntervalChoices.INTERVAL_HOURLY)
class SopAutoSyncMgmtInterfaces(SopSyncMgmtInterfaces):

    class Meta: # type: ignore
        name = "Auto Meraki devices management interfaces, only in prod"

    def run(self, *args, **kwargs):
        
        if settings.DEBUG:
            self.log_success("DEBUG MODE -> NO AUTO RUN")
            return
        
        super().run(*args, **kwargs)


        