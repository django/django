from django.core.signing import JSONSerializer as BaseJSONSerializer
try:
    from django.utils.six.moves import cPickle as pickle
except ImportError:
    import pickle


class PickleSerializer(object):
    """
    Simple wrapper around pickle to be used in signing.dumps and
    signing.loads.
    """
    def dumps(self, obj):
        return pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)

    def loads(self, data):
        return pickle.loads(data)


JSONSerializer = BaseJSONSerializer
