"""
This is a URLconf to be loaded by tests.py. Add any URLs needed for tests only.
"""

from freedom.conf.urls import url
from freedom.contrib.formtools.tests.tests import TestFormPreview

from freedom.contrib.formtools.tests.forms import TestForm


urlpatterns = [
    url(r'^preview/', TestFormPreview(TestForm)),
]
