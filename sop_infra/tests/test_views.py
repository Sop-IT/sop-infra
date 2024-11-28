from django.urls import reverse

from utilities.testing import TestCase
from ipam.models import IPAddress
from dcim.models import Site

from sop_infra.models import *


__all__ = (
    "SopInfraViewTestCase",
    "PrismaEndpointViewTestCase",
    "PrismaAccessLocationViewTestCase",
    "PrismaComputedAccessLocationViewTestCase",
)


class InfraViewTestCaseMixin:

    user_permissions = ()
    model = None

    ADD_PERM = None
    EDIT_PERM = None
    VIEW_PERM = None

    def get_action_url(self, action, instance=None):
        """reverse sopinfra plugin url with action"""
        url = f"plugins:sop_infra:{self.model._meta.model_name}_{action}"

        if instance is None:
            return reverse(url)

        return reverse(url, kwargs={"pk": instance.pk})

    def test_list_no_perm(self):
        """test list view no perm"""
        url = self.get_action_url("list")

        response = self.client.get(url)
        self.assertHttpStatus(response, 403)

    def test_list_perm(self):
        """test list view perm"""
        url = self.get_action_url("list")

        self.add_permissions(self.VIEW_PERM)
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)

    def test_add_no_perm(self):
        """test add view no perm"""
        url = self.get_action_url("add")

        response = self.client.get(url)
        self.assertHttpStatus(response, 403)

    def test_add_perm(self):
        """test add view perm"""
        url = self.get_action_url("add")

        self.add_permissions(self.ADD_PERM)
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)

    def test_detail_no_perm(self):
        """test detail no perm"""
        instance = self.model.objects.first()
        url = self.get_action_url("detail", instance)

        response = self.client.get(url)
        self.assertHttpStatus(response, 403)

    def test_detail_perm(self):
        """test detail perm"""
        instance = self.model.objects.first()
        url = self.get_action_url("detail", instance)

        self.add_permissions(self.VIEW_PERM)
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)

    def test_edit_no_perm(self):
        """test edit no perm"""
        instance = self.model.objects.first()
        url = self.get_action_url("edit", instance)

        response = self.client.get(url)
        self.assertHttpStatus(response, 403)

    def test_edit_perm(self):
        """test detail perm"""
        instance = self.model.objects.first()
        url = self.get_action_url("edit", instance)

        self.add_permissions(self.EDIT_PERM)
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)


class SopInfraViewTestCase(TestCase, InfraViewTestCaseMixin):

    model = SopInfra

    ADD_PERM = "sop_infra.add_sopinfra"
    EDIT_PERM = "sop_infra.change_sopinfra"
    VIEW_PERM = "sop_infra.view_sopinfra"

    @classmethod
    def setUpTestData(cls):

        sites = (
            Site(name="site 1", slug="site-1", status="active"),
            Site(name="site 2", slug="site-2", status="retired"),
        )
        for site in sites:
            site.full_clean()
            site.save()

    def test_tab_view_no_perm(self):
        """test tab no perm"""
        instance = Site.objects.first()
        url = f"/dcim/sites/{instance.pk}/infra/"

        self.add_permissions("dcim.view_site")
        response = self.client.get(url)
        self.assertHttpStatus(response, 403)

    def test_tab_view_perm(self):
        """test tab perm"""
        instance = Site.objects.first()
        url = f"/dcim/sites/{instance.pk}/infra/"

        self.add_permissions("dcim.view_site")
        self.add_permissions(self.VIEW_PERM)
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)

    def test_tab_view_context(self):
        """test tab view context"""
        site = Site.objects.first()
        infra = SopInfra.objects.get(site=site)
        url = f"/dcim/sites/{site.pk}/infra/"

        for i in range(3):
            s = Site.objects.create(name=f"salut{i}", slug=f"salut{i}")
            s.full_clean()
            s.save()
            t = SopInfra.objects.get(site__id=s.pk)
            t.master_site = site
            t.full_clean()
            t.save()

        self.add_permissions("dcim.view_site")
        self.add_permissions(self.VIEW_PERM)
        response = self.client.get(url)
        context = response.context["context"]

        self.assertHttpStatus(response, 200)
        self.assertEqual(context["sop_infra"], infra)
        self.assertEqual(context["count_slave_infra"], 3)
        self.assertEqual(context["count_slave"], 3)

    def test_recompute_sizing_no_perm(self):
        """test recompute sizing no perm"""
        instance = Site.objects.first()
        url = self.get_action_url("refresh")

        response = self.client.get(url)
        self.assertHttpStatus(response, 403)

        response = self.client.get(f"{url}?qs={instance.pk}")
        self.assertHttpStatus(response, 403)

    def test_recompute_sizing_perm(self):
        """test recompute sizing with perm"""
        instance = Site.objects.first()
        url = self.get_action_url("refresh")

        self.add_permissions(self.EDIT_PERM)
        response = self.client.get(f"{url}?qs={instance.pk}")
        self.assertHttpStatus(response, 200)

    def test_tab_view_perm_none(self):
        """test tab view with no object"""
        instance = Site.objects.first()
        url = f"/dcim/sites/{instance.pk}/infra/"

        SopInfra.objects.get(site=instance).delete()
        self.add_permissions("dcim.view_site")
        self.add_permissions(self.VIEW_PERM)

        response = self.client.get(url)
        self.assertHttpStatus(response, 200)


class PrismaEndpointViewTestCase(TestCase, InfraViewTestCaseMixin):

    model = PrismaEndpoint

    ADD_PERM = "sop_infra.add_prismaendpoint"
    EDIT_PERM = "sop_infra.change_prismaendpoint"
    VIEW_PERM = "sop_infra.view_prismaendpoint"

    @classmethod
    def setUpTestData(cls):

        ip_address = IPAddress(address="12.42.56.78/32")
        ip_address.full_clean()
        ip_address.save()

        compute_location = PrismaComputedAccessLocation(
            name="compute1",
            slug="compute1",
            bandwidth=42,
            strata_id="</>",
            strata_name="ha/nha",
        )
        compute_location.full_clean()
        compute_location.save()

        access_location = PrismaAccessLocation(
            name="loca1", slug="loca1", compute_location=compute_location
        )
        access_location.full_clean()
        access_location.save()

        model = PrismaEndpoint(
            name="salut",
            slug="salut",
            ip_address=ip_address,
            access_location=access_location,
        )
        model.full_clean()
        model.save()


class PrismaAccessLocationViewTestCase(TestCase, InfraViewTestCaseMixin):

    model = PrismaAccessLocation

    ADD_PERM = "sop_infra.add_prismaaccesslocation"
    EDIT_PERM = "sop_infra.change_prismaaccesslocation"
    VIEW_PERM = "sop_infra.view_prismaaccesslocation"

    @classmethod
    def setUpTestData(cls):

        compute_location = PrismaComputedAccessLocation(
            name="compute1",
            slug="compute1",
            bandwidth=42,
            strata_id="</>",
            strata_name="ha/nha",
        )
        compute_location.full_clean()
        compute_location.save()

        access_location = PrismaAccessLocation(
            name="loca1", slug="loca1", compute_location=compute_location
        )
        access_location.full_clean()
        access_location.save()


class PrismaComputedAccessLocationViewTestCase(TestCase, InfraViewTestCaseMixin):

    model = PrismaComputedAccessLocation

    ADD_PERM = "sop_infra.add_prismacomputedaccesslocation"
    EDIT_PERM = "sop_infra.change_prismacomputedaccesslocation"
    VIEW_PERM = "sop_infra.view_prismacomputedaccesslocation"

    @classmethod
    def setUpTestData(cls):

        compute_location = PrismaComputedAccessLocation(
            name="compute1",
            slug="compute1",
            bandwidth=42,
            strata_id="</>",
            strata_name="ha/nha",
        )
        compute_location.full_clean()
        compute_location.save()
