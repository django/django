from django.core.serializers.base import PickleSerializer as BasePickleSerializer
from django.core.signing import JSONSerializer as BaseJSONSerializer

JSONSerializer = BaseJSONSerializer
PickleSerializer = BasePickleSerializer
