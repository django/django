from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to
import views

urlpatterns = patterns('',
    (r'^no_template_view/$', views.no_template_view),
)
