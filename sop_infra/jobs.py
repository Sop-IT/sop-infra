from core.choices import JobIntervalChoices
from netbox.jobs import JobRunner, Job, system_job
from sop_infra.models import SopMerakiUtils
import logging

@system_job(interval=JobIntervalChoices.INTERVAL_MINUTELY)
class SopMerakiDashRefreshJob(JobRunner):

    class Meta:
        name = "Refresh Meraki dashboards"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        SopMerakiUtils.refresh_dashboards()

    @staticmethod
    def launch_async()->Job:
        return SopMerakiDashRefreshJob.enqueue()
