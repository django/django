from django.conf.urls.defaults import patterns

urlpatterns = patterns('regressiontests.cache.views',
    (r'^$', 'home'),
)
