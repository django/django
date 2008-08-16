from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'^geoapp/', include('django.contrib.gis.tests.geoapp.urls')),
                       )
                        
