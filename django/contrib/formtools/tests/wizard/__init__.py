from django.contrib.formtools.tests.wizard.test_cookiestorage import TestCookieStorage
from django.contrib.formtools.tests.wizard.test_forms import FormTests, SessionFormTests, CookieFormTests
from django.contrib.formtools.tests.wizard.test_loadstorage import TestLoadStorage
from django.contrib.formtools.tests.wizard.namedwizardtests.tests import (
    NamedSessionWizardTests,
    NamedCookieWizardTests,
    TestNamedUrlSessionWizardView,
    TestNamedUrlCookieWizardView,
    NamedSessionFormTests,
    NamedCookieFormTests,
)
from django.contrib.formtools.tests.wizard.test_sessionstorage import TestSessionStorage
from django.contrib.formtools.tests.wizard.wizardtests.tests import (
    SessionWizardTests,
    CookieWizardTests,
    WizardTestKwargs,
    WizardTestGenericViewInterface,
    WizardFormKwargsOverrideTests,
)
