# -*- coding: utf-8 -*-

from django.http import HttpRequest
from django.template import (
    Context, RequestContext, Template, Variable, VariableDoesNotExist,
)
from django.template.context import RenderContext
from django.test import RequestFactory, SimpleTestCase, override_settings


class ContextTests(SimpleTestCase):

    def test_context(self):
        c = Context({"a": 1, "b": "xyzzy"})
        self.assertEqual(c["a"], 1)
        self.assertEqual(c.push(), {})
        c["a"] = 2
        self.assertEqual(c["a"], 2)
        self.assertEqual(c.get("a"), 2)
        self.assertEqual(c.pop(), {"a": 2})
        self.assertEqual(c["a"], 1)
        self.assertEqual(c.get("foo", 42), 42)

        with c.push():
            c['a'] = 2
            self.assertEqual(c['a'], 2)
        self.assertEqual(c['a'], 1)

        with c.push(a=3):
            self.assertEqual(c['a'], 3)
        self.assertEqual(c['a'], 1)

    def test_resolve_on_context_method(self):
        """
        #17778 -- Variable shouldn't resolve RequestContext methods
        """
        empty_context = Context()

        with self.assertRaises(VariableDoesNotExist):
            Variable('no_such_variable').resolve(empty_context)

        with self.assertRaises(VariableDoesNotExist):
            Variable('new').resolve(empty_context)

        self.assertEqual(
            Variable('new').resolve(Context({'new': 'foo'})),
            'foo',
        )

    def test_render_context(self):
        test_context = RenderContext({'fruit': 'papaya'})

        # Test that push() limits access to the topmost dict
        test_context.push()

        test_context['vegetable'] = 'artichoke'
        self.assertEqual(list(test_context), ['vegetable'])

        self.assertNotIn('fruit', test_context)
        with self.assertRaises(KeyError):
            test_context['fruit']
        self.assertIsNone(test_context.get('fruit'))

    def test_flatten_context(self):
        a = Context()
        a.update({'a': 2})
        a.update({'b': 4})
        a.update({'c': 8})

        self.assertEqual(a.flatten(), {
            'False': False, 'None': None, 'True': True,
            'a': 2, 'b': 4, 'c': 8
        })

    def test_context_comparable(self):
        """
        #21765 -- equality comparison should work
        """

        test_data = {'x': 'y', 'v': 'z', 'd': {'o': object, 'a': 'b'}}

        self.assertEqual(Context(test_data), Context(test_data))

        a = Context()
        b = Context()
        self.assertEqual(a, b)

        # update only a
        a.update({'a': 1})
        self.assertNotEqual(a, b)

        # update both to check regression
        a.update({'c': 3})
        b.update({'c': 3})
        self.assertNotEqual(a, b)

        # make contexts equals again
        b.update({'a': 1})
        self.assertEqual(a, b)

    def test_copy_request_context_twice(self):
        """
        #24273 -- Copy twice shouldn't raise an exception
        """
        RequestContext(HttpRequest()).new().new()


class RequestContextTests(SimpleTestCase):

    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'loaders': [
                ('django.template.loaders.locmem.Loader', {
                    'child': '{{ var|default:"none" }}',
                }),
            ],
        },
    }])
    def test_include_only(self):
        """
        #15721 -- ``{% include %}`` and ``RequestContext`` should work
        together.
        """
        request = RequestFactory().get('/')
        ctx = RequestContext(request, {'var': 'parent'})
        self.assertEqual(Template('{% include "child" %}').render(ctx), 'parent')
        self.assertEqual(Template('{% include "child" only %}').render(ctx), 'none')

    def test_stack_size(self):
        """
        #7116 -- Optimize RequetsContext construction
        """
        request = RequestFactory().get('/')
        ctx = RequestContext(request, {})
        # The stack should now contain 3 items:
        # [builtins, supplied context, context processor, empty dict]
        self.assertEqual(len(ctx.dicts), 4)

    def test_context_comparable(self):
        # Create an engine without any context processors.
        test_data = {'x': 'y', 'v': 'z', 'd': {'o': object, 'a': 'b'}}

        # test comparing RequestContext to prevent problems if somebody
        # adds __eq__ in the future
        request = RequestFactory().get('/')

        self.assertEqual(
            RequestContext(request, dict_=test_data),
            RequestContext(request, dict_=test_data),
        )

    def test_modify_context_and_render(self):
        template = Template('{{ foo }}')
        request = RequestFactory().get('/')
        context = RequestContext(request, {})
        context['foo'] = 'foo'
        self.assertEqual(template.render(context), 'foo')
