from django.conf.urls import url

urlpatterns = [
    url(r'^guitarists/(\w{1,50})/$', 'unimplemented_view_placeholder', name='guitarist_detail'),
]
