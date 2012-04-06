from __future__ import absolute_import

import time

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import TestCase, RequestFactory
from django.utils import unittest
from django.views.generic import View, TemplateView, RedirectView

from . import views

class SimpleView(View):
    """
    A simple view with a docstring.
    """
    def get(self, request):
        return HttpResponse('This is a simple view')


class SimplePostView(SimpleView):
    post = SimpleView.get


class PostOnlyView(View):
    def post(self, request):
        return HttpResponse('This view only accepts POST')


class CustomizableView(SimpleView):
    parameter = {}


def decorator(view):
    view.is_decorated = True
    return view


class DecoratedDispatchView(SimpleView):

    @decorator
    def dispatch(self, request, *args, **kwargs):
        return super(DecoratedDispatchView, self).dispatch(request, *args, **kwargs)


class AboutTemplateView(TemplateView):
    def get(self, request):
        return self.render_to_response({})

    def get_template_names(self):
        return ['generic_views/about.html']


class AboutTemplateAttributeView(TemplateView):
    template_name = 'generic_views/about.html'

    def get(self, request):
        return self.render_to_response(context={})


class InstanceView(View):

    def get(self, request):
        return self


class ViewTest(unittest.TestCase):
    rf = RequestFactory()

    def _assert_simple(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'This is a simple view')

    def test_no_init_kwargs(self):
        """
        Test that a view can't be accidentally instantiated before deployment
        """
        try:
            view = SimpleView(key='value').as_view()
            self.fail('Should not be able to instantiate a view')
        except AttributeError:
            pass

    def test_no_init_args(self):
        """
        Test that a view can't be accidentally instantiated before deployment
        """
        try:
            view = SimpleView.as_view('value')
            self.fail('Should not be able to use non-keyword arguments instantiating a view')
        except TypeError:
            pass

    def test_pathological_http_method(self):
        """
        The edge case of a http request that spoofs an existing method name is caught.
        """
        self.assertEqual(SimpleView.as_view()(
            self.rf.get('/', REQUEST_METHOD='DISPATCH')
        ).status_code, 405)

    def test_get_only(self):
        """
        Test a view which only allows GET doesn't allow other methods.
        """
        self._assert_simple(SimpleView.as_view()(self.rf.get('/')))
        self.assertEqual(SimpleView.as_view()(self.rf.post('/')).status_code, 405)
        self.assertEqual(SimpleView.as_view()(
            self.rf.get('/', REQUEST_METHOD='FAKE')
        ).status_code, 405)

    def test_get_and_head(self):
        """
        Test a view which supplies a GET method also responds correctly to HEAD.
        """
        self._assert_simple(SimpleView.as_view()(self.rf.get('/')))
        response = SimpleView.as_view()(self.rf.head('/'))
        self.assertEqual(response.status_code, 200)

    def test_head_no_get(self):
        """
        Test a view which supplies no GET method responds to HEAD with HTTP 405.
        """
        response = PostOnlyView.as_view()(self.rf.head('/'))
        self.assertEqual(response.status_code, 405)

    def test_get_and_post(self):
        """
        Test a view which only allows both GET and POST.
        """
        self._assert_simple(SimplePostView.as_view()(self.rf.get('/')))
        self._assert_simple(SimplePostView.as_view()(self.rf.post('/')))
        self.assertEqual(SimplePostView.as_view()(
            self.rf.get('/', REQUEST_METHOD='FAKE')
        ).status_code, 405)

    def test_invalid_keyword_argument(self):
        """
        Test that view arguments must be predefined on the class and can't
        be named like a HTTP method.
        """
        # Check each of the allowed method names
        for method in SimpleView.http_method_names:
            kwargs = dict(((method, "value"),))
            self.assertRaises(TypeError, SimpleView.as_view, **kwargs)

        # Check the case view argument is ok if predefined on the class...
        CustomizableView.as_view(parameter="value")
        # ...but raises errors otherwise.
        self.assertRaises(TypeError, CustomizableView.as_view, foobar="value")

    def test_calling_more_than_once(self):
        """
        Test a view can only be called once.
        """
        request = self.rf.get('/')
        view = InstanceView.as_view()
        self.assertNotEqual(view(request), view(request))

    def test_class_attributes(self):
        """
        Test that the callable returned from as_view() has proper
        docstring, name and module.
        """
        self.assertEqual(SimpleView.__doc__, SimpleView.as_view().__doc__)
        self.assertEqual(SimpleView.__name__, SimpleView.as_view().__name__)
        self.assertEqual(SimpleView.__module__, SimpleView.as_view().__module__)

    def test_dispatch_decoration(self):
        """
        Test that attributes set by decorators on the dispatch method
        are also present on the closure.
        """
        self.assertTrue(DecoratedDispatchView.as_view().is_decorated)


class TemplateViewTest(TestCase):
    urls = 'regressiontests.generic_views.urls'

    rf = RequestFactory()

    def _assert_about(self, response):
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1>About</h1>')

    def test_get(self):
        """
        Test a view that simply renders a template on GET
        """
        self._assert_about(AboutTemplateView.as_view()(self.rf.get('/about/')))

    def test_head(self):
        """
        Test a TemplateView responds correctly to HEAD
        """
        response = AboutTemplateView.as_view()(self.rf.head('/about/'))
        self.assertEqual(response.status_code, 200)

    def test_get_template_attribute(self):
        """
        Test a view that renders a template on GET with the template name as
        an attribute on the class.
        """
        self._assert_about(AboutTemplateAttributeView.as_view()(self.rf.get('/about/')))

    def test_get_generic_template(self):
        """
        Test a completely generic view that renders a template on GET
        with the template name as an argument at instantiation.
        """
        self._assert_about(TemplateView.as_view(template_name='generic_views/about.html')(self.rf.get('/about/')))

    def test_template_name_required(self):
        """
        A template view must provide a template name
        """
        self.assertRaises(ImproperlyConfigured, self.client.get, '/template/no_template/')

    def test_template_params(self):
        """
        A generic template view passes kwargs as context.
        """
        response = self.client.get('/template/simple/bar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['params'], {'foo': 'bar'})

    def test_extra_template_params(self):
        """
        A template view can be customized to return extra context.
        """
        response = self.client.get('/template/custom/bar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['params'], {'foo': 'bar'})
        self.assertEqual(response.context['key'], 'value')

    def test_cached_views(self):
        """
        A template view can be cached
        """
        response = self.client.get('/template/cached/bar/')
        self.assertEqual(response.status_code, 200)

        time.sleep(1.0)

        response2 = self.client.get('/template/cached/bar/')
        self.assertEqual(response2.status_code, 200)

        self.assertEqual(response.content, response2.content)

        time.sleep(2.0)

        # Let the cache expire and test again
        response2 = self.client.get('/template/cached/bar/')
        self.assertEqual(response2.status_code, 200)

        self.assertNotEqual(response.content, response2.content)

class RedirectViewTest(unittest.TestCase):
    rf = RequestFactory()

    def test_no_url(self):
        "Without any configuration, returns HTTP 410 GONE"
        response = RedirectView.as_view()(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 410)

    def test_permanent_redirect(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_temporary_redirect(self):
        "Permanent redirects are an option"
        response = RedirectView.as_view(url='/bar/', permanent=False)(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/bar/')

    def test_include_args(self):
        "GET arguments can be included in the redirected URL"
        response = RedirectView.as_view(url='/bar/')(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

        response = RedirectView.as_view(url='/bar/', query_string=True)(self.rf.get('/foo/?pork=spam'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/?pork=spam')

    def test_include_urlencoded_args(self):
        "GET arguments can be URL-encoded when included in the redirected URL"
        response = RedirectView.as_view(url='/bar/', query_string=True)(
            self.rf.get('/foo/?unicode=%E2%9C%93'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/?unicode=%E2%9C%93')

    def test_parameter_substitution(self):
        "Redirection URLs can be parameterized"
        response = RedirectView.as_view(url='/bar/%(object_id)d/')(self.rf.get('/foo/42/'), object_id=42)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/42/')

    def test_redirect_POST(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.post('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_redirect_HEAD(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.head('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_redirect_OPTIONS(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.options('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_redirect_PUT(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.put('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_redirect_DELETE(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.delete('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_redirect_when_meta_contains_no_query_string(self):
        "regression for #16705"
        # we can't use self.rf.get because it always sets QUERY_STRING
        response = RedirectView.as_view(url='/bar/')(self.rf.request(PATH_INFO='/foo/'))
        self.assertEqual(response.status_code, 301)


class GetContextDataTest(unittest.TestCase):

    def test_get_context_data_super(self):
        test_view = views.CustomContextView()
        context = test_view.get_context_data(kwarg_test='kwarg_value')

        # the test_name key is inserted by the test classes parent
        self.assertTrue('test_name' in context)
        self.assertEqual(context['kwarg_test'], 'kwarg_value')
        self.assertEqual(context['custom_key'], 'custom_value')

        # test that kwarg overrides values assigned higher up
        context = test_view.get_context_data(test_name='test_value')
        self.assertEqual(context['test_name'], 'test_value')
