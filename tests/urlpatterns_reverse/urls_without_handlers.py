# A URLconf that doesn't define any handlerXXX.
from django.conf.urls import url

from .views import bad_view, empty_view

urlpatterns = [
    url(r'^test_view/$', empty_view, name="test_view"),
    url(r'^bad_view/$', bad_view, name="bad_view"),
]
