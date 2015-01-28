from django.conf.urls import url

from .views import ArticleFormView

urlpatterns = [
    url(r'^model_form/(?P<pk>[0-9]+)/$', ArticleFormView.as_view(), name="article_form"),
]
