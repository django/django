from django.conf.urls import include, url

urlpatterns = [
    url('^', include([
        url(r'^$', lambda x: x, name='name_with:colon'),
    ])),
]
