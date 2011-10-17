"""
This is a URLconf to be loaded by tests.py. Add any URLs needed for tests only.
"""

from __future__ import absolute_import

from django.conf.urls import patterns, url
from django.contrib.formtools.tests import TestFormPreview, TestWizardClass

from django.contrib.formtools.tests.forms import (ContactWizard, Page1, Page2,
    Page3, TestForm, WizardPageOneForm, WizardPageTwoForm, WizardPageThreeForm)


urlpatterns = patterns('',
    url(r'^preview/', TestFormPreview(TestForm)),
    url(r'^wizard1/$', TestWizardClass(
        [WizardPageOneForm, WizardPageTwoForm, WizardPageThreeForm])),
    url(r'^wizard2/$', ContactWizard([Page1, Page2, Page3])),
)
