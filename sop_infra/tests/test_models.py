from django.test import TestCase
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError

from dcim.models import Site, Location

from ..models import SopInfra


class SopInfraTestCase(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.minas = Site.objects.create(
            name="Minas Tirith",
            slug="minas-tirith",
            status="active"
        )
        cls.bree = Site.objects.create(
            name="Bree",
            slug="bree",
            status="candidate"
        )
        cls.rivendell = Site.objects.create(
            name="Rivendell",
            slug="rivendell",
            status="starting"
        )
        cls.moria = Site.objects.create(
            name="Moria",
            slug="moria",
            status="unknown"
        )
        cls.gondor = Location.objects.create(
            name="Gondor",
            slug="gondor",
            site=cls.minas
        )
        cls.ad:int = 42
        cls.est:int = 69

    def test_slave_site_wrong_location_db(self):
        """Test that invalid master_site raises IntegrityError"""
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                i = SopInfra.objects.create(
                    site=self.minas,
                    site_sdwan_master_location=self.gondor,
                    master_site=self.gondor.site
                )

    def test_slave_site_wrong_location_clean(self): 
        """Test that invalid master_location raises ValidationError""" 
        with self.assertRaises(ValidationError):
            i = SopInfra.objects.create(
                site=self.minas,
                site_sdwan_master_location=self.gondor
            )
            i.full_clean()

    def test_slave_site_sdwan(self):
        """Test that valid slave site creates '-SLAVE SITE-' sdwanha"""
        i = SopInfra.objects.create(
            site=self.bree,
            site_sdwan_master_location=self.gondor
        )
        i.full_clean()
        self.assertTrue(i.sdwanha == '-SLAVE SITE-')

    def test_count_wan_computed_users(self):
        """Test that valid SopInfra computes wan users"""
        i_act = SopInfra.objects.create(
            site=self.minas,
            ad_cumul_user=self.ad,
            est_cumulative_users=self.est
        )
        i_cand = SopInfra.objects.create(
            site=self.bree,
            ad_cumul_user=self.ad,
            est_cumulative_users=self.est
        )
        i_star = SopInfra.objects.create(
            site=self.rivendell,
            ad_cumul_user=self.ad,
            est_cumulative_users=self.est
        )
        i_unk = SopInfra.objects.create(
            site=self.moria,
            ad_cumul_user=self.ad,
            est_cumulative_users=self.est
        )
        
        i_act.full_clean()
        i_cand.full_clean()
        i_star.full_clean()
        i_unk.full_clean()

        # active -> wan = ad
        self.assertTrue(i_act.wan_computed_users == 42)
        # candidate -> wan = est
        self.assertTrue(i_cand.wan_computed_users == 69)
        # starting -> wan = est ? est > wan : ad
        self.assertTrue(i_star.wan_computed_users == 69)
        # unkown -> wan = 0
        self.assertTrue(i_unk.wan_computed_users == 0)

    def test_count_site_users(self):
        """Test that valid SopInfra computes site users"""
        i = SopInfra.objects.create(
            site=self.minas,
            ad_cumul_user=self.ad,
            est_cumulative_users=self.est
        )
        i.full_clean()
        self.assertTrue(i.site_user_count == '20<50')

        i.ad_cumul_user = 235
        i.full_clean()
        self.assertTrue(i.site_user_count == '200<500')

        i.ad_cumul_user = 9
        i.full_clean()
        self.assertTrue(i.site_user_count == '<10')

    def test_recommended_bandwidth(self):
        """Test that valid SopInfra computes recomended bandwidth"""
        i = SopInfra.objects.create(
            site=self.minas,
            ad_cumul_user=self.ad,
            est_cumulative_users=self.est
        )
        # reco bw = wan * cm
        i.full_clean()
        self.assertTrue(i.wan_reco_bw == 42 * 4)

        i.ad_cumul_user = 235
        i.full_clean()
        self.assertTrue(i.wan_reco_bw == round(235 * 2.5))

        i.ad_cumul_user = 9
        i.full_clean()
        self.assertTrue(i.wan_reco_bw == 9 * 5)

    def test_sdwanha_no_network(self):
        """Test that valid SopInfra computes SDWANHA value"""
        i = SopInfra.objects.create(site=self.bree)
        i.full_clean()
        self.assertTrue(i.sdwanha == '-NO NETWORK-')

    def test_sdwanha_nha(self):
        """Test that valid SopInfra computes SDWANHA value"""
        i = SopInfra.objects.create(site=self.minas)
        i.full_clean()
        self.assertTrue(i.sdwanha == '-NHA-')

    def test_sdwanha_ha(self):
        """Test that valid SopInfra computes SDWANHA value"""
        i = SopInfra.objects.create(
            site=self.minas,
            site_type_vip='true',
        )
        i.full_clean()
        self.assertTrue(i.sdwanha == '-HA-')

        j = SopInfra.objects.create(
            site=self.rivendell,
            site_infra_sysinfra='sysclust'
        )
        j.full_clean()
        self.assertTrue(j.sdwanha == '-HA-')


