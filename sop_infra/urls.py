from django.urls import include, path
from utilities.urls import get_model_urls

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

    # ========================================================================
    # list views
    path('list/', SopInfraListView.as_view(), name='sopinfra_list'),
  

    # ========================================================================
    # SOP INFRA - SOP MERAKI VIEWS
    path('edit_meraki/<int:pk>/', SopMerakiEditView.as_view(), name='sopmeraki_edit'),
    path('create_meraki_network/<int:pk>/', SopMerakiCreateNetworksView.as_view(), name='create_meraki_network'),
    path('claim_meraki_devices/<int:pk>/', SopMerakiClaimView.as_view(), name='claim_meraki_devices'),
    

    # ========================================================================
    # SOP INFRA - DEVICE SETTINGS VIEWS
    path('sopdevicesettings/<int:pk>/', SopDeviceSettingDetailView.as_view(), name='sopdevicesetting_detail'),
    path('sopdevicesettings/edit/<int:pk>/', SopDeviceSettingEditView.as_view(), name='sopdevicesetting_edit'),
    path('sopdevicesettings/try_manage_in_netbox/<int:pk>/', SopDeviceSettingTryManageInNetbox.as_view(), name='sopdevicesetting_try_manage_in_netbox'),
 

    # ========================================================================
    # SOP INFRA - SWITCH TEMPLATE VIEWS
    path('sopswitchtemplate/<int:pk>/', SopSwitchTemplateDetailView.as_view(), name='sopswitchtemplate_detail'),
    path('sopswitchtemplate/add/', SopSwitchTemplateEditView.as_view(), name='sopswitchtemplate_add'),
    path('sopswitchtemplate/edit/<int:pk>/', SopSwitchTemplateEditView.as_view(), name='sopswitchtemplate_edit'),
    path('sopswitchtemplate/delete/<int:pk>/', SopSwitchTemplateDeleteView.as_view(), name='sopswitchtemplate_delete'),
    path('sopswitchtemplate/list/', SopSwitchTemplateListView.as_view(), name='sopswitchtemplate_list'),   
    path('sopswitchtemplate/journal/<int:pk>', ObjectJournalView.as_view(), name='sopswitchtemplate_journal', kwargs={'model': SopSwitchTemplate}),
    path('sopswitchtemplate/changelog/<int:pk>', ObjectChangeLogView.as_view(), name='sopswitchtemplate_changelog', kwargs={'model': SopSwitchTemplate}),


    # ========================================================================
    # endpoint
    path('endpoint/', PrismaEndpointListView.as_view(), name='prismaendpoint_list'),
    path('endpoint/<int:pk>', PrismaEndpointDetailView.as_view(), name='prismaendpoint_detail'),
    path('endpoint/add/', PrismaEndpointEditView.as_view(), name='prismaendpoint_add'),
    path('endpoint/edit/<int:pk>', PrismaEndpointEditView.as_view(), name='prismaendpoint_edit'),
    path('endpoint/delete/<int:pk>', PrismaEndpointDeleteView.as_view(), name='prismaendpoint_delete'),
    path('endpoint/journal/<int:pk>', ObjectJournalView.as_view(), name='prismaendpoint_journal', kwargs={'model': PrismaEndpoint}),
    path('endpoint/changelog/<int:pk>', ObjectChangeLogView.as_view(), name='prismaendpoint_changelog', kwargs={'model': PrismaEndpoint}),

    # ========================================================================
    # access location
    path('access_location/', PrismaAccessLocationListView.as_view(), name='prismaaccesslocation_list'),
    path('access_location/<int:pk>', PrismaAccessLocationDetailView.as_view(), name='prismaaccesslocation_detail'),
    path('access_location/add/', PrismaAccessLocationEditView.as_view(), name='prismaaccesslocation_add'),
    path('access_location/edit/<int:pk>', PrismaAccessLocationEditView.as_view(), name='prismaaccesslocation_edit'),
    path('access_location/delete/<int:pk>', PrismaAccessLocationDeleteView.as_view(), name='prismaaccesslocation_delete'),
    path('access_location/journal/<int:pk>', ObjectJournalView.as_view(), name='prismaaccesslocation_journal', kwargs={'model': PrismaAccessLocation}),
    path('access_location/changelog/<int:pk>', ObjectChangeLogView.as_view(), name='prismaaccesslocation_changelog', kwargs={'model': PrismaAccessLocation}),
    path('access_location/refresh/', PrismaAccessLocationRefreshView.as_view(), name='prismaaccesslocation_refresh'),

    # ========================================================================
    # computed access location
    path('computed_location/', PrismaComputedAccessLocationListView.as_view(), name='prismacomputedaccesslocation_list'),
    path('computed_location/<int:pk>', PrismaComputedAccessLocationDetailView.as_view(), name='prismacomputedaccesslocation_detail'),
    path('computed_location/add/', PrismaComputedAccessLocationEditView.as_view(), name='prismacomputedaccesslocation_add'),
    path('computed_location/edit/<int:pk>', PrismaComputedAccessLocationEditView.as_view(), name='prismacomputedaccesslocation_edit'),
    path('computed_location/delete/<int:pk>', PrismaComputedAccessLocationDeleteView.as_view(), name='prismacomputedaccesslocation_delete'),
    path('computed_location/journal/<int:pk>', ObjectJournalView.as_view(), name='prismacomputedaccesslocation_journal', kwargs={'model': PrismaComputedAccessLocation}),
    path('computed_location/changelog/<int:pk>', ObjectChangeLogView.as_view(), name='prismacomputedaccesslocation_changelog', kwargs={'model': PrismaComputedAccessLocation}),

    # ========================================================================
    # sopmeraki dash
    path('sopmerakidash/', SopMerakiDashListView.as_view(), name='sopmerakidash_list'),
    path('sopmerakidash/add/', SopMerakiDashEditView.as_view(), name='sopmerakidash_add'),
    path('sopmerakidash/<int:pk>/', SopMerakiDashView.as_view(), name='sopmerakidash_detail'),
    path('sopmerakidash/<int:pk>/edit/', SopMerakiDashEditView.as_view(), name='sopmerakidash_edit'),
    path('sopmerakidash/<int:pk>/delete/', SopMerakiDashDeleteView.as_view(), name='sopmerakidash_delete'),
    path('sopmerakidash/refresh/', SopMerakiDashRefreshChooseView.as_view(), name='sopmerakidash_refresh_choose'),
    path('sopmerakidash/<int:pk>/refresh/', SopMerakiDashRefreshView.as_view(), name='sopmerakidash_refresh'),
    path('sopmerakidash/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='sopmerakidash_changelog', kwargs={'model': SopMerakiDash}),

    # ========================================================================
    # meraki org
    path('sopmerakiorg/', SopMerakiOrgListView.as_view(), name='sopmerakiorg_list'),
    path('sopmerakiorg/add/', SopMerakiOrgEditView.as_view(), name='sopmerakiorg_add'),
    path('sopmerakiorg/<int:pk>/', SopMerakiOrgView.as_view(), name='sopmerakiorg_detail'),
    path('sopmerakiorg/<int:pk>/edit/', SopMerakiOrgEditView.as_view(), name='sopmerakiorg_edit'),
    path('sopmerakiorg/<int:pk>/delete/', SopMerakiOrgDeleteView.as_view(), name='sopmerakiorg_delete'),
    path('sopmerakiorg/refresh/', SopMerakiOrgRefreshChooseView.as_view(), name='sopmerakiorg_refresh_choose'),
    path('sopmerakiorg/<int:pk>/refresh/', SopMerakiOrgRefreshView.as_view(), name='sopmerakiorg_refresh'),
    path('sopmerakiorg/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='sopmerakiorg_changelog', kwargs={'model': SopMerakiOrg}),


    # ========================================================================
    # SopMerakiNet
    path('sopmerakinet/', SopMerakiNetListView.as_view(), name='sopmerakinet_list'),
    path('sopmerakinet/add/', SopMerakiNetEditView.as_view(), name='sopmerakinet_add'),
    path('sopmerakinet/<int:pk>/', SopMerakiNetView.as_view(), name='sopmerakinet_detail'),
    path('sopmerakinet/<int:pk>/edit/', SopMerakiNetEditView.as_view(), name='sopmerakinet_edit'),
    path('sopmerakinet/<int:pk>/delete/', SopMerakiNetDeleteView.as_view(), name='sopmerakinet_delete'),
    path('sopmerakinet/refresh/', SopMerakiNetRefreshChooseView.as_view(), name='sopmerakinet_refresh_choose'),
    path('sopmerakinet/<int:pk>/refresh/', SopMerakiNetRefreshView.as_view(), name='sopmerakinet_refresh'),
    path('sopmerakinet/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='sopmerakinet_changelog', kwargs={'model': SopMerakiNet}),

    # ========================================================================
    # SopMerakiSwitchStack
    path('sopmerakiswitchstack/', include(get_model_urls('sop_infra', 'sopmerakiswitchstack', detail=False))),
    path('sopmerakiswitchstack/<int:pk>/', include(get_model_urls('sop_infra', 'sopmerakiswitchstack'))),

    # ========================================================================
    # SopMerakiDevice
    path('sopmerakidevice/', include(get_model_urls('sop_infra', 'sopmerakidevice', detail=False))),
    path('sopmerakidevice/<int:pk>/', include(get_model_urls('sop_infra', 'sopmerakidevice'))),

]

