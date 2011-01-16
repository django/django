import os
from django.utils import unittest
from django.test import RequestFactory, TestCase
from django.conf import settings
import django.template.context
from django.template import Template, Context, RequestContext
from django.template.response import (TemplateResponse, SimpleTemplateResponse,
                                      ContentNotRenderedError)

def test_processor(request):
    return {'processors': 'yes'}
test_processor_name = 'regressiontests.templates.response.test_processor'


# A test middleware that installs a temporary URLConf
class CustomURLConfMiddleware(object):
    def process_request(self, request):
        request.urlconf = 'regressiontests.templates.alternate_urls'


class BaseTemplateResponseTest(unittest.TestCase):
    # tests rely on fact that global context
    # processors should only work when RequestContext is used.

    def setUp(self):
        self.factory = RequestFactory()
        self._old_processors = settings.TEMPLATE_CONTEXT_PROCESSORS
        self._old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_CONTEXT_PROCESSORS = [test_processor_name]
        settings.TEMPLATE_DIRS = (
            os.path.join(
                os.path.dirname(__file__),
                'templates'
            ),
        )
        # Force re-evaluation of the contex processor list
        django.template.context._standard_context_processors = None

    def tearDown(self):
        settings.TEMPLATE_DIRS = self._old_TEMPLATE_DIRS
        settings.TEMPLATE_CONTEXT_PROCESSORS = self._old_processors
        # Force re-evaluation of the contex processor list
        django.template.context._standard_context_processors = None


class SimpleTemplateResponseTest(BaseTemplateResponseTest):

    def _response(self, template='foo', *args, **kwargs):
        return SimpleTemplateResponse(Template(template), *args, **kwargs)

    def test_template_resolving(self):
        response = SimpleTemplateResponse('first/test.html')
        response.render()
        self.assertEqual('First template\n', response.content)

        templates = ['foo.html', 'second/test.html', 'first/test.html']
        response = SimpleTemplateResponse(templates)
        response.render()
        self.assertEqual('Second template\n', response.content)

        response = self._response()
        response.render()
        self.assertEqual(response.content, 'foo')

    def test_explicit_baking(self):
        # explicit baking
        response = self._response()
        self.assertFalse(response.is_rendered)
        response.render()
        self.assertTrue(response.is_rendered)

    def test_render(self):
        # response is not re-rendered without the render call
        response = self._response().render()
        self.assertEqual(response.content, 'foo')

        # rebaking doesn't change the rendered content
        response.template_name = Template('bar{{ baz }}')
        response.render()
        self.assertEqual(response.content, 'foo')

        # but rendered content can be overridden by manually
        # setting content
        response.content = 'bar'
        self.assertEqual(response.content, 'bar')

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
        self.assertEqual(res, ['foo'])

    def test_content_access_unrendered(self):
        # unrendered response raises an exception when content is accessed
        response = self._response()
        self.assertFalse(response.is_rendered)
        self.assertRaises(ContentNotRenderedError, lambda: response.content)
        self.assertFalse(response.is_rendered)

    def test_content_access_rendered(self):
        # rendered response content can be accessed
        response = self._response().render()
        self.assertEqual(response.content, 'foo')

    def test_set_content(self):
        # content can be overriden
        response = self._response()
        self.assertFalse(response.is_rendered)
        response.content = 'spam'
        self.assertTrue(response.is_rendered)
        self.assertEqual(response.content, 'spam')
        response.content = 'baz'
        self.assertEqual(response.content, 'baz')

    def test_dict_context(self):
        response = self._response('{{ foo }}{{ processors }}',
                                  {'foo': 'bar'})
        self.assertEqual(response.context_data, {'foo': 'bar'})
        response.render()
        self.assertEqual(response.content, 'bar')

    def test_context_instance(self):
        response = self._response('{{ foo }}{{ processors }}',
                                  Context({'foo': 'bar'}))
        self.assertEqual(response.context_data.__class__, Context)
        response.render()
        self.assertEqual(response.content, 'bar')

    def test_kwargs(self):
        response = self._response(content_type = 'application/json', status=504)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.status_code, 504)

    def test_args(self):
        response = SimpleTemplateResponse('', {}, 'application/json', 504)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.status_code, 504)


class TemplateResponseTest(BaseTemplateResponseTest):

    def _response(self, template='foo', *args, **kwargs):
        return TemplateResponse(self.factory.get('/'), Template(template),
                                *args, **kwargs)

    def test_render(self):
        response = self._response('{{ foo }}{{ processors }}').render()
        self.assertEqual(response.content, 'yes')

    def test_render_with_requestcontext(self):
        response = self._response('{{ foo }}{{ processors }}',
                                  {'foo': 'bar'}).render()
        self.assertEqual(response.content, 'baryes')

    def test_render_with_context(self):
        response = self._response('{{ foo }}{{ processors }}',
                                  Context({'foo': 'bar'})).render()
        self.assertEqual(response.content, 'bar')

    def test_kwargs(self):
        response = self._response(content_type = 'application/json',
                                  status=504)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.status_code, 504)

    def test_args(self):
        response = TemplateResponse(self.factory.get('/'), '', {},
                                    'application/json', 504)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.status_code, 504)

    def test_custom_app(self):
        response = self._response('{{ foo }}', current_app="foobar")

        rc = response.resolve_context(response.context_data)

        self.assertEqual(rc.current_app, 'foobar')


class CustomURLConfTest(TestCase):
    urls = 'regressiontests.templates.urls'

    def setUp(self):
        self.old_MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES
        settings.MIDDLEWARE_CLASSES = list(settings.MIDDLEWARE_CLASSES) + [
            'regressiontests.templates.response.CustomURLConfMiddleware'
        ]

    def tearDown(self):
        settings.MIDDLEWARE_CLASSES = self.old_MIDDLEWARE_CLASSES

    def test_custom_urlconf(self):
        response = self.client.get('/template_response_view/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'This is where you can find the snark: /snark/')


