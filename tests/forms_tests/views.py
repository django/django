from django.views.generic.edit import UpdateView

from .models import Article


class ArticleFormView(UpdateView):
    model = Article
    success_url = '/'
    fields = '__all__'
