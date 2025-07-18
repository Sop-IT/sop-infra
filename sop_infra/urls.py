from django.urls import path

from netbox.views.generic import ObjectChangeLogView, ObjectJournalView
from sop_infra.views.infra import SopInfraSyncAdUsers, SopMerakiClaimView, SopMerakiCreateNetworksView, SopMerakiEditView

from .views import *
from .models import *


app_name = 'sop_infra'


urlpatterns = [

    path('trisearch', SopMerakiTriSearchView.as_view(), name='trisearch'),
    path('sync_ad_users', SopInfraSyncAdUsers.as_view(), name='sync_ad_users'),
    

    path('jsonexports/adusers', SopInfraJsonExportsAdUsers.as_view(), name='jsonexports_adusers'),
    path('jsonexports/adsites', SopInfraJsonExportsAdSites.as_view(), name='jsonexports_adsites'),

    path('<int:pk>/', SopInfraDetailView.as_view(), name='sopinfra_detail'),
    # path('add/', SopInfraAddView.as_view(), name='sopinfra_add'),
    # path('add/<int:pk>/', SopInfraAddView.as_view(), name='sopinfra_add'),
    path('edit/<int:pk>/', SopInfraEditView.as_view(), name='sopinfra_edit'),
    path('delete/<int:pk>/', SopInfraDeleteView.as_view(), name='sopinfra_delete'),
    path('refresh/', SopInfraRefreshView.as_view(), name='sopinfra_refresh'),
    path('journal/<int:pk>', ObjectJournalView.as_view(), name='sopinfra_journal', kwargs={'model': SopInfra}),
    path('changelog/<int:pk>', ObjectChangeLogView.as_view(), name='sopinfra_changelog', kwargs={'model': SopInfra}),

    # ____________________
    # list views
    path('list/', SopInfraListView.as_view(), name='sopinfra_list'),
  

    # ____________________
    # SOP INFRA - SOP MERAKI VIEWS
    path('edit_meraki/<int:pk>/', SopMerakiEditView.as_view(), name='sopmeraki_edit'),
    path('create_meraki_network/<int:pk>/', SopMerakiCreateNetworksView.as_view(), name='create_meraki_network'),
    path('claim_meraki_devices/<int:pk>/', SopMerakiClaimView.as_view(), name='claim_meraki_devices'),
    


    # #____________________
    # # bulk views
    # path('delete/', SopInfraBulkDeleteView.as_view(), name='sopinfra_bulk_delete'),
    # path('edit/', SopInfraBulkEditView.as_view(), name='sopinfra_bulk_edit'),

    #____________________
    # endpoint
    path('endpoint/', PrismaEndpointListView.as_view(), name='prismaendpoint_list'),
    path('endpoint/<int:pk>', PrismaEndpointDetailView.as_view(), name='prismaendpoint_detail'),
    path('endpoint/add/', PrismaEndpointEditView.as_view(), name='prismaendpoint_add'),
    path('endpoint/edit/<int:pk>', PrismaEndpointEditView.as_view(), name='prismaendpoint_edit'),
    path('endpoint/delete/<int:pk>', PrismaEndpointDeleteView.as_view(), name='prismaendpoint_delete'),
    path('endpoint/journal/<int:pk>', ObjectJournalView.as_view(), name='prismaendpoint_journal', kwargs={'model': PrismaEndpoint}),
    path('endpoint/changelog/<int:pk>', ObjectChangeLogView.as_view(), name='prismaendpoint_changelog', kwargs={'model': PrismaEndpoint}),

    #____________________
    # access location
    path('access_location/', PrismaAccessLocationListView.as_view(), name='prismaaccesslocation_list'),
    path('access_location/<int:pk>', PrismaAccessLocationDetailView.as_view(), name='prismaaccesslocation_detail'),
    path('access_location/add/', PrismaAccessLocationEditView.as_view(), name='prismaaccesslocation_add'),
    path('access_location/edit/<int:pk>', PrismaAccessLocationEditView.as_view(), name='prismaaccesslocation_edit'),
    path('access_location/delete/<int:pk>', PrismaAccessLocationDeleteView.as_view(), name='prismaaccesslocation_delete'),
    path('access_location/journal/<int:pk>', ObjectJournalView.as_view(), name='prismaaccesslocation_journal', kwargs={'model': PrismaAccessLocation}),
    path('access_location/changelog/<int:pk>', ObjectChangeLogView.as_view(), name='prismaaccesslocation_changelog', kwargs={'model': PrismaAccessLocation}),
    path('access_location/refresh/', PrismaAccessLocationRefreshView.as_view(), name='prismaaccesslocation_refresh'),

    #____________________
    # computed access location
    path('computed_location/', PrismaComputedAccessLocationListView.as_view(), name='prismacomputedaccesslocation_list'),
    path('computed_location/<int:pk>', PrismaComputedAccessLocationDetailView.as_view(), name='prismacomputedaccesslocation_detail'),
    path('computed_location/add/', PrismaComputedAccessLocationEditView.as_view(), name='prismacomputedaccesslocation_add'),
    path('computed_location/edit/<int:pk>', PrismaComputedAccessLocationEditView.as_view(), name='prismacomputedaccesslocation_edit'),
    path('computed_location/delete/<int:pk>', PrismaComputedAccessLocationDeleteView.as_view(), name='prismacomputedaccesslocation_delete'),
    path('computed_location/journal/<int:pk>', ObjectJournalView.as_view(), name='prismacomputedaccesslocation_journal', kwargs={'model': PrismaComputedAccessLocation}),
    path('computed_location/changelog/<int:pk>', ObjectChangeLogView.as_view(), name='prismacomputedaccesslocation_changelog', kwargs={'model': PrismaComputedAccessLocation}),


    #____________________
    # sopmeraki dash
    path('sopmerakidash/', SopMerakiDashListView.as_view(), name='sopmerakidash_list'),
    path('sopmerakidash/add/', SopMerakiDashEditView.as_view(), name='sopmerakidash_add'),
    path('sopmerakidash/<int:pk>/', SopMerakiDashView.as_view(), name='sopmerakidash_detail'),
    path('sopmerakidash/<int:pk>/edit/', SopMerakiDashEditView.as_view(), name='sopmerakidash_edit'),
    path('sopmerakidash/<int:pk>/delete/', SopMerakiDashDeleteView.as_view(), name='sopmerakidash_delete'),
    path('sopmerakidash/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='sopmerakidash_changelog', kwargs={'model': SopMerakiDash}),
    path('sopmerakidash/refresh/', SopMerakiRefreshDashboardsView.as_view(), name='sopmerakidash_refresh'),

    #____________________
    # meraki org
    path('sopmerakiorg/', SopMerakiOrgListView.as_view(), name='sopmerakiorg_list'),
    path('sopmerakiorg/add/', SopMerakiOrgEditView.as_view(), name='sopmerakiorg_add'),
    path('sopmerakiorg/<int:pk>/', SopMerakiOrgView.as_view(), name='sopmerakiorg_detail'),
    path('sopmerakiorg/<int:pk>/edit/', SopMerakiOrgEditView.as_view(), name='sopmerakiorg_edit'),
    path('sopmerakiorg/<int:pk>/delete/', SopMerakiOrgDeleteView.as_view(), name='sopmerakiorg_delete'),
    path('sopmerakiorg/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='sopmerakiorg_changelog', kwargs={'model': SopMerakiOrg}),

    #____________________
    # meraki net
    path('sopmerakinet/', SopMerakiNetListView.as_view(), name='sopmerakinet_list'),
    path('sopmerakinet/add/', SopMerakiNetEditView.as_view(), name='sopmerakinet_add'),
    path('sopmerakinet/<int:pk>/', SopMerakiNetView.as_view(), name='sopmerakinet_detail'),
    path('sopmerakinet/<int:pk>/edit/', SopMerakiNetEditView.as_view(), name='sopmerakinet_edit'),
    path('sopmerakinet/<int:pk>/delete/', SopMerakiNetDeleteView.as_view(), name='sopmerakinet_delete'),
    path('sopmerakinet/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='sopmerakinet_changelog', kwargs={'model': SopMerakiNet}),

    #____________________
    # meraki dev
    path('sopmerakidevice/', SopMerakiDeviceListView.as_view(), name='sopmerakidevice_list'),
    path('sopmerakidevice/add/', SopMerakiDeviceEditView.as_view(), name='sopmerakidevice_add'),
    path('sopmerakidevice/<int:pk>/', SopMerakiDeviceView.as_view(), name='sopmerakidevice_detail'),
    path('sopmerakidevice/<int:pk>/edit/', SopMerakiDeviceEditView.as_view(), name='sopmerakidevice_edit'),
    path('sopmerakidevice/<int:pk>/delete/', SopMerakiDeviceDeleteView.as_view(), name='sopmerakidevice_delete'),
    path('sopmerakidevice/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='sopmerakidevice_changelog', kwargs={'model': SopMerakiDevice}),

]

