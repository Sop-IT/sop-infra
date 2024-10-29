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
            status="active"
        )
        cls.gondor = Location.objects.create(
            name="Gondor",
            slug="gondor",
            site=cls.minas
        )

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

