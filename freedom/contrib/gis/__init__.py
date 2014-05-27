from freedom.utils import six

if six.PY3:
    memoryview = memoryview
else:
    memoryview = buffer


default_app_config = 'freedom.contrib.gis.apps.GISConfig'
