from django.conf.urls import patterns
from django.contrib.databrowse import views

# Note: The views in this URLconf all require a 'models' argument,
# which is a list of model classes (*not* instances).

urlpatterns = patterns('',
    #(r'^$', views.homepage),
    #(r'^([^/]+)/([^/]+)/$', views.model_detail),

    (r'^([^/]+)/([^/]+)/fields/(\w+)/$', views.choice_list),
    (r'^([^/]+)/([^/]+)/fields/(\w+)/(.*)/$', views.choice_detail),

    #(r'^([^/]+)/([^/]+)/calendars/(\w+)/$', views.calendar_main),
    #(r'^([^/]+)/([^/]+)/calendars/(\w+)/(\d{4})/$', views.calendar_year),
    #(r'^([^/]+)/([^/]+)/calendars/(\w+)/(\d{4})/(\w{3})/$', views.calendar_month),
    #(r'^([^/]+)/([^/]+)/calendars/(\w+)/(\d{4})/(\w{3})/(\d{1,2})/$', views.calendar_day),

    #(r'^([^/]+)/([^/]+)/objects/(.*)/$', views.object_detail),
)
