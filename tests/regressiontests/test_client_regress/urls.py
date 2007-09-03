from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    (r'^no_template_view/$', views.no_template_view),
    (r'^file_upload/$', views.file_upload_view),
    (r'^get_view/$', views.get_view),
    (r'^login_protected_redirect_view/$', views.login_protected_redirect_view)
)
