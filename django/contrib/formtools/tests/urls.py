"""
This is a URLconf to be loaded by tests.py. Add any URLs needed for tests only.
"""

from django.conf.urls import patterns, url
from django.contrib.formtools.tests.tests import TestFormPreview

from django.contrib.formtools.tests.forms import TestForm


urlpatterns = patterns('',
    url(r'^preview/', TestFormPreview(TestForm)),
)
