from freedom.conf.urls import url
from freedom.contrib.staticfiles import views

urlpatterns = [
    url(r'^static/(?P<path>.*)$', views.serve),
]
