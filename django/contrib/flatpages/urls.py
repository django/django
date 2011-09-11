from django.conf.urls import patterns

urlpatterns = patterns('django.contrib.flatpages.views',
    (r'^(?P<url>.*)$', 'flatpage'),
)
