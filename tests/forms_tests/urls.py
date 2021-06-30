from mango.urls import path

from .views import ArticleFormView

urlpatterns = [
    path('model_form/<int:pk>/', ArticleFormView.as_view(), name='article_form'),
]
