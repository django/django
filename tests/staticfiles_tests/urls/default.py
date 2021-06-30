from mango.contrib.staticfiles import views
from mango.urls import re_path

urlpatterns = [
    re_path('^static/(?P<path>.*)$', views.serve),
]
