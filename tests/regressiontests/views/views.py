import sys

from django.http import HttpResponse, HttpResponseRedirect
from django import forms
from django.views.debug import technical_500_response
from django.views.generic.create_update import create_object
from django.core.urlresolvers import get_resolver
from django.shortcuts import render_to_response

from regressiontests.views import BrokenException, except_args

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
            self.instance.slug = 'some-other-slug'
            return super(SlugChangingArticleForm, self).save(*args, **kwargs)

    return create_object(request,
        post_save_redirect='/views/create_update/view/article/%(slug)s/',
        form_class=SlugChangingArticleForm)

def raises(request):
    try:
        raise Exception
    except Exception:
        return technical_500_response(request, *sys.exc_info())

def raises404(request):
    resolver = get_resolver(None)
    resolver.resolve('')

def redirect(request):
    """
    Forces an HTTP redirect.
    """
    return HttpResponseRedirect("target/")

def view_exception(request, n):
    raise BrokenException(except_args[int(n)])

def template_exception(request, n):
    return render_to_response('debug/template_exception.html',
        {'arg': except_args[int(n)]})

