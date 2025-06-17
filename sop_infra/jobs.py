import traceback
from core.choices import JobIntervalChoices
from netbox.jobs import JobRunner, Job, system_job
from sop_infra.models import SopMerakiUtils
from sop_infra.utils import JobRunnerLogMixin
import logging


class SopMerakiDashRefreshJob(JobRunnerLogMixin, JobRunner):

    class Meta:
        name = "Refresh Meraki dashboards"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            SopMerakiUtils.refresh_dashboards(self)
        except Exception:
            text=traceback.format_exc()
            self.failure(text)
            self.job.error = text
            raise
        finally:
            self.job.data = self.get_job_data()       


    @staticmethod
    def launch_manual()->Job:
        if SopMerakiUtils.get_no_auto_sched():
            return SopMerakiDashRefreshJob.enqueue(immediate=True)
        return SopMerakiDashRefreshJob.enqueue()


if not(SopMerakiUtils.get_no_auto_sched()):
    SopMerakiDashRefreshJob.enqueue_once(interval=JobIntervalChoices.INTERVAL_MINUTELY*2)