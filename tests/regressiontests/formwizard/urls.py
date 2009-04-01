from django.conf.urls.defaults import *
from forms import ContactWizard, Page1, Page2, Page3

urlpatterns = patterns('',
    url(r'^wiz/$', ContactWizard([Page1, Page2, Page3])),
    )
