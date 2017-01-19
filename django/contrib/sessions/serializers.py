import pickle

from django.core.signing import JSONSerializer as BaseJSONSerializer


class PickleSerializer:
    """
    Simple wrapper around pickle to be used in signing.dumps and
    signing.loads.
    """
    def dumps(self, obj):
        return pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)

    def loads(self, data):
        return pickle.loads(data)


JSONSerializer = BaseJSONSerializer
