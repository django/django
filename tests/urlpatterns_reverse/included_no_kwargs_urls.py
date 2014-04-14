from django.conf.urls import url

from .views import empty_view


urlpatterns = [
    url(r'^inner-no-kwargs/(\d+)/', empty_view, name="inner-no-kwargs")
]
