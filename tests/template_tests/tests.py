# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys

from django.contrib.auth.models import Group
from django.core import urlresolvers
from django.template import (
    Context, Template, TemplateSyntaxError, base as template_base, engines,
    loader,
)
from django.test import SimpleTestCase, override_settings
from django.utils._os import upath

TEMPLATES_DIR = os.path.join(os.path.dirname(upath(__file__)), 'templates')


class TemplateTests(SimpleTestCase):

    @override_settings(DEBUG=True)
    def test_string_origin(self):
        template = Template('string template')
        self.assertEqual(template.origin.source, 'string template')


class TemplateRegressionTests(SimpleTestCase):

    def test_token_smart_split(self):
        # Regression test for #7027
        token = template_base.Token(template_base.TOKEN_BLOCK, 'sometag _("Page not found") value|yesno:_("yes,no")')
        split = token.split_contents()
        self.assertEqual(split, ["sometag", '_("Page not found")', 'value|yesno:_("yes,no")'])

    @override_settings(SETTINGS_MODULE=None, DEBUG=True)
    def test_url_reverse_no_settings_module(self):
        # Regression test for #9005
        t = Template('{% url will_not_match %}')
        c = Context()
        with self.assertRaises(urlresolvers.NoReverseMatch):
            t.render(c)

    @override_settings(
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'OPTIONS': {'string_if_invalid': '%s is invalid'},
        }],
        SETTINGS_MODULE='also_something',
    )
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

    @override_settings(DEBUG=True)
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
            t.render()

    def test_debug_tag_non_ascii(self):
        """
        Test non-ASCII model representation in debug output (#23060).
        """
        Group.objects.create(name="清風")
        c1 = Context({"objs": Group.objects.all()})
        t1 = Template('{% debug %}')
        self.assertIn("清風", t1.render(c1))

    def test_extends_generic_template(self):
        """
        {% extends %} accepts django.template.backends.django.Template (#24338).
        """
        parent = engines['django'].from_string(
            '{% block content %}parent{% endblock %}')
        child = engines['django'].from_string(
            '{% extends parent %}{% block content %}child{% endblock %}')
        self.assertEqual(child.render({'parent': parent}), 'child')
