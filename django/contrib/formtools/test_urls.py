"""

This is a urlconf to be loaded by tests.py. Add any urls needed
for tests only.

"""
from django.conf.urls.defaults import *
from django.contrib.formtools.tests import *

urlpatterns = patterns('',
                       (r'^test1/', TestFormPreview(TestForm)),
                      )
