# coding: utf-8
from django.conf.urls.defaults import *

from regressiontests.templates import views


urlpatterns = patterns('',
    # View returning a template response
    (r'^template_response_view/$', views.template_response_view),

    # A view that can be hard to find...
    url(r'^snark/', views.snark, name='snark'),
)
