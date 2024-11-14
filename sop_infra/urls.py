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
    path('edit/', SopInfraBulkEditView.as_view(), name='sopinfra_bulk_edit')

]

