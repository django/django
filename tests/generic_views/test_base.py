import time

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.test.utils import require_jinja2
from django.urls import resolve
from django.views.generic import RedirectView, TemplateView, View

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
        return super().dispatch(request, *args, **kwargs)


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


class ViewTest(SimpleTestCase):
    rf = RequestFactory()

    def _assert_simple(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'This is a simple view')

    def test_no_init_kwargs(self):
        """
        A view can't be accidentally instantiated before deployment
        """
        msg = 'This method is available only on the class, not on instances.'
        with self.assertRaisesMessage(AttributeError, msg):
            SimpleView(key='value').as_view()

    def test_no_init_args(self):
        """
        A view can't be accidentally instantiated before deployment
        """
        msg = 'as_view() takes 1 positional argument but 2 were given'
        with self.assertRaisesMessage(TypeError, msg):
            SimpleView.as_view('value')

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

    def test_setup_get_and_head(self):
        view_instance = SimpleView()
        self.assertFalse(hasattr(view_instance, 'head'))
        view_instance.setup(self.rf.get('/'))
        self.assertTrue(hasattr(view_instance, 'head'))
        self.assertEqual(view_instance.head, view_instance.get)

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
        View arguments must be predefined on the class and can't
        be named like a HTTP method.
        """
        msg = (
            'The method name %s is not accepted as a keyword argument to '
            'SimpleView().'
        )
        # Check each of the allowed method names
        for method in SimpleView.http_method_names:
            with self.assertRaisesMessage(TypeError, msg % method):
                SimpleView.as_view(**{method: 'value'})

        # Check the case view argument is ok if predefined on the class...
        CustomizableView.as_view(parameter="value")
        # ...but raises errors otherwise.
        msg = (
            "CustomizableView() received an invalid keyword 'foobar'. "
            "as_view only accepts arguments that are already attributes of "
            "the class."
        )
        with self.assertRaisesMessage(TypeError, msg):
            CustomizableView.as_view(foobar="value")

    def test_calling_more_than_once(self):
        """
        Test a view can only be called once.
        """
        request = self.rf.get('/')
        view = InstanceView.as_view()
        self.assertNotEqual(view(request), view(request))

    def test_class_attributes(self):
        """
        The callable returned from as_view() has proper
        docstring, name and module.
        """
        self.assertEqual(SimpleView.__doc__, SimpleView.as_view().__doc__)
        self.assertEqual(SimpleView.__name__, SimpleView.as_view().__name__)
        self.assertEqual(SimpleView.__module__, SimpleView.as_view().__module__)

    def test_dispatch_decoration(self):
        """
        Attributes set by decorators on the dispatch method
        are also present on the closure.
        """
        self.assertTrue(DecoratedDispatchView.as_view().is_decorated)

    def test_options(self):
        """
        Views respond to HTTP OPTIONS requests with an Allow header
        appropriate for the methods implemented by the view class.
        """
        request = self.rf.options('/')
        view = SimpleView.as_view()
        response = view(request)
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.headers['Allow'])

    def test_options_for_get_view(self):
        """
        A view implementing GET allows GET and HEAD.
        """
        request = self.rf.options('/')
        view = SimpleView.as_view()
        response = view(request)
        self._assert_allows(response, 'GET', 'HEAD')

    def test_options_for_get_and_post_view(self):
        """
        A view implementing GET and POST allows GET, HEAD, and POST.
        """
        request = self.rf.options('/')
        view = SimplePostView.as_view()
        response = view(request)
        self._assert_allows(response, 'GET', 'HEAD', 'POST')

    def test_options_for_post_view(self):
        """
        A view implementing POST allows POST.
        """
        request = self.rf.options('/')
        view = PostOnlyView.as_view()
        response = view(request)
        self._assert_allows(response, 'POST')

    def _assert_allows(self, response, *expected_methods):
        "Assert allowed HTTP methods reported in the Allow response header"
        response_allows = set(response.headers['Allow'].split(', '))
        self.assertEqual(set(expected_methods + ('OPTIONS',)), response_allows)

    def test_args_kwargs_request_on_self(self):
        """
        Test a view only has args, kwargs & request once `as_view`
        has been called.
        """
        bare_view = InstanceView()
        view = InstanceView.as_view()(self.rf.get('/'))
        for attribute in ('args', 'kwargs', 'request'):
            self.assertNotIn(attribute, dir(bare_view))
            self.assertIn(attribute, dir(view))

    def test_overridden_setup(self):
        class SetAttributeMixin:
            def setup(self, request, *args, **kwargs):
                self.attr = True
                super().setup(request, *args, **kwargs)

        class CheckSetupView(SetAttributeMixin, SimpleView):
            def dispatch(self, request, *args, **kwargs):
                assert hasattr(self, 'attr')
                return super().dispatch(request, *args, **kwargs)

        response = CheckSetupView.as_view()(self.rf.get('/'))
        self.assertEqual(response.status_code, 200)

    def test_not_calling_parent_setup_error(self):
        class TestView(View):
            def setup(self, request, *args, **kwargs):
                pass  # Not calling super().setup()

        msg = (
            "TestView instance has no 'request' attribute. Did you override "
            "setup() and forget to call super()?"
        )
        with self.assertRaisesMessage(AttributeError, msg):
            TestView.as_view()(self.rf.get('/'))

    def test_setup_adds_args_kwargs_request(self):
        request = self.rf.get('/')
        args = ('arg 1', 'arg 2')
        kwargs = {'kwarg_1': 1, 'kwarg_2': 'year'}

        view = View()
        view.setup(request, *args, **kwargs)
        self.assertEqual(request, view.request)
        self.assertEqual(args, view.args)
        self.assertEqual(kwargs, view.kwargs)

    def test_direct_instantiation(self):
        """
        It should be possible to use the view by directly instantiating it
        without going through .as_view() (#21564).
        """
        view = PostOnlyView()
        response = view.dispatch(self.rf.head('/'))
        self.assertEqual(response.status_code, 405)


@override_settings(ROOT_URLCONF='generic_views.urls')
class TemplateViewTest(SimpleTestCase):

    rf = RequestFactory()

    def _assert_about(self, response):
        response.render()
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
        A template view must provide a template name.
        """
        msg = (
            "TemplateResponseMixin requires either a definition of "
            "'template_name' or an implementation of 'get_template_names()'"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.client.get('/template/no_template/')

    @require_jinja2
    def test_template_engine(self):
        """
        A template view may provide a template engine.
        """
        request = self.rf.get('/using/')
        view = TemplateView.as_view(template_name='generic_views/using.html')
        self.assertEqual(view(request).render().content, b'DTL\n')
        view = TemplateView.as_view(template_name='generic_views/using.html', template_engine='django')
        self.assertEqual(view(request).render().content, b'DTL\n')
        view = TemplateView.as_view(template_name='generic_views/using.html', template_engine='jinja2')
        self.assertEqual(view(request).render().content, b'Jinja2\n')

    def test_template_params(self):
        """
        A generic template view passes kwargs as context.
        """
        response = self.client.get('/template/simple/bar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['foo'], 'bar')
        self.assertIsInstance(response.context['view'], View)

    def test_extra_template_params(self):
        """
        A template view can be customized to return extra context.
        """
        response = self.client.get('/template/custom/bar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['foo'], 'bar')
        self.assertEqual(response.context['key'], 'value')
        self.assertIsInstance(response.context['view'], View)

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

    def test_content_type(self):
        response = self.client.get('/template/content_type/')
        self.assertEqual(response.headers['Content-Type'], 'text/plain')

    def test_resolve_view(self):
        match = resolve('/template/content_type/')
        self.assertIs(match.func.view_class, TemplateView)
        self.assertEqual(match.func.view_initkwargs['content_type'], 'text/plain')

    def test_resolve_login_required_view(self):
        match = resolve('/template/login_required/')
        self.assertIs(match.func.view_class, TemplateView)

    def test_extra_context(self):
        response = self.client.get('/template/extra_context/')
        self.assertEqual(response.context['title'], 'Title')


@override_settings(ROOT_URLCONF='generic_views.urls')
class RedirectViewTest(SimpleTestCase):

    rf = RequestFactory()

    def test_no_url(self):
        "Without any configuration, returns HTTP 410 GONE"
        response = RedirectView.as_view()(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 410)

    def test_default_redirect(self):
        "Default is a temporary redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/')

    def test_permanent_redirect(self):
        "Permanent redirects are an option"
        response = RedirectView.as_view(url='/bar/', permanent=True)(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/bar/')

    def test_temporary_redirect(self):
        "Temporary redirects are an option"
        response = RedirectView.as_view(url='/bar/', permanent=False)(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/')

    def test_include_args(self):
        "GET arguments can be included in the redirected URL"
        response = RedirectView.as_view(url='/bar/')(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/')

        response = RedirectView.as_view(url='/bar/', query_string=True)(self.rf.get('/foo/?pork=spam'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/?pork=spam')

    def test_include_urlencoded_args(self):
        "GET arguments can be URL-encoded when included in the redirected URL"
        response = RedirectView.as_view(url='/bar/', query_string=True)(
            self.rf.get('/foo/?unicode=%E2%9C%93'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/?unicode=%E2%9C%93')

    def test_parameter_substitution(self):
        "Redirection URLs can be parameterized"
        response = RedirectView.as_view(url='/bar/%(object_id)d/')(self.rf.get('/foo/42/'), object_id=42)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/42/')

    def test_named_url_pattern(self):
        "Named pattern parameter should reverse to the matching pattern"
        response = RedirectView.as_view(pattern_name='artist_detail')(self.rf.get('/foo/'), pk=1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/detail/artist/1/')

    def test_named_url_pattern_using_args(self):
        response = RedirectView.as_view(pattern_name='artist_detail')(self.rf.get('/foo/'), 1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/detail/artist/1/')

    def test_redirect_POST(self):
        "Default is a temporary redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.post('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/')

    def test_redirect_HEAD(self):
        "Default is a temporary redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.head('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/')

    def test_redirect_OPTIONS(self):
        "Default is a temporary redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.options('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/')

    def test_redirect_PUT(self):
        "Default is a temporary redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.put('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/')

    def test_redirect_PATCH(self):
        "Default is a temporary redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.patch('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/')

    def test_redirect_DELETE(self):
        "Default is a temporary redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.delete('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/bar/')

    def test_redirect_when_meta_contains_no_query_string(self):
        "regression for #16705"
        # we can't use self.rf.get because it always sets QUERY_STRING
        response = RedirectView.as_view(url='/bar/')(self.rf.request(PATH_INFO='/foo/'))
        self.assertEqual(response.status_code, 302)

    def test_direct_instantiation(self):
        """
        It should be possible to use the view without going through .as_view()
        (#21564).
        """
        view = RedirectView()
        response = view.dispatch(self.rf.head('/foo/'))
        self.assertEqual(response.status_code, 410)


class GetContextDataTest(SimpleTestCase):

    def test_get_context_data_super(self):
        test_view = views.CustomContextView()
        context = test_view.get_context_data(kwarg_test='kwarg_value')

        # the test_name key is inserted by the test classes parent
        self.assertIn('test_name', context)
        self.assertEqual(context['kwarg_test'], 'kwarg_value')
        self.assertEqual(context['custom_key'], 'custom_value')

        # test that kwarg overrides values assigned higher up
        context = test_view.get_context_data(test_name='test_value')
        self.assertEqual(context['test_name'], 'test_value')

    def test_object_at_custom_name_in_context_data(self):
        # Checks 'pony' key presence in dict returned by get_context_date
        test_view = views.CustomSingleObjectView()
        test_view.context_object_name = 'pony'
        context = test_view.get_context_data()
        self.assertEqual(context['pony'], test_view.object)

    def test_object_in_get_context_data(self):
        # Checks 'object' key presence in dict returned by get_context_date #20234
        test_view = views.CustomSingleObjectView()
        context = test_view.get_context_data()
        self.assertEqual(context['object'], test_view.object)


class UseMultipleObjectMixinTest(SimpleTestCase):
    rf = RequestFactory()

    def test_use_queryset_from_view(self):
        test_view = views.CustomMultipleObjectMixinView()
        test_view.get(self.rf.get('/'))
        # Don't pass queryset as argument
        context = test_view.get_context_data()
        self.assertEqual(context['object_list'], test_view.queryset)

    def test_overwrite_queryset(self):
        test_view = views.CustomMultipleObjectMixinView()
        test_view.get(self.rf.get('/'))
        queryset = [{'name': 'Lennon'}, {'name': 'Ono'}]
        self.assertNotEqual(test_view.queryset, queryset)
        # Overwrite the view's queryset with queryset from kwarg
        context = test_view.get_context_data(object_list=queryset)
        self.assertEqual(context['object_list'], queryset)


class SingleObjectTemplateResponseMixinTest(SimpleTestCase):

    def test_template_mixin_without_template(self):
        """
        We want to makes sure that if you use a template mixin, but forget the
        template, it still tells you it's ImproperlyConfigured instead of
        TemplateDoesNotExist.
        """
        view = views.TemplateResponseWithoutTemplate()
        msg = (
            "TemplateResponseMixin requires either a definition of "
            "'template_name' or an implementation of 'get_template_names()'"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            view.get_template_names()
