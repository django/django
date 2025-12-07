from django import forms
from django.http import HttpResponse
from django.template import Context, Template
from django.views.generic.edit import UpdateView

from .models import Article


class ArticleForm(forms.ModelForm):
    content = forms.CharField(strip=False, widget=forms.Textarea)

    class Meta:
        model = Article
        fields = "__all__"


class ArticleFormView(UpdateView):
    model = Article
    success_url = "/"
    form_class = ArticleForm


def form_view(request):
    class Form(forms.Form):
        number = forms.FloatField()

    template = Template("<html>{{ form }}</html>")
    context = Context({"form": Form()})
    return HttpResponse(template.render(context))
