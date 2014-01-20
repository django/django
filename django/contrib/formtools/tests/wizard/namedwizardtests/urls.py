from django.conf.urls import patterns, url
from django.contrib.formtools.tests.wizard.namedwizardtests.forms import (
    SessionContactWizard, CookieContactWizard, Page1, Page2, Page3, Page4)


def get_named_session_wizard():
    return SessionContactWizard.as_view(
        [('form1', Page1), ('form2', Page2), ('form3', Page3), ('form4', Page4)],
        url_name='nwiz_session',
        done_step_name='nwiz_session_done'
    )


def get_named_cookie_wizard():
    return CookieContactWizard.as_view(
        [('form1', Page1), ('form2', Page2), ('form3', Page3), ('form4', Page4)],
        url_name='nwiz_cookie',
        done_step_name='nwiz_cookie_done'
    )

urlpatterns = patterns('',
    url(r'^nwiz_session/(?P<step>.+)/$', get_named_session_wizard(), name='nwiz_session'),
    url(r'^nwiz_session/$', get_named_session_wizard(), name='nwiz_session_start'),
    url(r'^nwiz_cookie/(?P<step>.+)/$', get_named_cookie_wizard(), name='nwiz_cookie'),
    url(r'^nwiz_cookie/$', get_named_cookie_wizard(), name='nwiz_cookie_start'),
)
