from django.conf.urls import patterns, include
import views
import customadmin
import admin

urlpatterns = patterns('',
    (r'^test_admin/admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^test_admin/admin/secure-view/$', views.secure_view),
    (r'^test_admin/admin/', include(admin.site.urls)),
    (r'^test_admin/admin2/', include(customadmin.site.urls)),
)
