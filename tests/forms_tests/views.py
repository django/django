from django import forms
from django.views.generic.edit import UpdateView

from .models import Article


class ArticleForm(forms.ModelForm):
    content = forms.CharField(strip=False, widget=forms.Textarea)

    class Meta:
        model = Article
        fields = '__all__'


class ArticleFormView(UpdateView):
    model = Article
    success_url = '/'
    form_class = ArticleForm
