from django.conf import settings
from core.choices import JobIntervalChoices
from netbox.jobs import system_job
from sop_infra.jobs import SopMerakiDashRefreshJob

@system_job(interval=JobIntervalChoices.INTERVAL_MINUTELY * 60)
class SopMerakiDashAutoRefreshJob(SopMerakiDashRefreshJob):

    class Meta:  # type: ignore
        name = "Auto refresh Meraki dashboards, only in prod"

    def run(self, *args, **kwargs):

        if settings.DEBUG:
            self.log_success("DEBUG MODE -> NO AUTO RUN")
            return

        super().run(*args, **kwargs)
