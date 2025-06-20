import traceback
from django.conf import settings
from core.choices import JobIntervalChoices
from netbox.jobs import JobRunner, Job, system_job
from sop_infra.models import SopMerakiUtils
from sop_infra.utils import JobRunnerLogMixin


@system_job(interval=JobIntervalChoices.INTERVAL_MINUTELY*10)
class SopMerakiDashRefreshJob(JobRunnerLogMixin, JobRunner):

    class Meta:
        name = "Refresh Meraki dashboards"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            SopMerakiUtils.refresh_dashboards(self, settings.DEBUG)
        except Exception:
            text=traceback.format_exc()
            self.failure(text)
            self.job.error = text
            raise
        finally:
            self.job.data = self.get_job_data()       


    @staticmethod
    def launch_manual()->Job:
        if settings.DEBUG:
            return SopMerakiDashRefreshJob.enqueue(immediate=True)
        return SopMerakiDashRefreshJob.enqueue()

