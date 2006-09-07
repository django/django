from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    (r'^get_view/$', views.get_view),
    (r'^post_view/$', views.post_view),
    (r'^redirect_view/$', views.redirect_view),
    (r'^login_protected_view/$', views.login_protected_view),
)
