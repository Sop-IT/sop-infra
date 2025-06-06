from netbox.jobs import JobRunner, Job
from sop_infra.models import SopMerakiUtils
import logging

class SopMerakiDashRefreshJob(JobRunner):

    class Meta:
        name = "Refresh Meraki dashboards"

    def run(self, *args, **kwargs):
        job:Job=self.job
        obj = job.object
        SopMerakiUtils.refresh_dashboards()

    @staticmethod
    def launch_async()->Job:
        return SopMerakiDashRefreshJob.enqueue_once()