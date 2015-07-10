from django.conf.urls import url

from .views import empty_view

urlpatterns = [
    url(r'^inner-no-kwargs/([0-9]+)/', empty_view, name="inner-no-kwargs")
]
