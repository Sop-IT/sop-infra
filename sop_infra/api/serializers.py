from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer, WritableNestedSerializer

from ..models import *


__all__ = (
    'InfraClassificationSerializer',
    'NestedInfraClassificationserializer',
    'InfraSizingSerializer',
    'NestedSizingSerializer',
    'InfraMerakiSDWANSerializer',
    'NestedMerakiSDWANSerializer',
)


class InfraMerakiSDWANSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:sop_infra-api:inframerakisdwan-detail'
    )

    class Meta:
        model = InfraMerakiSDWAN
        fields = ('url', 'id', 'site', 'master_location',
            'master_site', 'migration_date', 'monitor_in_starting')


class NestedMerakiSDWANSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:sop_infra-api:inframerakisdwan-detail'
    )

    class Meta:
        model = InfraMerakiSDWAN
        fields = ('url', 'id', 'site', 'master_location',
            'master_site', 'migration_date', 'monitor_in_starting')


class InfraSizingSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:sop_infra-api:infrasizing-detail'
    )

    class Meta:
        model = InfraSizing
        fields = ('url', 'id', 'site', 'ad_cumul_user',
            'est_cumul_user', 'reco_bw')


class NestedSizingSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:sop_infra-api:infrasizing-detail'
    )

    class Meta:
        model = InfraSizing
        fields = ('url', 'id', 'site', 'ad_cumul_user',
            'est_cumul_user', 'reco_bw')


class InfraClassificationSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:sop_infra-api:infraclassification-detail'
    )

    class Meta:
        model = InfraClassification
        fields = ('url', 'id', 'site', 'infrastructure', 'industrial',
            'phone_critical', 'r_and_d', 'vip', 'wms')


class NestedInfraClassificationserializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:sop_infra-api:infraclassification-detail'
    )

    class Meta:
        model = InfraClassification
        fields = ('url', 'id', 'site', 'infrastructure', 'industrial',
            'phone_critical', 'r_and_d', 'vip', 'wms')


