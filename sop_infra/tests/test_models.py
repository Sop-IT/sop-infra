from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from utilities.testing import TestCase
from dcim.models import Site, Location

from sop_infra.models import SopInfra


__all__ = (
    'SopInfraSlaveModelTestCase',
    'SopInfraMasterModelTestCase'
)


class SopInfraSlaveModelTestCase(TestCase):

    user_permissions = ()


    @classmethod
    def setUpTestData(cls):

        sites = (
            Site(name='site 1', slug='site-1', status='active'),
            Site(name='site 2', slug='site-2', status='starting'),
            Site(name='site 3', slug='site-3', status='staging')
        )
        for site in sites:
            site.save()

        location = Location(site=Site.objects.first(), name="test-location", slug='test-loc')
        location.full_clean()
        location.save()

        cls.site1 = Site.objects.get(slug='site-1')
        cls.site2 = Site.objects.get(slug='site-2')
        cls.site3 = Site.objects.get(slug='site-3')
        cls.location = location


    def test_slave_wrong_location(self):
        """Test that invalid master location raises ValidationError"""
        with self.assertRaises(ValidationError):
            infra = SopInfra.objects.create(
                site=self.site1,
                site_sdwan_master_location=self.location
            )
            infra.full_clean()


    def test_slave_wrong_master_site(self):
        """Test that invalid master site raises IntegrityError"""
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                infra = SopInfra.objects.create(
                    site=self.site1,
                    master_site=self.site1
                )


    def test_slave_master_location_site_not_master_site(self):
        """Test master site coherence """
        with self.assertRaises(ValidationError):
            infra = SopInfra.objects.create(
                site=self.site1,
                site_sdwan_master_location=self.location,
                master_site=self.site3
            )
            infra.full_clean()


    def test_slave_correct_master_location(self):
        """Test valid master location"""
        infra = SopInfra.objects.create(
            site=self.site2,
        site_sdwan_master_location=self.location
        )
        infra.full_clean()
        self.assertEqual(infra.master_site, infra.site_sdwan_master_location.site)


    def test_slave_correct_master_site(self):
        """Test valid master site"""
        infra = SopInfra.objects.create(
            site=self.site2,
            master_site=self.site1
        )
        infra.full_clean()
        self.assertEqual(infra.site_sdwan_master_location, None)


    def test_slave_master_location_already_exists(self):
        """Test that if master location already exists -> raise ValidationError"""
        with self.assertRaises(ValidationError):
            infra = SopInfra.objects.create(
                site=self.site2,
                site_sdwan_master_location=self.location
            )
            infra2 = SopInfra.objects.create(
                site=self.site3,
                site_sdwan_master_location=self.location
            )
            infra.full_clean()
            infra2.full_clean()


    def test_slave_compute_sizing(self):
        """Test that valid slave infra computes sizing"""
        infra = SopInfra.objects.create(
            site=self.site1,
            master_site=self.site3
        )
        infra.full_clean()
        self.assertEqual(infra.wan_computed_users, 0)

        infra.ad_direct_users = 42
        infra.est_cumulative_users = 69
        infra.full_clean()
        self.assertEqual(infra.wan_computed_users, 42)

        infra.site = self.site2
        infra.full_clean()
        self.assertEqual(infra.wan_computed_users, 69)


    def test_slave_default_fields(self):
        """Test that valid slave infra computes default fields"""
        infra = SopInfra.objects.create(
            site=self.site1,
            master_site=self.site2
        )
        infra.full_clean()
        self.assertEqual(infra.sdwanha, '-SLAVE SITE-')

        infra.master_site = None
        infra.full_clean()
        self.assertEqual(infra.sdwanha, '-NHA-')



class SopInfraMasterModelTestCase(TestCase):

    user_permissions = ()


    @classmethod
    def setUpTestData(cls):

        sites = (
            Site(name='site 1', slug='site-1', status='active'),
            Site(name='site 2', slug='site-2', status='starting'),
            Site(name='site 3', slug='site-3', status='staging')
        )
        for site in sites:
            site.save()

        cls.site1 = Site.objects.get(slug='site-1')
        cls.site2 = Site.objects.get(slug='site-2')
        cls.site3 = Site.objects.get(slug='site-3')

        infras = (
            SopInfra(site=cls.site1, ad_direct_users=442),
            SopInfra(site=cls.site2, ad_direct_users=42, est_cumulative_users=69, site_type_red='true'),
            SopInfra(site=cls.site3, ad_direct_users=0, est_cumulative_users=19, site_type_vip='true'),
        )
        for infra in infras:
            infra.full_clean()
            infra.save()

        cls.infra1 = SopInfra.objects.get(site__slug='site-1')
        cls.infra2 = SopInfra.objects.get(site__slug='site-2')
        cls.infra3 = SopInfra.objects.get(site__slug='site-3')


    def test_master_ad_cumulative_users(self):
        """Test that valid MASTER SopInfra computes ad_cumulative_users"""
        self.assertEqual(self.infra1.ad_cumulative_users, 442)
        self.assertEqual(self.infra2.ad_cumulative_users, 42)
        self.assertEqual(self.infra3.ad_cumulative_users, 0)


    def test_master_ad_cumulative_users_children(self):
        """Test that valid MASTER SopInfra with children computes ad_cumulative_users"""
        self.infra1.master_site = self.infra2.site

        # need to save bc ad_cumulative_users algorithm uses db queryset
        self.infra1.full_clean()
        self.infra1.save()
        self.infra2.full_clean()
        self.infra1.save()

        self.assertEqual(self.infra1.ad_cumulative_users, 442)
        self.assertEqual(self.infra2.ad_cumulative_users, 484)


    def test_master_wan_computed_users(self):
        """Test that valid MASTER SopInfra computes wan_computed_users"""
        self.assertEqual(self.infra1.wan_computed_users, 442)
        self.assertEqual(self.infra2.wan_computed_users, 69)
        self.assertEqual(self.infra3.wan_computed_users, 19)


    def test_master_wan_computed_users_children(self):
        """Test that valid MASTER SopInfra with children computes wan_computed_users"""
        self.infra1.master_site = self.infra2.site

        # need to save bc ad_cumulative_users algorithm uses db queryset
        self.infra1.full_clean()
        self.infra1.save()
        self.infra2.full_clean()
        self.infra1.save()

        self.assertEqual(self.infra1.wan_computed_users, 442)
        self.assertEqual(self.infra2.wan_computed_users, 484)


    def test_master_mx_user_slice(self):
        """Test that valid MASTER SopInfra computes mx and user_slice"""

        self.assertEqual(self.infra1.site_mx_model, 'MX95')
        self.assertEqual(self.infra2.site_mx_model, 'MX85')
        self.assertEqual(self.infra3.site_mx_model, 'MX67')

        self.assertEqual(self.infra1.site_user_count, '200<500')
        self.assertEqual(self.infra2.site_user_count, '50<100')
        self.assertEqual(self.infra3.site_user_count, '10<20')


    def test_master_mx_user_slice_children(self):
        """Test that valid MASTER SopInfra with children computes mx and user_slice"""
        self.infra1.master_site = self.infra2.site
        self.infra2.ad_direct_users = 84

        # need to save bc ad_cumulative_users algorithm uses db queryset
        self.infra1.full_clean()
        self.infra1.save()
        self.infra2.full_clean()
        self.infra1.save()

        self.assertEqual(self.infra1.site_mx_model, None)
        self.assertEqual(self.infra2.site_mx_model, 'MX250')

        self.assertEqual(self.infra1.site_user_count, '200<500')
        self.assertEqual(self.infra2.site_user_count, '>500')


    def test_master_recommended_bandwidth(self):
        """Test that valid MASTER SopInfra computes recommended bandwidth"""

        # bw = wan * cm where cm depends of wan size
        self.assertEqual(self.infra1.wan_reco_bw, round(442 * 2.5 ))
        self.assertEqual(self.infra2.wan_reco_bw, round(69 * 3))
        self.assertEqual(self.infra3.wan_reco_bw, round(19 * 4))


        self.infra2.est_cumulative_users = 9
        self.infra2.ad_direct_users = 8
        self.infra2.full_clean()
        self.infra2.save()

        self.assertEqual(self.infra2.wan_reco_bw, round(9 * 5))


    def test_master_recommended_bandwidth_children(self):
        """Test that valid MASTER SopInfra with children computes recommended bandwidth"""
        self.infra1.master_site = self.infra2.site
        self.infra2.ad_direct_users = 84

        # need to save bc ad_cumulative_users algorithm uses db queryset
        self.infra1.full_clean()
        self.infra1.save()
        self.infra2.full_clean()
        self.infra1.save()

        self.assertEqual(self.infra1.wan_reco_bw, None)
        self.assertEqual(self.infra2.wan_reco_bw, round(526 * 2.5))


    def test_master_compute_sdwanha(self):
        """Test that valid MASTER SopInfra computes default fields"""

        self.infra2.site_type_vip = 'true'
        self.infra3.site.status = 'candidate'

        self.infra2.full_clean()
        self.infra2.save()
        self.infra3.full_clean()
        self.infra3.save()

        self.assertEqual(self.infra1.sdwanha, '-HA-')
        self.assertEqual(self.infra1.criticity_stars, '**')

        self.assertEqual(self.infra2.sdwanha, '-HA-')
        self.assertEqual(self.infra2.criticity_stars, '***')

        self.assertEqual(self.infra3.sdwanha, '-NO NETWORK-')
        self.assertEqual(self.infra3.criticity_stars, None)

        self.infra1.ad_direct_users = 9
        self.infra1.full_clean()
        self.infra1.save()

        self.assertEqual(self.infra1.sdwanha, '-NHA-')
        self.assertEqual(self.infra1.criticity_stars, '*')

