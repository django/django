from unittest import mock

from django.http import HttpRequest
from django.template import (
    Context, Engine, RequestContext, Template, Variable, VariableDoesNotExist,
)
from django.template.context import RenderContext
from django.test import RequestFactory, SimpleTestCase


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
        self.assertEqual(c, mock.ANY)

    def test_push_context_manager(self):
        c = Context({"a": 1})
        with c.push():
            c['a'] = 2
            self.assertEqual(c['a'], 2)
        self.assertEqual(c['a'], 1)

        with c.push(a=3):
            self.assertEqual(c['a'], 3)
        self.assertEqual(c['a'], 1)

    def test_update_context_manager(self):
        c = Context({"a": 1})
        with c.update({}):
            c['a'] = 2
            self.assertEqual(c['a'], 2)
        self.assertEqual(c['a'], 1)

        with c.update({'a': 3}):
            self.assertEqual(c['a'], 3)
        self.assertEqual(c['a'], 1)

    def test_push_context_manager_with_context_object(self):
        c = Context({'a': 1})
        with c.push(Context({'a': 3})):
            self.assertEqual(c['a'], 3)
        self.assertEqual(c['a'], 1)

    def test_update_context_manager_with_context_object(self):
        c = Context({'a': 1})
        with c.update(Context({'a': 3})):
            self.assertEqual(c['a'], 3)
        self.assertEqual(c['a'], 1)

    def test_push_proper_layering(self):
        c = Context({'a': 1})
        c.push(Context({'b': 2}))
        c.push(Context({'c': 3, 'd': {'z': '26'}}))
        self.assertEqual(
            c.dicts,
            [
                {'False': False, 'None': None, 'True': True},
                {'a': 1},
                {'b': 2},
                {'c': 3, 'd': {'z': '26'}},
            ]
        )

    def test_update_proper_layering(self):
        c = Context({'a': 1})
        c.update(Context({'b': 2}))
        c.update(Context({'c': 3, 'd': {'z': '26'}}))
        self.assertEqual(
            c.dicts,
            [
                {'False': False, 'None': None, 'True': True},
                {'a': 1},
                {'b': 2},
                {'c': 3, 'd': {'z': '26'}},
            ]
        )

    def test_setdefault(self):
        c = Context()

        x = c.setdefault('x', 42)
        self.assertEqual(x, 42)
        self.assertEqual(c['x'], 42)

        x = c.setdefault('x', 100)
        self.assertEqual(x, 42)
        self.assertEqual(c['x'], 42)

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

        # push() limits access to the topmost dict
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

    def test_flatten_context_with_context(self):
        """
        Context.push() with a Context argument should work.
        """
        a = Context({'a': 2})
        a.push(Context({'z': '8'}))
        self.assertEqual(a.flatten(), {
            'False': False,
            'None': None,
            'True': True,
            'a': 2,
            'z': '8',
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

    def test_set_upward(self):
        c = Context({'a': 1})
        c.set_upward('a', 2)
        self.assertEqual(c.get('a'), 2)

    def test_set_upward_empty_context(self):
        empty_context = Context()
        empty_context.set_upward('a', 1)
        self.assertEqual(empty_context.get('a'), 1)

    def test_set_upward_with_push(self):
        """
        The highest context which has the given key is used.
        """
        c = Context({'a': 1})
        c.push({'a': 2})
        c.set_upward('a', 3)
        self.assertEqual(c.get('a'), 3)
        c.pop()
        self.assertEqual(c.get('a'), 1)

    def test_set_upward_with_push_no_match(self):
        """
        The highest context is used if the given key isn't found.
        """
        c = Context({'b': 1})
        c.push({'b': 2})
        c.set_upward('a', 2)
        self.assertEqual(len(c.dicts), 3)
        self.assertEqual(c.dicts[-1]['a'], 2)


class RequestContextTests(SimpleTestCase):
    request_factory = RequestFactory()

    def test_include_only(self):
        """
        #15721 -- ``{% include %}`` and ``RequestContext`` should work
        together.
        """
        engine = Engine(loaders=[
            ('django.template.loaders.locmem.Loader', {
                'child': '{{ var|default:"none" }}',
            }),
        ])
        request = self.request_factory.get('/')
        ctx = RequestContext(request, {'var': 'parent'})
        self.assertEqual(engine.from_string('{% include "child" %}').render(ctx), 'parent')
        self.assertEqual(engine.from_string('{% include "child" only %}').render(ctx), 'none')

    def test_stack_size(self):
        """Optimized RequestContext construction (#7116)."""
        request = self.request_factory.get('/')
        ctx = RequestContext(request, {})
        # The stack contains 4 items:
        # [builtins, supplied context, context processor, empty dict]
        self.assertEqual(len(ctx.dicts), 4)

    def test_context_comparable(self):
        # Create an engine without any context processors.
        test_data = {'x': 'y', 'v': 'z', 'd': {'o': object, 'a': 'b'}}

        # test comparing RequestContext to prevent problems if somebody
        # adds __eq__ in the future
        request = self.request_factory.get('/')

        self.assertEqual(
            RequestContext(request, dict_=test_data),
            RequestContext(request, dict_=test_data),
        )

    def test_modify_context_and_render(self):
        template = Template('{{ foo }}')
        request = self.request_factory.get('/')
        context = RequestContext(request, {})
        context['foo'] = 'foo'
        self.assertEqual(template.render(context), 'foo')
