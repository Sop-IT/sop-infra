from netbox.views import generic
from utilities.views import GetRelatedModelsMixin

from sop_infra.models import (
    PrismaEndpoint, PrismaAccessLocation, PrismaComputedAccessLocation
)
from sop_infra.forms import (
    PrismaEndpointForm, PrismaAccessLocationForm, PrismaComputedAccessLocationForm
)
from sop_infra.tables import (
    PrismaEndpointTable, PrismaAccessLocationTable, PrismaComputedAccessLocationTable
)


__all__ = (
'PrismaEndpointEditView',
    'PrismaEndpointListView',
    'PrismaEndpointDeleteView',
    'PrismaEndpointDetailView',
    'PrismaAccessLocationEditView',
    'PrismaAccessLocationListView',
    'PrismaAccessLocationDeleteView',
    'PrismaAccessLocationDetailView',
    'PrismaComputedAccessLocationEditView',
    'PrismaComputedAccessLocationListView',
    'PrismaComputedAccessLocationDeleteView',
    'PrismaComputedAccessLocationDetailView'
)


#______________
# Endpoint


class PrismaEndpointEditView(generic.ObjectEditView):

    queryset = PrismaEndpoint.objects.all()
    form = PrismaEndpointForm



class PrismaEndpointDeleteView(generic.ObjectDeleteView):

    queryset = PrismaEndpoint.objects.all()



class PrismaEndpointListView(generic.ObjectListView):

    queryset = PrismaEndpoint.objects.all()
    table = PrismaEndpointTable


class PrismaEndpointDetailView(generic.ObjectView):

    queryset = PrismaEndpoint.objects.all()


#______________
# AccessLocation


class PrismaAccessLocationEditView(generic.ObjectEditView):

    queryset = PrismaAccessLocation.objects.all()
    form = PrismaAccessLocationForm



class PrismaAccessLocationDeleteView(generic.ObjectDeleteView):

    queryset = PrismaAccessLocation.objects.all()




class PrismaAccessLocationListView(generic.ObjectListView):

    queryset = PrismaAccessLocation.objects.all()
    table = PrismaAccessLocationTable



class PrismaAccessLocationDetailView(
    generic.ObjectView, GetRelatedModelsMixin):

    queryset = PrismaAccessLocation.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        '''
        additional context for related models/objects
        '''
        related_models = self.get_related_models(
            request,
            instance,
            # later SopInfra
        )
        return {'related_models':related_models}

#______________
# ComputedAccessLocation


class PrismaComputedAccessLocationEditView(generic.ObjectEditView):

    queryset = PrismaComputedAccessLocation.objects.all()
    form = PrismaComputedAccessLocationForm



class PrismaComputedAccessLocationDeleteView(generic.ObjectDeleteView):

    queryset = PrismaComputedAccessLocation.objects.all()



class PrismaComputedAccessLocationListView(generic.ObjectListView):

    queryset = PrismaComputedAccessLocation.objects.all()
    table=PrismaComputedAccessLocationTable



class PrismaComputedAccessLocationDetailView(
    generic.ObjectView, GetRelatedModelsMixin):

    queryset = PrismaComputedAccessLocation.objects.all()

    def get_extra_context(self, request, instance) -> dict:
        '''
        additional context for related models/objects
        '''
        related_models = self.get_related_models(
            request,
            instance,
            # later SopInfra
        )
        return {'related_models':related_models}
