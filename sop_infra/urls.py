from django.urls import include, path


from netbox.views.generic.feature_views import ObjectJobsView
from utilities.urls import get_model_urls

from netbox.views.generic import ObjectChangeLogView, ObjectJournalView

from sop_infra.models.infra import SopInfra, SopSwitchTemplate
from sop_infra.views.infra import SopInfraHelperDhcp, SopInfraRefreshChooseView, SopMerakiClaimDevicesView, SopMerakiCreateNetworksView, SopMerakiEditView
from sop_infra.views.infra import SopInfraListView, SopInfraDetailView, SopInfraEditView, SopInfraDeleteView, SopInfraRecomputeSizingView
from sop_infra.views.infra import SopDeviceSettingDetailView, SopDeviceSettingEditView, SopDeviceSettingTryManageInNetbox
from sop_infra.views.infra import SopSwitchTemplateListView, SopSwitchTemplateDetailView, SopSwitchTemplateEditView, SopSwitchTemplateDeleteView
from sop_infra.views.infra import SopInfraSyncAdUsers,SopInfraJsonExportsAdUsers, SopInfraJsonExportsAdSites


from sop_infra.models.sopmeraki import SopMerakiDash, SopMerakiNet, SopMerakiOrg
from sop_infra.views.sopmeraki import SopMerakiDashListView, SopMerakiDashDeleteView, SopMerakiDashEditView,SopMerakiDashRefreshChooseView, SopMerakiDashRefreshView, SopMerakiDashView, SopMerakiDashConnectivityStatusesView, SopMerakiEnableUmbrellaSiteGroupView, SopMerakiEnableUmbrellaRegionView, SopMerakiEnableUmbrellaSiteView, SopMerakiEnableUmbrellaTenantGroupView, SopMerakiEnableUmbrellaTenantView, SopMerakiJsonConnectivityStatusSite, SopMerakiLinkUmbrellaSiteGroupView, SopMerakiLinkUmbrellaRegionView, SopMerakiLinkUmbrellaSiteView, SopMerakiLinkUmbrellaTenantGroupView, SopMerakiLinkUmbrellaTenantView, SopMerakiNetUpdateConnectivityStatusesView, SopMerakiOrgClaimView, SopMerakiOrgUpdateConnectivityStatusesView, SopMerakiPushGroupView, SopMerakiPushRegionView
from sop_infra.views.sopmeraki import SopMerakiOrgListView, SopMerakiOrgView, SopMerakiOrgEditView, SopMerakiOrgDeleteView, SopMerakiOrgRefreshView, SopMerakiOrgRefreshChooseView
from sop_infra.views.sopmeraki import SopMerakiNetListView, SopMerakiNetView, SopMerakiNetEditView, SopMerakiNetDeleteView, SopMerakiNetRefreshView, SopMerakiNetRefreshChooseView
from sop_infra.views.sopmeraki import SopMerakiDeviceListView, SopMerakiDeviceView, SopMerakiDeviceEditView, SopMerakiDeviceDeleteView
from sop_infra.views.sopmeraki import SopMerakiPushSiteView
# TODO -> move to infra
from sop_infra.views.sopmeraki import SopMerakiTriSearchView


from sop_infra.models.prisma import PrismaAccessLocation, PrismaComputedAccessLocation, PrismaEndpoint
from sop_infra.views.prisma import PrismaEndpointListView, PrismaEndpointDetailView, PrismaEndpointEditView, PrismaEndpointDeleteView
from sop_infra.views.prisma import  PrismaAccessLocationListView, PrismaAccessLocationDetailView, PrismaAccessLocationEditView, PrismaAccessLocationDeleteView
from sop_infra.views.prisma import  PrismaComputedAccessLocationListView, PrismaComputedAccessLocationDetailView, PrismaComputedAccessLocationEditView, PrismaComputedAccessLocationDeleteView, PrismaAccessLocationRefreshView



app_name = 'sop_infra'

urlpatterns = [

    path('trisearch', SopMerakiTriSearchView.as_view(), name='trisearch'),
    path('sync_ad_users', SopInfraSyncAdUsers.as_view(), name='sync_ad_users'),

    #path('sopmeraki/pushdbg/site/', SopMerakiPushSiteView.as_view(), name='sopmeraki_push'),
    path('sopmeraki/push/site/<int:pk>/', SopMerakiPushSiteView.as_view(), name='sopmeraki_push_site'),
    path('sopmeraki/push/region/<int:pk>/', SopMerakiPushRegionView.as_view(), name='sopmeraki_push_region'),
    path('sopmeraki/push/group/<int:pk>/', SopMerakiPushGroupView.as_view(), name='sopmeraki_push_group'),


    # MERAKI UMBRELLA views
    path('sopmeraki/umblink/site/<int:pk>/', SopMerakiLinkUmbrellaSiteView.as_view(), name='sopmeraki_umblink_site'),
    path('sopmeraki/umblink/region/<int:pk>/', SopMerakiLinkUmbrellaRegionView.as_view(), name='sopmeraki_umblink_region'),
    path('sopmeraki/umblink/sitegroup/<int:pk>/', SopMerakiLinkUmbrellaSiteGroupView.as_view(), name='sopmeraki_umblink_sitegroup'),
    path('sopmeraki/umblink/tenant/<int:pk>/', SopMerakiLinkUmbrellaTenantView.as_view(), name='sopmeraki_umblink_tenant'),
    path('sopmeraki/umblink/tenantgroup/<int:pk>/', SopMerakiLinkUmbrellaTenantGroupView.as_view(), name='sopmeraki_umblink_tenantgroup'),

    path('sopmeraki/umbenable/site/<int:pk>/', SopMerakiEnableUmbrellaSiteView.as_view(), name='sopmeraki_umbenable_site'),
    path('sopmeraki/umbenable/region/<int:pk>/', SopMerakiEnableUmbrellaRegionView.as_view(), name='sopmeraki_umbenable_region'),
    path('sopmeraki/umbenable/sitegroup/<int:pk>/', SopMerakiEnableUmbrellaSiteGroupView.as_view(), name='sopmeraki_umbenable_sitegroup'),
    path('sopmeraki/umbenable/tenant/<int:pk>/', SopMerakiEnableUmbrellaTenantView.as_view(), name='sopmeraki_umbenable_tenant'),
    path('sopmeraki/umbenable/tenantgroup/<int:pk>/', SopMerakiEnableUmbrellaTenantGroupView.as_view(), name='sopmeraki_umbenable_tenantgroup'),


    path('jsonexports/adusers', SopInfraJsonExportsAdUsers.as_view(), name='jsonexports_adusers'),
    path('jsonexports/adsites', SopInfraJsonExportsAdSites.as_view(), name='jsonexports_adsites'),

    path('jsonexports/connectivity_statuses/<str:ip>/', SopMerakiJsonConnectivityStatusSite.as_view(), name='jsonexports_connectivity_statuses_ip'),


    path('<int:pk>/', SopInfraDetailView.as_view(), name='sopinfra_detail'),
    # path('add/', SopInfraAddView.as_view(), name='sopinfra_add'),
    # path('add/<int:pk>/', SopInfraAddView.as_view(), name='sopinfra_add'),
    path('edit/<int:pk>/', SopInfraEditView.as_view(), name='sopinfra_edit'),
    path('delete/<int:pk>/', SopInfraDeleteView.as_view(), name='sopinfra_delete'),

    path('sopinfra/refresh/', SopInfraRefreshChooseView.as_view(), name='sopinfra_refresh_choose'),
    path('sopinfra/<int:pk>/journal', ObjectJournalView.as_view(), name='sopinfra_journal', kwargs={'model': SopInfra}),
    path('sopinfra/<int:pk>/changelog', ObjectChangeLogView.as_view(), name='sopinfra_changelog', kwargs={'model': SopInfra}),
    path('sopinfra/<int:pk>/jobs', ObjectJobsView.as_view(), name='sopinfra_jobs', kwargs={'model': SopInfra}),
    path('sopinfra/recompute_sizing', SopInfraRecomputeSizingView.as_view(), name='recompute_sizing'),

    # ========================================================================
    # list views
    path('list/', SopInfraListView.as_view(), name='sopinfra_list'),
  
    # ========================================================================
    # HELPERS
    path('helpers/dhcp', SopInfraHelperDhcp.as_view(), name='helpers_dhcp'),


    # ========================================================================
    # SOP INFRA - SOP MERAKI VIEWS
    path('edit_meraki/<int:pk>/', SopMerakiEditView.as_view(), name='sopmeraki_edit'),
    path('create_meraki_network/<int:pk>/', SopMerakiCreateNetworksView.as_view(), name='create_meraki_network'),
    path('sopmeraki/claim_devices/<int:pk>/', SopMerakiClaimDevicesView.as_view(), name='sopmeraki_claim_devices'),

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
    path('sopmerakidash/<int:pk>/update_connectivity_statuses/', SopMerakiDashConnectivityStatusesView.as_view(), name='sopmerakidash_update_connectivity_statuses'),
    path('sopmerakidash/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='sopmerakidash_changelog', kwargs={'model': SopMerakiDash}),
    path('sopmerakidash/<int:pk>/jobs/', ObjectJobsView.as_view(), name='sopmerakidash_jobs', kwargs={'model': SopMerakiDash}),

    # ========================================================================
    # meraki org
    path('sopmerakiorg/', SopMerakiOrgListView.as_view(), name='sopmerakiorg_list'),
    path('sopmerakiorg/add/', SopMerakiOrgEditView.as_view(), name='sopmerakiorg_add'),
    path('sopmerakiorg/<int:pk>/', SopMerakiOrgView.as_view(), name='sopmerakiorg_detail'),
    path('sopmerakiorg/<int:pk>/edit/', SopMerakiOrgEditView.as_view(), name='sopmerakiorg_edit'),
    path('sopmerakiorg/<int:pk>/delete/', SopMerakiOrgDeleteView.as_view(), name='sopmerakiorg_delete'),
    path('sopmerakiorg/refresh/', SopMerakiOrgRefreshChooseView.as_view(), name='sopmerakiorg_refresh_choose'),
    path('sopmerakiorg/<int:pk>/refresh/', SopMerakiOrgRefreshView.as_view(), name='sopmerakiorg_refresh'),
    path('sopmerakiorg/<int:pk>/update_connectivity_statuses/', SopMerakiOrgUpdateConnectivityStatusesView.as_view(), name='sopmerakiorg_update_connectivity_statuses'),
    path('sopmerakiorg/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='sopmerakiorg_changelog', kwargs={'model': SopMerakiOrg}),
    path('sopmerakiorg/<int:pk>/jobs/', ObjectJobsView.as_view(), name='sopmerakiorg_jobs', kwargs={'model': SopMerakiOrg}),
    path('sopmerakiorg/<int:pk>/claim_devices', SopMerakiOrgClaimView.as_view(), name='sopmerakiorg_claim_devices'),
    

    # ========================================================================
    # SopMerakiNet
    path('sopmerakinet/', SopMerakiNetListView.as_view(), name='sopmerakinet_list'),
    path('sopmerakinet/add/', SopMerakiNetEditView.as_view(), name='sopmerakinet_add'),
    path('sopmerakinet/<int:pk>/', SopMerakiNetView.as_view(), name='sopmerakinet_detail'),
    path('sopmerakinet/<int:pk>/edit/', SopMerakiNetEditView.as_view(), name='sopmerakinet_edit'),
    path('sopmerakinet/<int:pk>/delete/', SopMerakiNetDeleteView.as_view(), name='sopmerakinet_delete'),
    path('sopmerakinet/refresh/', SopMerakiNetRefreshChooseView.as_view(), name='sopmerakinet_refresh_choose'),
    path('sopmerakinet/<int:pk>/refresh/', SopMerakiNetRefreshView.as_view(), name='sopmerakinet_refresh'),
    path('sopmerakinet/<int:pk>/update_connectivity_statuses/', SopMerakiNetUpdateConnectivityStatusesView.as_view(), name='sopmerakinet_update_connectivity_statuses'),
    path('sopmerakinet/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='sopmerakinet_changelog', kwargs={'model': SopMerakiNet}),
    path('sopmerakinet/<int:pk>/jobs/', ObjectJobsView.as_view(), name='sopmerakinet_jobs', kwargs={'model': SopMerakiNet}),

    # ========================================================================
    # SopMerakiSwitchStack
    path('sopmerakiswitchstack/', include(get_model_urls('sop_infra', 'sopmerakiswitchstack', detail=False))),
    path('sopmerakiswitchstack/<int:pk>/', include(get_model_urls('sop_infra', 'sopmerakiswitchstack'))),

    # ========================================================================
    # SopMerakiDevice
    path('sopmerakidevice/', include(get_model_urls('sop_infra', 'sopmerakidevice', detail=False))),
    path('sopmerakidevice/<int:pk>/', include(get_model_urls('sop_infra', 'sopmerakidevice'))),

]

