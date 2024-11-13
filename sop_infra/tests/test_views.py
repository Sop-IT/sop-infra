from django.test import TestCase
from django.urls import reverse

from dcim.models import Site, Location

from sop_infra.models import SopInfra


class SopInfraViewTestCase(TestCase):

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
        cls.gondor = Location.objects.create(
            name="Gondor",
            slug="gondor",
            site=cls.minas
        )

    def test_sopinfra_view(self):
        infra = SopInfra.objects.create(
            site=self.bree
        )
        infra.full_clean()
        infra.save()
        url = reverse('plugins:sop_infra:sopinfra_detail', args=[infra.pk])
        response = self.client.get(url)
        self.assertTrue(response.status_code, 200)

    def test_sopinfra_tab_view(self):
        url = f'/dcim/sites/{self.minas.pk}/infra'
        response = self.client.get(url)
        self.assertTrue(response.status_code, 200)

    def test_sopinfra_add_view(self):

        url = reverse('plugins:sop_infra:sopinfra_add', args=[self.minas.pk])
        response = self.client.get(url)
        self.assertTrue(response.status_code, 200)

        url = reverse('plugins:sop_infra:meraki_add', args=[self.minas.pk])
        response = self.client.get(url)
        self.assertTrue(response.status_code, 200)

        url = reverse('plugins:sop_infra:sizing_add', args=[self.bree.pk])
        response = self.client.get(url)
        self.assertTrue(response.status_code, 200)

        url = reverse('plugins:sop_infra:class_add', args=[self.minas.pk])
        response = self.client.get(url)
        self.assertTrue(response.status_code, 200)

    def test_sopinfra_edit_view(self):

        infra = SopInfra.objects.create(site=self.minas,)
        infra.full_clean()
        infra.save()

        url = reverse('plugins:sop_infra:sopinfra_edit', args=[infra.pk])
        response = self.client.get(url)
        self.assertTrue(response.status_code, 200)

        url = reverse('plugins:sop_infra:meraki_edit', args=[infra.pk])
        response = self.client.get(url)
        self.assertTrue(response.status_code, 200)

        url = reverse('plugins:sop_infra:sizing_edit', args=[infra.pk])
        response = self.client.get(url)
        self.assertTrue(response.status_code, 200)

        url = reverse('plugins:sop_infra:class_edit', args=[infra.pk])
        response = self.client.get(url)
        self.assertTrue(response.status_code, 200)

