from thibaud.contrib.staticfiles import views
from thibaud.urls import re_path

urlpatterns = [
    re_path("^static/(?P<path>.*)$", views.serve),
]
