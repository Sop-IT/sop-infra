from core.choices import JobIntervalChoices
from netbox.jobs import JobRunner, Job, system_job
from sop_infra.models import SopMerakiUtils
from sop_infra.utils import JobRunnerLogMixin
import logging

@system_job(interval=JobIntervalChoices.INTERVAL_MINUTELY)
class SopMerakiDashRefreshJob(JobRunnerLogMixin, JobRunner):

    class Meta:
        name = "Refresh Meraki dashboards"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        try:
            SopMerakiUtils.refresh_dashboards(self)
        finally:
            self.job.data = self.get_job_data()       

    @staticmethod
    def launch_async()->Job:
        return SopMerakiDashRefreshJob.enqueue()
