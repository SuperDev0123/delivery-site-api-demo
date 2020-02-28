from tastypie.resources import ModelResource
from api.models import Fp_freight_providers
from tastypie.authorization import Authorization
class NoteResource(ModelResource):
    class Meta:
        queryset = Fp_freight_providers.objects.all()
        resource_name = 'fp'
        authorization = Authorization()
