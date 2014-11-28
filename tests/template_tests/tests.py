# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import unittest

from django import template
from django.contrib.auth.models import Group
from django.core import urlresolvers
from django.template import (base as template_base, loader,
    Context, RequestContext, Template, TemplateSyntaxError)
from django.template.engine import Engine
from django.template.loaders import app_directories, filesystem
from django.test import RequestFactory, SimpleTestCase
from django.test.utils import override_settings, extend_sys_path
from django.utils._os import upath


class TemplateLoaderTests(SimpleTestCase):

    def test_loaders_security(self):
        ad_loader = app_directories.Loader(Engine.get_default())
        fs_loader = filesystem.Loader(Engine.get_default())

        def test_template_sources(path, template_dirs, expected_sources):
            if isinstance(expected_sources, list):
                # Fix expected sources so they are abspathed
                expected_sources = [os.path.abspath(s) for s in expected_sources]
            # Test the two loaders (app_directores and filesystem).
            func1 = lambda p, t: list(ad_loader.get_template_sources(p, t))
            func2 = lambda p, t: list(fs_loader.get_template_sources(p, t))
            for func in (func1, func2):
                if isinstance(expected_sources, list):
                    self.assertEqual(func(path, template_dirs), expected_sources)
                else:
                    self.assertRaises(expected_sources, func, path, template_dirs)

        template_dirs = ['/dir1', '/dir2']
        test_template_sources('index.html', template_dirs,
                              ['/dir1/index.html', '/dir2/index.html'])
        test_template_sources('/etc/passwd', template_dirs, [])
        test_template_sources('etc/passwd', template_dirs,
                              ['/dir1/etc/passwd', '/dir2/etc/passwd'])
        test_template_sources('../etc/passwd', template_dirs, [])
        test_template_sources('../../../etc/passwd', template_dirs, [])
        test_template_sources('/dir1/index.html', template_dirs,
                              ['/dir1/index.html'])
        test_template_sources('../dir2/index.html', template_dirs,
                              ['/dir2/index.html'])
        test_template_sources('/dir1blah', template_dirs, [])
        test_template_sources('../dir1blah', template_dirs, [])

        # UTF-8 bytestrings are permitted.
        test_template_sources(b'\xc3\x85ngstr\xc3\xb6m', template_dirs,
                              ['/dir1/Ångström', '/dir2/Ångström'])
        # Unicode strings are permitted.
        test_template_sources('Ångström', template_dirs,
                              ['/dir1/Ångström', '/dir2/Ångström'])
        test_template_sources('Ångström', [b'/Stra\xc3\x9fe'], ['/Straße/Ångström'])
        test_template_sources(b'\xc3\x85ngstr\xc3\xb6m', [b'/Stra\xc3\x9fe'],
                              ['/Straße/Ångström'])
        # Invalid UTF-8 encoding in bytestrings is not. Should raise a
        # semi-useful error message.
        test_template_sources(b'\xc3\xc3', template_dirs, UnicodeDecodeError)

        # Case insensitive tests (for win32). Not run unless we're on
        # a case insensitive operating system.
        if os.path.normcase('/TEST') == os.path.normpath('/test'):
            template_dirs = ['/dir1', '/DIR2']
            test_template_sources('index.html', template_dirs,
                                  ['/dir1/index.html', '/DIR2/index.html'])
            test_template_sources('/DIR1/index.HTML', template_dirs,
                                  ['/DIR1/index.HTML'])

    @override_settings(TEMPLATE_LOADERS=['django.template.loaders.filesystem.Loader'])
    # Turn TEMPLATE_DEBUG on, so that the origin file name will be kept with
    # the compiled templates.
    @override_settings(TEMPLATE_DEBUG=True)
    def test_loader_debug_origin(self):
        # We rely on the fact that runtests.py sets up TEMPLATE_DIRS to
        # point to a directory containing a login.html file.
        load_name = 'login.html'

        # We also rely on the fact the file system and app directories loaders
        # both inherit the load_template method from the base Loader class, so
        # we only need to test one of them.
        template = loader.get_template(load_name).template
        template_name = template.nodelist[0].source[0].name
        self.assertTrue(template_name.endswith(load_name),
            'Template loaded by filesystem loader has incorrect name for debug page: %s' % template_name)

    @override_settings(TEMPLATE_LOADERS=[
        ('django.template.loaders.cached.Loader',
            ['django.template.loaders.filesystem.Loader']),
    ])
    @override_settings(TEMPLATE_DEBUG=True)
    def test_cached_loader_debug_origin(self):
        # Same comment as in test_loader_debug_origin.
        load_name = 'login.html'

        # Test the cached loader separately since it overrides load_template.
        template = loader.get_template(load_name).template
        template_name = template.nodelist[0].source[0].name
        self.assertTrue(template_name.endswith(load_name),
            'Template loaded through cached loader has incorrect name for debug page: %s' % template_name)

        template = loader.get_template(load_name).template
        template_name = template.nodelist[0].source[0].name
        self.assertTrue(template_name.endswith(load_name),
            'Cached template loaded through cached loader has incorrect name for debug page: %s' % template_name)

    @override_settings(TEMPLATE_DEBUG=True)
    def test_loader_origin(self):
        template = loader.get_template('login.html')
        self.assertEqual(template.origin.loadname, 'login.html')

    @override_settings(TEMPLATE_DEBUG=True)
    def test_string_origin(self):
        template = Template('string template')
        self.assertEqual(template.origin.source, 'string template')

    def test_debug_false_origin(self):
        template = loader.get_template('login.html')
        self.assertEqual(template.origin, None)

    # TEMPLATE_DEBUG must be true, otherwise the exception raised
    # during {% include %} processing will be suppressed.
    @override_settings(TEMPLATE_DEBUG=True)
    # Test the base loader class via the app loader. load_template
    # from base is used by all shipped loaders excepting cached,
    # which has its own test.
    @override_settings(TEMPLATE_LOADERS=['django.template.loaders.app_directories.Loader'])
    def test_include_missing_template(self):
        """
        Tests that the correct template is identified as not existing
        when {% include %} specifies a template that does not exist.
        """
        load_name = 'test_include_error.html'
        r = None
        try:
            tmpl = loader.select_template([load_name])
            r = tmpl.render(template.Context({}))
        except template.TemplateDoesNotExist as e:
            self.assertEqual(e.args[0], 'missing.html')
        self.assertEqual(r, None, 'Template rendering unexpectedly succeeded, produced: ->%r<-' % r)

    # TEMPLATE_DEBUG must be true, otherwise the exception raised
    # during {% include %} processing will be suppressed.
    @override_settings(TEMPLATE_DEBUG=True)
    # Test the base loader class via the app loader. load_template
    # from base is used by all shipped loaders excepting cached,
    # which has its own test.
    @override_settings(TEMPLATE_LOADERS=['django.template.loaders.app_directories.Loader'])
    def test_extends_include_missing_baseloader(self):
        """
        Tests that the correct template is identified as not existing
        when {% extends %} specifies a template that does exist, but
        that template has an {% include %} of something that does not
        exist. See #12787.
        """
        load_name = 'test_extends_error.html'
        tmpl = loader.get_template(load_name)
        r = None
        try:
            r = tmpl.render(template.Context({}))
        except template.TemplateDoesNotExist as e:
            self.assertEqual(e.args[0], 'missing.html')
        self.assertEqual(r, None, 'Template rendering unexpectedly succeeded, produced: ->%r<-' % r)

    @override_settings(TEMPLATE_DEBUG=True)
    def test_extends_include_missing_cachedloader(self):
        """
        Same as test_extends_include_missing_baseloader, only tests
        behavior of the cached loader instead of base loader.
        """
        with override_settings(TEMPLATE_LOADERS=[
            ('django.template.loaders.cached.Loader', [
                'django.template.loaders.app_directories.Loader',
            ]),
        ]):
            load_name = 'test_extends_error.html'
            tmpl = loader.get_template(load_name)
            r = None
            try:
                r = tmpl.render(template.Context({}))
            except template.TemplateDoesNotExist as e:
                self.assertEqual(e.args[0], 'missing.html')
            self.assertEqual(r, None, 'Template rendering unexpectedly succeeded, produced: ->%r<-' % r)

            # For the cached loader, repeat the test, to ensure the first attempt did not cache a
            # result that behaves incorrectly on subsequent attempts.
            tmpl = loader.get_template(load_name)
            try:
                tmpl.render(template.Context({}))
            except template.TemplateDoesNotExist as e:
                self.assertEqual(e.args[0], 'missing.html')
            self.assertEqual(r, None, 'Template rendering unexpectedly succeeded, produced: ->%r<-' % r)

    def test_include_template_argument(self):
        """
        Support any render() supporting object
        """
        ctx = Context({
            'tmpl': Template('This worked!'),
        })
        outer_tmpl = Template('{% include tmpl %}')
        output = outer_tmpl.render(ctx)
        self.assertEqual(output, 'This worked!')

    @override_settings(TEMPLATE_DEBUG=True)
    def test_include_immediate_missing(self):
        """
        Regression test for #16417 -- {% include %} tag raises TemplateDoesNotExist at compile time if TEMPLATE_DEBUG is True

        Test that an {% include %} tag with a literal string referencing a
        template that does not exist does not raise an exception at parse
        time.
        """
        tmpl = Template('{% include "this_does_not_exist.html" %}')
        self.assertIsInstance(tmpl, Template)

    @override_settings(TEMPLATE_DEBUG=True)
    def test_include_recursive(self):
        comments = [
            {
                'comment': 'A1',
                'children': [
                    {'comment': 'B1', 'children': []},
                    {'comment': 'B2', 'children': []},
                    {'comment': 'B3', 'children': [
                        {'comment': 'C1', 'children': []}
                    ]},
                ]
            }
        ]

        t = loader.get_template('recursive_include.html')
        self.assertEqual(
            "Recursion!  A1  Recursion!  B1   B2   B3  Recursion!  C1",
            t.render(Context({'comments': comments})).replace(' ', '').replace('\n', ' ').strip(),
        )


class TemplateRegressionTests(SimpleTestCase):

    def test_token_smart_split(self):
        # Regression test for #7027
        token = template_base.Token(template_base.TOKEN_BLOCK, 'sometag _("Page not found") value|yesno:_("yes,no")')
        split = token.split_contents()
        self.assertEqual(split, ["sometag", '_("Page not found")', 'value|yesno:_("yes,no")'])

    @override_settings(SETTINGS_MODULE=None, TEMPLATE_DEBUG=True)
    def test_url_reverse_no_settings_module(self):
        # Regression test for #9005
        t = Template('{% url will_not_match %}')
        c = Context()
        with self.assertRaises(urlresolvers.NoReverseMatch):
            t.render(c)

    @override_settings(TEMPLATE_STRING_IF_INVALID='%s is invalid', SETTINGS_MODULE='also_something')
    def test_url_reverse_view_name(self):
        # Regression test for #19827
        t = Template('{% url will_not_match %}')
        c = Context()
        try:
            t.render(c)
        except urlresolvers.NoReverseMatch:
            tb = sys.exc_info()[2]
            depth = 0
            while tb.tb_next is not None:
                tb = tb.tb_next
                depth += 1
            self.assertGreater(depth, 5,
                "The traceback context was lost when reraising the traceback. See #19827")

    @override_settings(DEBUG=True, TEMPLATE_DEBUG=True)
    def test_no_wrapped_exception(self):
        """
        The template system doesn't wrap exceptions, but annotates them.
        Refs #16770
        """
        c = Context({"coconuts": lambda: 42 / 0})
        t = Template("{{ coconuts }}")
        with self.assertRaises(ZeroDivisionError) as cm:
            t.render(c)

        self.assertEqual(cm.exception.django_template_source[1], (0, 14))

    def test_invalid_block_suggestion(self):
        # See #7876
        try:
            Template("{% if 1 %}lala{% endblock %}{% endif %}")
        except TemplateSyntaxError as e:
            self.assertEqual(e.args[0], "Invalid block tag: 'endblock', expected 'elif', 'else' or 'endif'")

    def test_ifchanged_concurrency(self):
        # Tests for #15849
        template = Template('[0{% for x in foo %},{% with var=get_value %}{% ifchanged %}{{ var }}{% endifchanged %}{% endwith %}{% endfor %}]')

        # Using generator to mimic concurrency.
        # The generator is not passed to the 'for' loop, because it does a list(values)
        # instead, call gen.next() in the template to control the generator.
        def gen():
            yield 1
            yield 2
            # Simulate that another thread is now rendering.
            # When the IfChangeNode stores state at 'self' it stays at '3' and skip the last yielded value below.
            iter2 = iter([1, 2, 3])
            output2 = template.render(Context({'foo': range(3), 'get_value': lambda: next(iter2)}))
            self.assertEqual(output2, '[0,1,2,3]', 'Expected [0,1,2,3] in second parallel template, got {}'.format(output2))
            yield 3

        gen1 = gen()
        output1 = template.render(Context({'foo': range(3), 'get_value': lambda: next(gen1)}))
        self.assertEqual(output1, '[0,1,2,3]', 'Expected [0,1,2,3] in first template, got {}'.format(output1))

    def test_cache_regression_20130(self):
        t = Template('{% load cache %}{% cache 1 regression_20130 %}foo{% endcache %}')
        cachenode = t.nodelist[1]
        self.assertEqual(cachenode.fragment_name, 'regression_20130')

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'default',
        },
        'template_fragments': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'fragments',
        },
    })
    def test_cache_fragment_cache(self):
        """
        When a cache called "template_fragments" is present, the cache tag
        will use it in preference to 'default'
        """
        t1 = Template('{% load cache %}{% cache 1 fragment %}foo{% endcache %}')
        t2 = Template('{% load cache %}{% cache 1 fragment using="default" %}bar{% endcache %}')

        ctx = Context()
        o1 = t1.render(ctx)
        o2 = t2.render(ctx)

        self.assertEqual(o1, 'foo')
        self.assertEqual(o2, 'bar')

    def test_cache_missing_backend(self):
        """
        When a cache that doesn't exist is specified, the cache tag will
        raise a TemplateSyntaxError
        '"""
        t = Template('{% load cache %}{% cache 1 backend using="unknown" %}bar{% endcache %}')

        ctx = Context()
        with self.assertRaises(TemplateSyntaxError):
            t.render(ctx)

    def test_ifchanged_render_once(self):
        """ Test for ticket #19890. The content of ifchanged template tag was
        rendered twice."""
        template = Template('{% ifchanged %}{% cycle "1st time" "2nd time" %}{% endifchanged %}')
        output = template.render(Context({}))
        self.assertEqual(output, '1st time')

    def test_super_errors(self):
        """
        Test behavior of the raise errors into included blocks.
        See #18169
        """
        t = loader.get_template('included_content.html')
        with self.assertRaises(urlresolvers.NoReverseMatch):
            t.render(Context({}))

    def test_debug_tag_non_ascii(self):
        """
        Test non-ASCII model representation in debug output (#23060).
        """
        Group.objects.create(name="清風")
        c1 = Context({"objs": Group.objects.all()})
        t1 = Template('{% debug %}')
        self.assertIn("清風", t1.render(c1))


class TemplateTagLoading(SimpleTestCase):

    def setUp(self):
        self.egg_dir = '%s/eggs' % os.path.dirname(upath(__file__))

    def test_load_error(self):
        ttext = "{% load broken_tag %}"
        self.assertRaises(template.TemplateSyntaxError, template.Template, ttext)
        try:
            template.Template(ttext)
        except template.TemplateSyntaxError as e:
            self.assertIn('ImportError', e.args[0])
            self.assertIn('Xtemplate', e.args[0])

    def test_load_error_egg(self):
        ttext = "{% load broken_egg %}"
        egg_name = '%s/tagsegg.egg' % self.egg_dir
        with extend_sys_path(egg_name):
            with self.assertRaises(template.TemplateSyntaxError):
                with self.settings(INSTALLED_APPS=['tagsegg']):
                    template.Template(ttext)
            try:
                with self.settings(INSTALLED_APPS=['tagsegg']):
                    template.Template(ttext)
            except template.TemplateSyntaxError as e:
                self.assertIn('ImportError', e.args[0])
                self.assertIn('Xtemplate', e.args[0])

    def test_load_working_egg(self):
        ttext = "{% load working_egg %}"
        egg_name = '%s/tagsegg.egg' % self.egg_dir
        with extend_sys_path(egg_name):
            with self.settings(INSTALLED_APPS=['tagsegg']):
                template.Template(ttext)


class RequestContextTests(unittest.TestCase):

    def setUp(self):
        self.fake_request = RequestFactory().get('/')

    @override_settings(TEMPLATE_LOADERS=[
        ('django.template.loaders.locmem.Loader', {
            'child': '{{ var|default:"none" }}',
        }),
    ])
    def test_include_only(self):
        """
        Regression test for #15721, ``{% include %}`` and ``RequestContext``
        not playing together nicely.
        """
        ctx = RequestContext(self.fake_request, {'var': 'parent'})
        self.assertEqual(
            template.Template('{% include "child" %}').render(ctx),
            'parent'
        )
        self.assertEqual(
            template.Template('{% include "child" only %}').render(ctx),
            'none'
        )

    def test_stack_size(self):
        """
        Regression test for #7116, Optimize RequetsContext construction
        """
        ctx = RequestContext(self.fake_request, {})
        # The stack should now contain 3 items:
        # [builtins, supplied context, context processor]
        self.assertEqual(len(ctx.dicts), 3)

    @override_settings(TEMPLATE_CONTEXT_PROCESSORS=())
    def test_context_comparable(self):
        test_data = {'x': 'y', 'v': 'z', 'd': {'o': object, 'a': 'b'}}

        # test comparing RequestContext to prevent problems if somebody
        # adds __eq__ in the future
        request = RequestFactory().get('/')

        self.assertEqual(
            RequestContext(request, dict_=test_data),
            RequestContext(request, dict_=test_data)
        )


class SSITests(SimpleTestCase):
    def setUp(self):
        self.this_dir = os.path.dirname(os.path.abspath(upath(__file__)))
        self.ssi_dir = os.path.join(self.this_dir, "templates", "first")

    def render_ssi(self, path):
        # the path must exist for the test to be reliable
        self.assertTrue(os.path.exists(path))
        return template.Template('{%% ssi "%s" %%}' % path).render(Context())

    def test_allowed_paths(self):
        acceptable_path = os.path.join(self.ssi_dir, "..", "first", "test.html")
        with override_settings(ALLOWED_INCLUDE_ROOTS=(self.ssi_dir,)):
            self.assertEqual(self.render_ssi(acceptable_path), 'First template\n')

    def test_relative_include_exploit(self):
        """
        May not bypass ALLOWED_INCLUDE_ROOTS with relative paths

        e.g. if ALLOWED_INCLUDE_ROOTS = ("/var/www",), it should not be
        possible to do {% ssi "/var/www/../../etc/passwd" %}
        """
        disallowed_paths = [
            os.path.join(self.ssi_dir, "..", "ssi_include.html"),
            os.path.join(self.ssi_dir, "..", "second", "test.html"),
        ]
        with override_settings(ALLOWED_INCLUDE_ROOTS=(self.ssi_dir,)):
            for path in disallowed_paths:
                self.assertEqual(self.render_ssi(path), '')
