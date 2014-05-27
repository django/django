from freedom.conf.urls import url
from freedom.contrib.auth import views

urlpatterns = [
    url(r'^accounts/logout/$', views.logout),
]
