from django.conf.urls import include, url
from django.views.generic import TemplateView

from . import views, customadmin, admin


urlpatterns = [
    url(r'^test_admin/admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^test_admin/admin/secure-view/$', views.secure_view),
    url(r'^test_admin/admin/', include(admin.site.urls)),
    url(r'^test_admin/admin2/', include(customadmin.site.urls)),
    url(r'^test_admin/admin3/', include(admin.site.urls), dict(form_url='pony')),
    url(r'^test_admin/admin4/', include(customadmin.simple_site.urls)),
    url(r'^test_admin/admin5/', include(admin.site2.urls)),
    url(r'^test_admin/admin6/', include(customadmin.special_site.urls)),
    url(r'^test_extends_base_site/$', TemplateView.as_view(template_name='test_extends_base_site.html')),
]
