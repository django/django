"""
This is a URLconf to be loaded by tests.py. Add any URLs needed for tests only.
"""

from django.conf.urls.defaults import *
from django.contrib.formtools.tests import TestFormPreview, TestWizardClass

from forms import (ContactWizard, Page1, Page2, Page3, TestForm,
    WizardPageOneForm, WizardPageTwoForm, WizardPageThreeForm)

urlpatterns = patterns('',
    url(r'^preview/', TestFormPreview(TestForm)),
    url(r'^wizard1/$', TestWizardClass(
        [WizardPageOneForm, WizardPageTwoForm, WizardPageThreeForm])),
    url(r'^wizard2/$', ContactWizard([Page1, Page2, Page3])),
)
