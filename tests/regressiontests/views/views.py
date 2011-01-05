import sys

from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import get_resolver
from django.shortcuts import render_to_response, render
from django.template import Context, RequestContext
from django.views.debug import technical_500_response
from django.views.generic.create_update import create_object

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

# Some views to exercise the shortcuts

def render_to_response_view(request):
    return render_to_response('debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    })

def render_to_response_view_with_request_context(request):
    return render_to_response('debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, context_instance=RequestContext(request))

def render_to_response_view_with_mimetype(request):
    return render_to_response('debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, mimetype='application/x-rendertest')

def render_view(request):
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    })

def render_view_with_base_context(request):
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, context_instance=Context())

def render_view_with_content_type(request):
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, content_type='application/x-rendertest')

def render_view_with_status(request):
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, status=403)

def render_view_with_current_app(request):
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, current_app="foobar_app")

def render_view_with_current_app_conflict(request):
    # This should fail because we don't passing both a current_app and
    # context_instance:
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, current_app="foobar_app", context_instance=RequestContext(request))
