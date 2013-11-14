from django.conf.urls import patterns, url

from .views import ArticleFormView


urlpatterns = patterns('',
    url(r'^model_form/(?P<pk>\d+)/$', ArticleFormView.as_view(), name="article_form"),
)
