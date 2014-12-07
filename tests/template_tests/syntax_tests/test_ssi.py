import os
import warnings

from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango19Warning

from ..utils import ROOT, setup


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
    @setup({'ssi04': '{% load ssi from future %}{% ssi ssi_file %}'})
    def test_ssi04(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RemovedInDjango19Warning)
            output = self.engine.render_to_string('ssi04', {
                'ssi_file': os.path.join(ROOT, 'templates', 'ssi_include.html')
            })
        self.assertEqual(output, 'This is for testing an ssi include. {{ test }}\n')

    @setup({'ssi05': '{% load ssi from future %}{% ssi ssi_file %}'})
    def test_ssi05(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RemovedInDjango19Warning)
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
