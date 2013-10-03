from django.conf.urls import url

urlpatterns = [
    url(r'^guitarists/(\w{1,50})/$', 'model_permalink.views.empty_view', name='guitarist_detail'),
]
