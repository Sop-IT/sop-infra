from django.urls import path

from netbox.views.generic import ObjectChangeLogView, ObjectJournalView

from .views import classification as cl
from .views import sizing as sz
from .views import meraki_sdwan as ms
from .views import tab_view
from .models import *


app_name = 'sop_infra'


urlpatterns = [
    
    # classification
    path('classification/<int:pk>', cl.ClassificationDetailView.as_view(), name='infraclassification_detail'),
    path('classification/edit/<int:pk>', cl.ClassificationEditView.as_view(), name='infraclassification_edit'),
    path('classification/changelog/<int:pk>', ObjectChangeLogView.as_view(), name='infraclassification_changelog', kwargs={'model': InfraClassification}),
    path('classification/journal/<int:pk>', ObjectJournalView.as_view(), name='infraclassification_journal', kwargs={'model': InfraClassification}),

    # sizing
    path('sizing/<int:pk>', sz.SizingDetailView.as_view(), name='infrasizing_detail'),
    path('sizing/edit/<int:pk>', sz.SizingEditView.as_view(), name='infrasizing_edit'),
    path('sizing/changelog/<int:pk>', ObjectChangeLogView.as_view(), name='infrasizing_changelog', kwargs={'model': InfraSizing}),
    path('sizing/journal/<int:pk>', ObjectJournalView.as_view(), name='infrasizing_journal', kwargs={'model': InfraSizing}),

    # meraki sdwan
    path('meraki_sdwan/<int:pk>', ms.MerakiSDWANDetailView.as_view(), name='inframerakisdwan_detail'),
    path('meraki_sdwan/edit/<int:pk>', ms.MerakiSDWANEditView.as_view(), name='inframerakisdwan_edit'),
    path('meraki_sdwan/changelog/<int:pk>', ObjectChangeLogView.as_view(), name='inframerakisdwan_changelog', kwargs={'model': InfraMerakiSDWAN}),
    path('meraki_sdwan/journal/<int:pk>', ObjectJournalView.as_view(), name='inframerakisdwan_journal', kwargs={'model': InfraMerakiSDWAN}),
    
]
