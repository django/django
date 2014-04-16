"""
This is a URLconf to be loaded by tests.py. Add any URLs needed for tests only.
"""

from django.conf.urls import url
from django.contrib.formtools.tests.tests import TestFormPreview

from django.contrib.formtools.tests.forms import TestForm


urlpatterns = [
    url(r'^preview/', TestFormPreview(TestForm)),
]
