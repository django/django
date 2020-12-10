import pickle

from django.core.signing import JSONSerializer as BaseJSONSerializer


class PickleSerializer:
    """
    Simple wrapper around pickle to be used in signing.dumps and
    signing.loads.
    """
    protocol = pickle.HIGHEST_PROTOCOL

    def dumps(self, obj):
        return pickle.dumps(obj, self.protocol)

    def loads(self, data):
        return pickle.loads(data)


JSONSerializer = BaseJSONSerializer
