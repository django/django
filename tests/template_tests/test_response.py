from __future__ import unicode_literals

import pickle
import time
from datetime import datetime

from django.conf import settings
from django.template import Context, engines
from django.template.response import (
    ContentNotRenderedError, SimpleTemplateResponse, TemplateResponse,
)
from django.test import (
    RequestFactory, SimpleTestCase, ignore_warnings, override_settings,
)
from django.test.utils import require_jinja2
from django.utils.deprecation import RemovedInDjango110Warning

from .utils import TEMPLATE_DIR


def test_processor(request):
    return {'processors': 'yes'}
test_processor_name = 'template_tests.test_response.test_processor'


# A test middleware that installs a temporary URLConf
class CustomURLConfMiddleware(object):
    def process_request(self, request):
        request.urlconf = 'template_tests.alternate_urls'


class SimpleTemplateResponseTest(SimpleTestCase):

    def _response(self, template='foo', *args, **kwargs):
        template = engines['django'].from_string(template)
        return SimpleTemplateResponse(template, *args, **kwargs)

    def test_template_resolving(self):
        response = SimpleTemplateResponse('first/test.html')
        response.render()
        self.assertEqual(response.content, b'First template\n')

        templates = ['foo.html', 'second/test.html', 'first/test.html']
        response = SimpleTemplateResponse(templates)
        response.render()
        self.assertEqual(response.content, b'Second template\n')

        response = self._response()
        response.render()
        self.assertEqual(response.content, b'foo')

    def test_explicit_baking(self):
        # explicit baking
        response = self._response()
        self.assertFalse(response.is_rendered)
        response.render()
        self.assertTrue(response.is_rendered)

    def test_render(self):
        # response is not re-rendered without the render call
        response = self._response().render()
        self.assertEqual(response.content, b'foo')

        # rebaking doesn't change the rendered content
        template = engines['django'].from_string('bar{{ baz }}')
        response.template_name = template
        response.render()
        self.assertEqual(response.content, b'foo')

        # but rendered content can be overridden by manually
        # setting content
        response.content = 'bar'
        self.assertEqual(response.content, b'bar')

    def test_iteration_unrendered(self):
        # unrendered response raises an exception on iteration
        response = self._response()
        self.assertFalse(response.is_rendered)

        def iteration():
            for x in response:
                pass
        self.assertRaises(ContentNotRenderedError, iteration)
        self.assertFalse(response.is_rendered)

    def test_iteration_rendered(self):
        # iteration works for rendered responses
        response = self._response().render()
        res = [x for x in response]
        self.assertEqual(res, [b'foo'])

    def test_content_access_unrendered(self):
        # unrendered response raises an exception when content is accessed
        response = self._response()
        self.assertFalse(response.is_rendered)
        self.assertRaises(ContentNotRenderedError, lambda: response.content)
        self.assertFalse(response.is_rendered)

    def test_content_access_rendered(self):
        # rendered response content can be accessed
        response = self._response().render()
        self.assertEqual(response.content, b'foo')

    def test_set_content(self):
        # content can be overridden
        response = self._response()
        self.assertFalse(response.is_rendered)
        response.content = 'spam'
        self.assertTrue(response.is_rendered)
        self.assertEqual(response.content, b'spam')
        response.content = 'baz'
        self.assertEqual(response.content, b'baz')

    def test_dict_context(self):
        response = self._response('{{ foo }}{{ processors }}',
                                  {'foo': 'bar'})
        self.assertEqual(response.context_data, {'foo': 'bar'})
        response.render()
        self.assertEqual(response.content, b'bar')

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_context_instance(self):
        response = self._response('{{ foo }}{{ processors }}',
                                  Context({'foo': 'bar'}))
        self.assertEqual(response.context_data.__class__, Context)
        response.render()
        self.assertEqual(response.content, b'bar')

    def test_kwargs(self):
        response = self._response(content_type='application/json', status=504)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.status_code, 504)

    def test_args(self):
        response = SimpleTemplateResponse('', {}, 'application/json', 504)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.status_code, 504)

    @require_jinja2
    def test_using(self):
        response = SimpleTemplateResponse('template_tests/using.html').render()
        self.assertEqual(response.content, b'DTL\n')
        response = SimpleTemplateResponse('template_tests/using.html', using='django').render()
        self.assertEqual(response.content, b'DTL\n')
        response = SimpleTemplateResponse('template_tests/using.html', using='jinja2').render()
        self.assertEqual(response.content, b'Jinja2\n')

    def test_post_callbacks(self):
        "Rendering a template response triggers the post-render callbacks"
        post = []

        def post1(obj):
            post.append('post1')

        def post2(obj):
            post.append('post2')

        response = SimpleTemplateResponse('first/test.html', {})
        response.add_post_render_callback(post1)
        response.add_post_render_callback(post2)

        # When the content is rendered, all the callbacks are invoked, too.
        response.render()
        self.assertEqual(response.content, b'First template\n')
        self.assertEqual(post, ['post1', 'post2'])

    def test_pickling(self):
        # Create a template response. The context is
        # known to be unpicklable (e.g., a function).
        response = SimpleTemplateResponse('first/test.html', {
            'value': 123,
            'fn': datetime.now,
        })
        self.assertRaises(ContentNotRenderedError,
                          pickle.dumps, response)

        # But if we render the response, we can pickle it.
        response.render()
        pickled_response = pickle.dumps(response)
        unpickled_response = pickle.loads(pickled_response)

        self.assertEqual(unpickled_response.content, response.content)
        self.assertEqual(unpickled_response['content-type'], response['content-type'])
        self.assertEqual(unpickled_response.status_code, response.status_code)

        # ...and the unpickled response doesn't have the
        # template-related attributes, so it can't be re-rendered
        template_attrs = ('template_name', 'context_data', '_post_render_callbacks')
        for attr in template_attrs:
            self.assertFalse(hasattr(unpickled_response, attr))

        # ...and requesting any of those attributes raises an exception
        for attr in template_attrs:
            with self.assertRaises(AttributeError):
                getattr(unpickled_response, attr)

    def test_repickling(self):
        response = SimpleTemplateResponse('first/test.html', {
            'value': 123,
            'fn': datetime.now,
        })
        self.assertRaises(ContentNotRenderedError,
                          pickle.dumps, response)

        response.render()
        pickled_response = pickle.dumps(response)
        unpickled_response = pickle.loads(pickled_response)
        pickle.dumps(unpickled_response)

    def test_pickling_cookie(self):
        response = SimpleTemplateResponse('first/test.html', {
            'value': 123,
            'fn': datetime.now,
        })

        response.cookies['key'] = 'value'

        response.render()
        pickled_response = pickle.dumps(response, pickle.HIGHEST_PROTOCOL)
        unpickled_response = pickle.loads(pickled_response)

        self.assertEqual(unpickled_response.cookies['key'].value, 'value')


@override_settings(TEMPLATES=[{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [TEMPLATE_DIR],
    'OPTIONS': {
        'context_processors': [test_processor_name],
    },
}])
class TemplateResponseTest(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _response(self, template='foo', *args, **kwargs):
        self._request = self.factory.get('/')
        template = engines['django'].from_string(template)
        return TemplateResponse(self._request, template, *args, **kwargs)

    def test_render(self):
        response = self._response('{{ foo }}{{ processors }}').render()
        self.assertEqual(response.content, b'yes')

    def test_render_with_requestcontext(self):
        response = self._response('{{ foo }}{{ processors }}',
                                  {'foo': 'bar'}).render()
        self.assertEqual(response.content, b'baryes')

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_render_with_context(self):
        response = self._response('{{ foo }}{{ processors }}',
                                  Context({'foo': 'bar'})).render()
        self.assertEqual(response.content, b'bar')

    def test_context_processor_priority(self):
        # context processors should be overridden by passed-in context
        response = self._response('{{ foo }}{{ processors }}',
                                  {'processors': 'no'}).render()
        self.assertEqual(response.content, b'no')

    def test_kwargs(self):
        response = self._response(content_type='application/json',
                                  status=504)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.status_code, 504)

    def test_args(self):
        response = TemplateResponse(self.factory.get('/'), '', {},
                                    'application/json', 504)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.status_code, 504)

    @require_jinja2
    def test_using(self):
        request = self.factory.get('/')
        response = TemplateResponse(request, 'template_tests/using.html').render()
        self.assertEqual(response.content, b'DTL\n')
        response = TemplateResponse(request, 'template_tests/using.html', using='django').render()
        self.assertEqual(response.content, b'DTL\n')
        response = TemplateResponse(request, 'template_tests/using.html', using='jinja2').render()
        self.assertEqual(response.content, b'Jinja2\n')

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_custom_app(self):
        self._response('{{ foo }}', current_app="foobar")
        self.assertEqual(self._request.current_app, 'foobar')

    def test_pickling(self):
        # Create a template response. The context is
        # known to be unpicklable (e.g., a function).
        response = TemplateResponse(self.factory.get('/'),
            'first/test.html', {
                'value': 123,
                'fn': datetime.now,
            }
        )
        self.assertRaises(ContentNotRenderedError,
                          pickle.dumps, response)

        # But if we render the response, we can pickle it.
        response.render()
        pickled_response = pickle.dumps(response)
        unpickled_response = pickle.loads(pickled_response)

        self.assertEqual(unpickled_response.content, response.content)
        self.assertEqual(unpickled_response['content-type'], response['content-type'])
        self.assertEqual(unpickled_response.status_code, response.status_code)

        # ...and the unpickled response doesn't have the
        # template-related attributes, so it can't be re-rendered
        template_attrs = ('template_name', 'context_data',
            '_post_render_callbacks', '_request', '_current_app')
        for attr in template_attrs:
            self.assertFalse(hasattr(unpickled_response, attr))

        # ...and requesting any of those attributes raises an exception
        for attr in template_attrs:
            with self.assertRaises(AttributeError):
                getattr(unpickled_response, attr)

    def test_repickling(self):
        response = SimpleTemplateResponse('first/test.html', {
            'value': 123,
            'fn': datetime.now,
        })
        self.assertRaises(ContentNotRenderedError,
                          pickle.dumps, response)

        response.render()
        pickled_response = pickle.dumps(response)
        unpickled_response = pickle.loads(pickled_response)
        pickle.dumps(unpickled_response)


@override_settings(
    MIDDLEWARE_CLASSES=list(settings.MIDDLEWARE_CLASSES) + [
        'template_tests.test_response.CustomURLConfMiddleware'
    ],
    ROOT_URLCONF='template_tests.urls',
)
class CustomURLConfTest(SimpleTestCase):

    def test_custom_urlconf(self):
        response = self.client.get('/template_response_view/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This is where you can find the snark: /snark/')


@override_settings(
    CACHE_MIDDLEWARE_SECONDS=2.0,
    MIDDLEWARE_CLASSES=list(settings.MIDDLEWARE_CLASSES) + [
        'django.middleware.cache.FetchFromCacheMiddleware',
        'django.middleware.cache.UpdateCacheMiddleware',
    ],
    ROOT_URLCONF='template_tests.alternate_urls',
)
class CacheMiddlewareTest(SimpleTestCase):

    def test_middleware_caching(self):
        response = self.client.get('/template_response_view/')
        self.assertEqual(response.status_code, 200)

        time.sleep(1.0)

        response2 = self.client.get('/template_response_view/')
        self.assertEqual(response2.status_code, 200)

        self.assertEqual(response.content, response2.content)

        time.sleep(2.0)

        # Let the cache expire and test again
        response2 = self.client.get('/template_response_view/')
        self.assertEqual(response2.status_code, 200)

        self.assertNotEqual(response.content, response2.content)
