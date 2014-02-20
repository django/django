from django.utils import six

if six.PY3:
    memoryview = memoryview
else:
    memoryview = buffer


default_app_config = 'django.contrib.gis.apps.GISConfig'
