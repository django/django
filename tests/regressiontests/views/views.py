from django.http import HttpResponse
from django import forms
from django.views.generic.create_update import create_object

from models import Article


def index_page(request):
    """Dummy index page"""
    return HttpResponse('<html><body>Dummy page</body></html>')


def custom_create(request):
    """
    Calls create_object generic view with a custom form class.
    """
    class SlugChangingArticleForm(forms.ModelForm):
        """Custom form class to overwrite the slug."""

        class Meta:
            model = Article

        def save(self, *args, **kwargs):
            self.cleaned_data['slug'] = 'some-other-slug'
            return super(SlugChangingArticleForm, self).save(*args, **kwargs)

    return create_object(request,
        post_save_redirect='/views/create_update/view/article/%(slug)s/',
        form_class=SlugChangingArticleForm)
