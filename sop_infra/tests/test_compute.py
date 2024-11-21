from django.urls import reverse

from utilities.testing import TestCase
from dcim.models import Site

from sop_infra.models import SopInfra
from sop_infra.utils import SopInfraRefreshMixin


__all__ = (
    'SopInfraComputeTestCase',
)


class SopInfraComputeTestCase(TestCase):

    user_permissions = ('sop_infra.change_sopinfra',)

    @classmethod
    def setUpTestData(cls):

        sites = (
            Site(name='site 1', slug='site-1', status='active'),
            Site(name='site 2', slug='site-2', status='starting'),
            Site(name='site 3', slug='site-3', status='candidate'),
        )

        for site in sites:
            site.save()

        cls.infra1 = SopInfra.objects.get(site=Site.objects.get(slug='site-1'))
        cls.infra2 = SopInfra.objects.get(site=Site.objects.get(slug='site-2'))
        cls.infra3 = SopInfra.objects.get(site=Site.objects.get(slug='site-3'))

        cls.infra2.master_site = cls.infra1.site
        cls.infra3.master_site = cls.infra1.site

        for infra in SopInfra.objects.all():
            infra.full_clean()
            infra.save()


    def test_recompute_sizing_master(self):
        """test if recomputing master recomputes its childs"""

        mixin = SopInfraRefreshMixin()
        s1 = Site.objects.get(slug='site-1')
        s2 = Site.objects.get(slug='site-2')
        s3 = Site.objects.get(slug='site-3')

        self.infra1.ad_direct_users = 42
        self.infra2.est_cumulative_users = 69

        self.infra1.save()
        self.infra2.save()

        mixin.refresh_infra(SopInfra.objects.filter(pk=self.infra1.pk))

        self.assertEqual(SopInfra.objects.get(site=s1).wan_computed_users, 111)
        self.assertEqual(SopInfra.objects.get(site=s2).wan_computed_users, 69)
        self.assertEqual(SopInfra.objects.get(site=s3).wan_computed_users, 0)


    def test_recompute_sizing_child(self):
        """test if recomputing child recomputes their master"""

        mixin = SopInfraRefreshMixin()
        s1 = Site.objects.get(slug='site-1')
        s2 = Site.objects.get(slug='site-2')
        s3 = Site.objects.get(slug='site-3')

        self.infra1.ad_direct_users = 42
        self.infra2.est_cumulative_users = 69

        self.infra1.save()
        self.infra2.save()

        mixin.refresh_infra(SopInfra.objects.filter(pk=self.infra2.pk))

        self.assertEqual(SopInfra.objects.get(site=s1).wan_computed_users, 111)
        self.assertEqual(SopInfra.objects.get(site=s2).wan_computed_users, 69)
        self.assertEqual(SopInfra.objects.get(site=s3).wan_computed_users, 0)

