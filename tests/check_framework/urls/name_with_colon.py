from django.conf.urls import url

urlpatterns = [
    url(r'^$', lambda x: x, name='name_with:colon'),
]
