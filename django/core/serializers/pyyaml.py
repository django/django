"""
YAML serializer.

Requires PyYaml (http://pyyaml.org/), but that's checked for in __init__.
"""

import datetime
from django.core.serializers.python import Serializer as PythonSerializer
from django.core.serializers.python import Deserializer as PythonDeserializer
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import yaml

class Serializer(PythonSerializer):
    """
    Convert a queryset to JSON.
    """
    def end_serialization(self):
        yaml.dump(self.objects, self.stream, **self.options)
        
    def getvalue(self):
        return self.stream.getvalue()

def Deserializer(stream_or_string, **options):
    """
    Deserialize a stream or string of JSON data.
    """
    if isinstance(stream_or_string, basestring):
        stream = StringIO(stream_or_string)
    else:
        stream = stream_or_string
    for obj in PythonDeserializer(yaml.load(stream)):
        yield obj
        
