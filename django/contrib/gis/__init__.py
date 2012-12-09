from django.utils import six

if six.PY3:
    memoryview = memoryview
else:
    memoryview = buffer
