# -*- encoding: utf-8 -*-
import os
import re
import shutil

from django.core import management
from django.test import TestCase


LOCALE='de'

class ExtractorTests(TestCase):

    PO_FILE='locale/%s/LC_MESSAGES/django.po' % LOCALE

    def setUp(self):
        self._cwd = os.getcwd()
        self.test_dir = os.path.abspath(os.path.dirname(__file__))

    def _rmrf(self, dname):
        if os.path.commonprefix([self.test_dir, os.path.abspath(dname)]) != self.test_dir:
            return
        shutil.rmtree(dname)

    def tearDown(self):
        os.chdir(self.test_dir)
        try:
            self._rmrf('locale/%s' % LOCALE)
        except OSError:
            pass
        os.chdir(self._cwd)

    def assertMsgId(self, msgid, s, use_quotes=True):
        if use_quotes:
            msgid = '"%s"' % msgid
        msgid = re.escape(msgid)
        return self.assertTrue(re.search('^msgid %s' % msgid, s, re.MULTILINE))

    def assertNotMsgId(self, msgid, s, use_quotes=True):
        if use_quotes:
            msgid = '"%s"' % msgid
        msgid = re.escape(msgid)
        return self.assertTrue(not re.search('^msgid %s' % msgid, s, re.MULTILINE))


class BasicExtractorTests(ExtractorTests):

    def test_comments_extractor(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        self.assertTrue('#. Translators: This comment should be extracted' in po_contents)
        self.assertTrue('This comment should not be extracted' not in po_contents)
        # Comments in templates
        self.assertTrue('#. Translators: Django template comment for translators' in po_contents)
        self.assertTrue("#. Translators: Django comment block for translators\n#. string's meaning unveiled" in po_contents)

        self.assertTrue('#. Translators: One-line translator comment #1' in po_contents)
        self.assertTrue('#. Translators: Two-line translator comment #1\n#. continued here.' in po_contents)

        self.assertTrue('#. Translators: One-line translator comment #2' in po_contents)
        self.assertTrue('#. Translators: Two-line translator comment #2\n#. continued here.' in po_contents)

        self.assertTrue('#. Translators: One-line translator comment #3' in po_contents)
        self.assertTrue('#. Translators: Two-line translator comment #3\n#. continued here.' in po_contents)

        self.assertTrue('#. Translators: One-line translator comment #4' in po_contents)
        self.assertTrue('#. Translators: Two-line translator comment #4\n#. continued here.' in po_contents)

        self.assertTrue('#. Translators: One-line translator comment #5 -- with non ASCII characters: áéíóúö' in po_contents)
        self.assertTrue('#. Translators: Two-line translator comment #5 -- with non ASCII characters: áéíóúö\n#. continued here.' in po_contents)

    def test_templatize(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        self.assertMsgId('I think that 100%% is more that 50%% of anything.', po_contents)
        self.assertMsgId('I think that 100%% is more that 50%% of %(obj)s.', po_contents)

    def test_extraction_error(self):
        os.chdir(self.test_dir)
        shutil.copyfile('./templates/template_with_error.tpl', './templates/template_with_error.html')
        self.assertRaises(SyntaxError, management.call_command, 'makemessages', locale=LOCALE, verbosity=0)
        try:
            management.call_command('makemessages', locale=LOCALE, verbosity=0)
        except SyntaxError, e:
            self.assertRegexpMatches(
                str(e),
                r'Translation blocks must not include other block tags: blocktrans \(file templates[/\\]template_with_error\.html, line 3\)'
            )
        finally:
            os.remove('./templates/template_with_error.html')
            os.remove('./templates/template_with_error.html.py') # Waiting for #8536 to be fixed

    def test_template_message_context_extractor(self):
        """
        Ensure that message contexts are correctly extracted for the
        {% trans %} and {% blocktrans %} template tags.
        Refs #14806.
        """
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        # {% trans %}
        self.assertTrue('msgctxt "Special trans context #1"' in po_contents)
        self.assertTrue("Translatable literal #7a" in po_contents)
        self.assertTrue('msgctxt "Special trans context #2"' in po_contents)
        self.assertTrue("Translatable literal #7b" in po_contents)
        self.assertTrue('msgctxt "Special trans context #3"' in po_contents)
        self.assertTrue("Translatable literal #7c" in po_contents)

        # {% blocktrans %}
        self.assertTrue('msgctxt "Special blocktrans context #1"' in po_contents)
        self.assertTrue("Translatable literal #8a" in po_contents)
        self.assertTrue('msgctxt "Special blocktrans context #2"' in po_contents)
        self.assertTrue("Translatable literal #8b-singular" in po_contents)
        self.assertTrue("Translatable literal #8b-plural" in po_contents)
        self.assertTrue('msgctxt "Special blocktrans context #3"' in po_contents)
        self.assertTrue("Translatable literal #8c-singular" in po_contents)
        self.assertTrue("Translatable literal #8c-plural" in po_contents)
        self.assertTrue('msgctxt "Special blocktrans context #4"' in po_contents)
        self.assertTrue("Translatable literal #8d" in po_contents)

class JavascriptExtractorTests(ExtractorTests):

    PO_FILE='locale/%s/LC_MESSAGES/djangojs.po' % LOCALE

    def test_javascript_literals(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', domain='djangojs', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        self.assertMsgId('This literal should be included.', po_contents)
        self.assertMsgId('This one as well.', po_contents)
        self.assertMsgId(r'He said, \"hello\".', po_contents)
        self.assertMsgId("okkkk", po_contents)
        self.assertMsgId("TEXT", po_contents)
        self.assertMsgId("It's at http://example.com", po_contents)
        self.assertMsgId("String", po_contents)
        self.assertMsgId("/* but this one will be too */ 'cause there is no way of telling...", po_contents)
        self.assertMsgId("foo", po_contents)
        self.assertMsgId("bar", po_contents)
        self.assertMsgId("baz", po_contents)
        self.assertMsgId("quz", po_contents)
        self.assertMsgId("foobar", po_contents)

class IgnoredExtractorTests(ExtractorTests):

    def test_ignore_option(self):
        os.chdir(self.test_dir)
        pattern1 = os.path.join('ignore_dir', '*')
        management.call_command('makemessages', locale=LOCALE, verbosity=0, ignore_patterns=[pattern1])
        self.assertTrue(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        self.assertMsgId('This literal should be included.', po_contents)
        self.assertNotMsgId('This should be ignored.', po_contents)


class SymlinkExtractorTests(ExtractorTests):

    def setUp(self):
        self._cwd = os.getcwd()
        self.test_dir = os.path.abspath(os.path.dirname(__file__))
        self.symlinked_dir = os.path.join(self.test_dir, 'templates_symlinked')

    def tearDown(self):
        super(SymlinkExtractorTests, self).tearDown()
        os.chdir(self.test_dir)
        try:
            os.remove(self.symlinked_dir)
        except OSError:
            pass
        os.chdir(self._cwd)

    def test_symlink(self):
        if hasattr(os, 'symlink'):
            if os.path.exists(self.symlinked_dir):
                self.assertTrue(os.path.islink(self.symlinked_dir))
            else:
                os.symlink(os.path.join(self.test_dir, 'templates'), self.symlinked_dir)
            os.chdir(self.test_dir)
            management.call_command('makemessages', locale=LOCALE, verbosity=0, symlinks=True)
            self.assertTrue(os.path.exists(self.PO_FILE))
            po_contents = open(self.PO_FILE, 'r').read()
            self.assertMsgId('This literal should be included.', po_contents)
            self.assertTrue('templates_symlinked/test.html' in po_contents)


class CopyPluralFormsExtractorTests(ExtractorTests):

    def test_copy_plural_forms(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        self.assertTrue('Plural-Forms: nplurals=2; plural=(n != 1)' in po_contents)


class NoWrapExtractorTests(ExtractorTests):

    def test_no_wrap_enabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0, no_wrap=True)
        self.assertTrue(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        self.assertMsgId('This literal should also be included wrapped or not wrapped depending on the use of the --no-wrap option.', po_contents)

    def test_no_wrap_disabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0, no_wrap=False)
        self.assertTrue(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        self.assertMsgId('""\n"This literal should also be included wrapped or not wrapped depending on the "\n"use of the --no-wrap option."', po_contents, use_quotes=False)


class NoLocationExtractorTests(ExtractorTests):

    def test_no_location_enabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0, no_location=True)
        self.assertTrue(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        self.assertFalse('#: templates/test.html:55' in po_contents)

    def test_no_location_disabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0, no_location=False)
        self.assertTrue(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        self.assertTrue('#: templates/test.html:55' in po_contents)
