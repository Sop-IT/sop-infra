from django.urls import reverse

from utilities.testing import TestCase
from dcim.models import Site

from sop_infra.models import SopInfra


VIEW_PERM = 'sop_infra.view_sopinfra'


class SopInfraApiTestCase(TestCase):

    user_permissions = ()

    @classmethod
    def setUpTestData(cls):

        sites = (
            Site(name='site 1', slug='site-1', status='active'),
            Site(name='site 2', slug='site-2', status='retired'),
        )
        for site in sites:
            site.full_clean()
            site.save()

        infras = (
            SopInfra(site=Site.objects.get(slug='site-1')),
            SopInfra(site=Site.objects.get(slug='site-2'))
        )
        for infra in infras:
            infra.full_clean()
            infra.save()


    def get_action_url(self, action, instance=None):
        """reverse sopinfra plugin api url with action"""
        url = f'plugins-api:sop_infra-api:sopinfra-{action}'

        if instance is None:
            return reverse(url)

        return reverse(url, kwargs={'pk': instance.pk})


    def test_detail_no_perm(self):
        """get api object no perm"""
        instance = SopInfra.objects.first()
        url = self.get_action_url('detail', instance)

        response = self.client.get(url)
        self.assertHttpStatus(response, 403)


    def test_detail_perm(self):
        """get api object perm"""
        instance = SopInfra.objects.first()
        url = self.get_action_url('detail', instance)

        self.add_permissions(VIEW_PERM)
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)


    def test_list_no_perm(self):
        """get api list no perm"""
        url = self.get_action_url('list')

        response = self.client.get(url)
        self.assertHttpStatus(response, 403)


    def test_list_perm(self):
        """get api list perm"""
        url = self.get_action_url('list')

        self.add_permissions(VIEW_PERM)
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data['results']), 2)

