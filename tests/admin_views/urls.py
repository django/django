from django.conf.urls import include, url

from . import admin, custom_has_permission_admin, customadmin, views

urlpatterns = [
    url(r'^test_admin/admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^test_admin/admin/secure-view/$', views.secure_view, name='secure_view'),
    url(r'^test_admin/admin/secure-view2/$', views.secure_view2, name='secure_view2'),
    url(r'^test_admin/admin/', admin.site.urls),
    url(r'^test_admin/admin2/', customadmin.site.urls),
    url(r'^test_admin/admin3/', (admin.site.get_urls(), 'admin', 'admin3'), dict(form_url='pony')),
    url(r'^test_admin/admin4/', customadmin.simple_site.urls),
    url(r'^test_admin/admin5/', admin.site2.urls),
    url(r'^test_admin/admin7/', admin.site7.urls),
    url(r'^test_admin/has_permission_admin/', custom_has_permission_admin.site.urls),
]
