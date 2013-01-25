# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import os
import re
import shutil

from django.conf import settings
from django.core import management
from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.utils.encoding import force_text
from django.utils._os import upath
from django.utils import six
from django.utils.six import StringIO


LOCALE='de'

class ExtractorTests(SimpleTestCase):

    PO_FILE='locale/%s/LC_MESSAGES/django.po' % LOCALE

    def setUp(self):
        self._cwd = os.getcwd()
        self.test_dir = os.path.abspath(os.path.dirname(upath(__file__)))

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
        q = '"'
        if use_quotes:
            msgid = '"%s"' % msgid
            q = "'"
        needle = 'msgid %s' % msgid
        msgid = re.escape(msgid)
        return self.assertTrue(re.search('^msgid %s' % msgid, s, re.MULTILINE), 'Could not find %(q)s%(n)s%(q)s in generated PO file' % {'n':needle, 'q':q})

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
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
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

    def test_templatize_trans_tag(self):
        # ticket #11240
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('Literal with a percent symbol at the end %%', po_contents)
            self.assertMsgId('Literal with a percent %% symbol in the middle', po_contents)
            self.assertMsgId('Completed 50%% of all the tasks', po_contents)
            self.assertMsgId('Completed 99%% of all the tasks', po_contents)
            self.assertMsgId("Shouldn't double escape this sequence: %% (two percent signs)", po_contents)
            self.assertMsgId("Shouldn't double escape this sequence %% either", po_contents)
            self.assertMsgId("Looks like a str fmt spec %%s but shouldn't be interpreted as such", po_contents)
            self.assertMsgId("Looks like a str fmt spec %% o but shouldn't be interpreted as such", po_contents)

    def test_templatize_blocktrans_tag(self):
        # ticket #11966
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('I think that 100%% is more that 50%% of anything.', po_contents)
            self.assertMsgId('I think that 100%% is more that 50%% of %(obj)s.', po_contents)
            self.assertMsgId("Blocktrans extraction shouldn't double escape this: %%, a=%(a)s", po_contents)

    def test_extraction_error(self):
        os.chdir(self.test_dir)
        self.assertRaises(SyntaxError, management.call_command, 'makemessages', locale=LOCALE, extensions=['tpl'], verbosity=0)
        with self.assertRaises(SyntaxError) as context_manager:
            management.call_command('makemessages', locale=LOCALE, extensions=['tpl'], verbosity=0)
        self.assertRegexpMatches(str(context_manager.exception),
                r'Translation blocks must not include other block tags: blocktrans \(file templates[/\\]template_with_error\.tpl, line 3\)'
            )
        # Check that the temporary file was cleaned up
        self.assertFalse(os.path.exists('./templates/template_with_error.tpl.py'))

    def test_extraction_warning(self):
        os.chdir(self.test_dir)
        shutil.copyfile('./code.sample', './code_sample.py')
        stdout = StringIO()
        management.call_command('makemessages', locale=LOCALE, stdout=stdout)
        os.remove('./code_sample.py')
        self.assertIn("code_sample.py:4", force_text(stdout.getvalue()))

    def test_template_message_context_extractor(self):
        """
        Ensure that message contexts are correctly extracted for the
        {% trans %} and {% blocktrans %} template tags.
        Refs #14806.
        """
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            # {% trans %}
            self.assertTrue('msgctxt "Special trans context #1"' in po_contents)
            self.assertMsgId("Translatable literal #7a", po_contents)
            self.assertTrue('msgctxt "Special trans context #2"' in po_contents)
            self.assertMsgId("Translatable literal #7b", po_contents)
            self.assertTrue('msgctxt "Special trans context #3"' in po_contents)
            self.assertMsgId("Translatable literal #7c", po_contents)

            # {% blocktrans %}
            self.assertTrue('msgctxt "Special blocktrans context #1"' in po_contents)
            self.assertMsgId("Translatable literal #8a", po_contents)
            self.assertTrue('msgctxt "Special blocktrans context #2"' in po_contents)
            self.assertMsgId("Translatable literal #8b-singular", po_contents)
            self.assertTrue("Translatable literal #8b-plural" in po_contents)
            self.assertTrue('msgctxt "Special blocktrans context #3"' in po_contents)
            self.assertMsgId("Translatable literal #8c-singular", po_contents)
            self.assertTrue("Translatable literal #8c-plural" in po_contents)
            self.assertTrue('msgctxt "Special blocktrans context #4"' in po_contents)
            self.assertMsgId("Translatable literal #8d %(a)s", po_contents)

    def test_context_in_single_quotes(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            # {% trans %}
            self.assertTrue('msgctxt "Context wrapped in double quotes"' in po_contents)
            self.assertTrue('msgctxt "Context wrapped in single quotes"' in po_contents)

            # {% blocktrans %}
            self.assertTrue('msgctxt "Special blocktrans context wrapped in double quotes"' in po_contents)
            self.assertTrue('msgctxt "Special blocktrans context wrapped in single quotes"' in po_contents)


class JavascriptExtractorTests(ExtractorTests):

    PO_FILE='locale/%s/LC_MESSAGES/djangojs.po' % LOCALE

    def test_javascript_literals(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', domain='djangojs', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = fp.read()
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
        stdout = StringIO()
        management.call_command('makemessages', locale=LOCALE, verbosity=2,
            ignore_patterns=[pattern1], stdout=stdout)
        data = stdout.getvalue()
        self.assertTrue("ignoring directory ignore_dir" in data)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = fp.read()
            self.assertMsgId('This literal should be included.', po_contents)
            self.assertNotMsgId('This should be ignored.', po_contents)


class SymlinkExtractorTests(ExtractorTests):

    def setUp(self):
        self._cwd = os.getcwd()
        self.test_dir = os.path.abspath(os.path.dirname(upath(__file__)))
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
            with open(self.PO_FILE, 'r') as fp:
                po_contents = force_text(fp.read())
                self.assertMsgId('This literal should be included.', po_contents)
                self.assertTrue('templates_symlinked/test.html' in po_contents)


class CopyPluralFormsExtractorTests(ExtractorTests):

    def test_copy_plural_forms(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertTrue('Plural-Forms: nplurals=2; plural=(n != 1)' in po_contents)


class NoWrapExtractorTests(ExtractorTests):

    def test_no_wrap_enabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0, no_wrap=True)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('This literal should also be included wrapped or not wrapped depending on the use of the --no-wrap option.', po_contents)

    def test_no_wrap_disabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0, no_wrap=False)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('""\n"This literal should also be included wrapped or not wrapped depending on the "\n"use of the --no-wrap option."', po_contents, use_quotes=False)


class NoLocationExtractorTests(ExtractorTests):

    def test_no_location_enabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0, no_location=True)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertFalse('#: templates/test.html:55' in po_contents)

    def test_no_location_disabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0, no_location=False)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertTrue('#: templates/test.html:55' in po_contents)


class KeepPotFileExtractorTests(ExtractorTests):

    POT_FILE='locale/django.pot'

    def setUp(self):
        super(KeepPotFileExtractorTests, self).setUp()

    def tearDown(self):
        super(KeepPotFileExtractorTests, self).tearDown()
        os.chdir(self.test_dir)
        try:
            os.unlink(self.POT_FILE)
        except OSError:
            pass
        os.chdir(self._cwd)

    def test_keep_pot_disabled_by_default(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        self.assertFalse(os.path.exists(self.POT_FILE))

    def test_keep_pot_explicitly_disabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0,
                                keep_pot=False)
        self.assertFalse(os.path.exists(self.POT_FILE))

    def test_keep_pot_enabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=LOCALE, verbosity=0,
                                keep_pot=True)
        self.assertTrue(os.path.exists(self.POT_FILE))


class MultipleLocaleExtractionTests(ExtractorTests):
    PO_FILE_PT = 'locale/pt/LC_MESSAGES/django.po'
    PO_FILE_DE = 'locale/de/LC_MESSAGES/django.po'
    LOCALES = ['pt', 'de', 'ch']

    def tearDown(self):
        os.chdir(self.test_dir)
        for locale in self.LOCALES:
            try:
                self._rmrf('locale/%s' % locale)
            except OSError:
                pass
        os.chdir(self._cwd)

    def test_multiple_locales(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=['pt','de'], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE_PT))
        self.assertTrue(os.path.exists(self.PO_FILE_DE))

    def test_comma_separated_locales(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale='pt,de,ch', verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE_PT))
        self.assertTrue(os.path.exists(self.PO_FILE_DE))


class CustomLayoutExtractionTests(ExtractorTests):
    def setUp(self):
        self._cwd = os.getcwd()
        self.test_dir = os.path.join(os.path.dirname(upath(__file__)), 'project_dir')

    def test_no_locale_raises(self):
        os.chdir(self.test_dir)
        with six.assertRaisesRegex(self, management.CommandError,
                "Unable to find a locale path to store translations for file"):
            management.call_command('makemessages', locale=LOCALE, verbosity=0)

    @override_settings(
        LOCALE_PATHS=(os.path.join(os.path.dirname(upath(__file__)), 'project_dir/project_locale'),)
    )
    def test_project_locale_paths(self):
        """
        Test that:
          * translations for app containing locale folder are stored in that folder
          * translations outside of that app are in LOCALE_PATHS[0]
        """
        os.chdir(self.test_dir)
        self.addCleanup(shutil.rmtree, os.path.join(settings.LOCALE_PATHS[0], LOCALE))
        self.addCleanup(shutil.rmtree, os.path.join(self.test_dir, 'app_with_locale/locale', LOCALE))

        management.call_command('makemessages', locale=LOCALE, verbosity=0)
        project_de_locale = os.path.join(
            self.test_dir, 'project_locale/de/LC_MESSAGES/django.po',)
        app_de_locale = os.path.join(
            self.test_dir, 'app_with_locale/locale/de/LC_MESSAGES/django.po',)
        self.assertTrue(os.path.exists(project_de_locale))
        self.assertTrue(os.path.exists(app_de_locale))

        with open(project_de_locale, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('This app has no locale directory', po_contents)
            self.assertMsgId('This is a project-level string', po_contents)
        with open(app_de_locale, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('This app has a locale directory', po_contents)
