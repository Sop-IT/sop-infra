from django.urls import path

from netbox.views.generic import ObjectChangeLogView, ObjectJournalView

from .views import *
from .models import *


app_name = 'sop_infra'


urlpatterns = [

    path('<int:pk>/', SopInfraDetailView.as_view(), name='sopinfra_detail'),
    path('add/', SopInfraAddView.as_view(), name='sopinfra_add'),
    path('add/<int:pk>/', SopInfraAddView.as_view(), name='sopinfra_add'),
    path('edit/<int:pk>/', SopInfraEditView.as_view(), name='sopinfra_edit'),
    path('delete/<int:pk>/', SopInfraDeleteView.as_view(), name='sopinfra_delete'),
    path('refresh/', SopInfraRefreshView.as_view(), name='sopinfra_refresh'),
    path('refresh_site/', SopInfraRefreshNoForm.as_view(), name='sopinfra_refresh_site'),
    path('journal/<int:pk>', ObjectJournalView.as_view(), name='sopinfra_journal', kwargs={'model': SopInfra}),
    path('changelog/<int:pk>', ObjectChangeLogView.as_view(), name='sopinfra_changelog', kwargs={'model': SopInfra}),

    #____________________
    # classification edit
    path('class/add/', SopInfraClassificationAddView.as_view(), name='class_add'),
    path('class/add/<int:pk>', SopInfraClassificationAddView.as_view(), name='class_add'),
    path('class/edit/<int:pk>', SopInfraClassificationEditView.as_view(), name='class_edit'),

    #____________________
    # sizing edit
    path('sizing/add/', SopInfraSizingAddView.as_view(), name='sizing_add'),
    path('sizing/add/<int:pk>', SopInfraSizingAddView.as_view(), name='sizing_add'),
    path('sizing/edit/<int:pk>', SopInfraSizingEditView.as_view(), name='sizing_edit'),

    #____________________
    # meraki sdwan edit
    path('meraki/add/', SopInfraMerakiAddView.as_view(), name='meraki_add'),
    path('meraki/add/<int:pk>', SopInfraMerakiAddView.as_view(), name='meraki_add'),
    path('meraki/edit/<int:pk>', SopInfraMerakiEditView.as_view(), name='meraki_edit'),

    #____________________
    # list views
    path('list/', SopInfraListView.as_view(), name='sopinfra_list'),
    path('class/list/', SopInfraClassificationListView.as_view(), name='class_list'),
    path('sizing/list/', SopInfraSizingListView.as_view(), name='sizing_list'),
    path('meraki/list/', SopInfraMerakiListView.as_view(), name='meraki_list'),

    #____________________
    # bulk views
    path('delete/', SopInfraBulkDeleteView.as_view(), name='sopinfra_bulk_delete'),
    path('edit/', SopInfraBulkEditView.as_view(), name='sopinfra_bulk_edit'),

    #____________________
    # infra prisma
    path('infra_prisma/add/<int:pk>', SopInfraPrismaAddView.as_view(), name='infra_prisma_add'),
    path('infra_prisma/edit/<int:pk>', SopInfraPrismaEditView.as_view(), name='infra_prisma_edit'),

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

]

