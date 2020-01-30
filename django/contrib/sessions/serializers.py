import pickle
import warnings

from django.core.signing import JSONSerializer as BaseJSONSerializer
from django.utils.deprecation import RemovedInDjango40Warning


class PickleSerializer:
    """
    Simple wrapper around pickle to be used in signing.dumps and
    signing.loads.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warnings.warn(
            (
                "PickleSerializer is deprecated due to its security risk. "
                "Use JSONSerializer instead."
            ),
            RemovedInDjango40Warning,
        )

    protocol = pickle.HIGHEST_PROTOCOL

    def dumps(self, obj):
        return pickle.dumps(obj, self.protocol)

    def loads(self, data):
        return pickle.loads(data)


JSONSerializer = BaseJSONSerializer
