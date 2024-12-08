from django.urls import path

from .views import ArticleFormView, form_view

urlpatterns = [
    path("form_view/", form_view, name="form_view"),
    path("model_form/<int:pk>/", ArticleFormView.as_view(), name="article_form"),
]
