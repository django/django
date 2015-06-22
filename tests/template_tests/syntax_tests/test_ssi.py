from __future__ import unicode_literals

import os

from django.template import Context, Engine
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import (
    RemovedInDjango19Warning, RemovedInDjango110Warning,
)

from ..utils import ROOT, setup


@ignore_warnings(category=RemovedInDjango110Warning)
class SsiTagTests(SimpleTestCase):

    # Test normal behavior
    @setup({'ssi01': '{%% ssi "%s" %%}' % os.path.join(
        ROOT, 'templates', 'ssi_include.html',
    )})
    def test_ssi01(self):
        output = self.engine.render_to_string('ssi01')
        self.assertEqual(output, 'This is for testing an ssi include. {{ test }}\n')

    @setup({'ssi02': '{%% ssi "%s" %%}' % os.path.join(
        ROOT, 'not_here',
    )})
    def test_ssi02(self):
        output = self.engine.render_to_string('ssi02')
        self.assertEqual(output, ''),

    @setup({'ssi03': "{%% ssi '%s' %%}" % os.path.join(
        ROOT, 'not_here',
    )})
    def test_ssi03(self):
        output = self.engine.render_to_string('ssi03')
        self.assertEqual(output, ''),

    # Test passing as a variable
    @ignore_warnings(category=RemovedInDjango19Warning)
    @setup({'ssi04': '{% load ssi from future %}{% ssi ssi_file %}'})
    def test_ssi04(self):
        output = self.engine.render_to_string('ssi04', {
            'ssi_file': os.path.join(ROOT, 'templates', 'ssi_include.html')
        })
        self.assertEqual(output, 'This is for testing an ssi include. {{ test }}\n')

    @ignore_warnings(category=RemovedInDjango19Warning)
    @setup({'ssi05': '{% load ssi from future %}{% ssi ssi_file %}'})
    def test_ssi05(self):
        output = self.engine.render_to_string('ssi05', {'ssi_file': 'no_file'})
        self.assertEqual(output, '')

    # Test parsed output
    @setup({'ssi06': '{%% ssi "%s" parsed %%}' % os.path.join(
        ROOT, 'templates', 'ssi_include.html',
    )})
    def test_ssi06(self):
        output = self.engine.render_to_string('ssi06', {'test': 'Look ma! It parsed!'})
        self.assertEqual(output, 'This is for testing an ssi include. '
                                 'Look ma! It parsed!\n')

    @setup({'ssi07': '{%% ssi "%s" parsed %%}' % os.path.join(
        ROOT, 'not_here',
    )})
    def test_ssi07(self):
        output = self.engine.render_to_string('ssi07', {'test': 'Look ma! It parsed!'})
        self.assertEqual(output, '')

    # Test space in file name
    @setup({'ssi08': '{%% ssi "%s" %%}' % os.path.join(
        ROOT, 'templates', 'ssi include with spaces.html',
    )})
    def test_ssi08(self):
        output = self.engine.render_to_string('ssi08')
        self.assertEqual(output, 'This is for testing an ssi include '
                                 'with spaces in its name. {{ test }}\n')

    @setup({'ssi09': '{%% ssi "%s" parsed %%}' % os.path.join(
        ROOT, 'templates', 'ssi include with spaces.html',
    )})
    def test_ssi09(self):
        output = self.engine.render_to_string('ssi09', {'test': 'Look ma! It parsed!'})
        self.assertEqual(output, 'This is for testing an ssi include '
                                 'with spaces in its name. Look ma! It parsed!\n')


@ignore_warnings(category=RemovedInDjango110Warning)
class SSISecurityTests(SimpleTestCase):

    def setUp(self):
        self.ssi_dir = os.path.join(ROOT, "templates", "first")
        self.engine = Engine(allowed_include_roots=(self.ssi_dir,))

    def render_ssi(self, path):
        # the path must exist for the test to be reliable
        self.assertTrue(os.path.exists(path))
        return self.engine.from_string('{%% ssi "%s" %%}' % path).render(Context({}))

    def test_allowed_paths(self):
        acceptable_path = os.path.join(self.ssi_dir, "..", "first", "test.html")
        self.assertEqual(self.render_ssi(acceptable_path), 'First template\n')

    def test_relative_include_exploit(self):
        """
        May not bypass allowed_include_roots with relative paths

        e.g. if allowed_include_roots = ("/var/www",), it should not be
        possible to do {% ssi "/var/www/../../etc/passwd" %}
        """
        disallowed_paths = [
            os.path.join(self.ssi_dir, "..", "ssi_include.html"),
            os.path.join(self.ssi_dir, "..", "second", "test.html"),
        ]
        for disallowed_path in disallowed_paths:
            self.assertEqual(self.render_ssi(disallowed_path), '')
