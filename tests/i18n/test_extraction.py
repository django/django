# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import io
import os
import re
import shutil
import time
import warnings
from unittest import SkipTest, skipUnless

from django.conf import settings
from django.core import management
from django.core.management import execute_from_command_line
from django.core.management.base import CommandError
from django.core.management.commands.makemessages import \
    Command as MakeMessagesCommand
from django.core.management.utils import find_command
from django.test import SimpleTestCase, mock, override_settings
from django.test.testcases import SerializeMixin
from django.test.utils import captured_stderr, captured_stdout
from django.utils import six
from django.utils._os import upath
from django.utils.encoding import force_text
from django.utils.six import StringIO
from django.utils.translation import TranslatorCommentWarning

LOCALE = 'de'
has_xgettext = find_command('xgettext')
this_directory = os.path.dirname(upath(__file__))


@skipUnless(has_xgettext, 'xgettext is mandatory for extraction tests')
class ExtractorTests(SerializeMixin, SimpleTestCase):

    # makemessages scans the current working directory and writes in the
    # locale subdirectory. There aren't any options to control this. As a
    # consequence tests can't run in parallel. Since i18n tests run in less
    # than 4 seconds, serializing them with SerializeMixin is acceptable.
    lockfile = __file__

    test_dir = os.path.abspath(os.path.join(this_directory, 'commands'))

    PO_FILE = 'locale/%s/LC_MESSAGES/django.po' % LOCALE

    def setUp(self):
        self._cwd = os.getcwd()

    def _rmrf(self, dname):
        if os.path.commonprefix([self.test_dir, os.path.abspath(dname)]) != self.test_dir:
            return
        shutil.rmtree(dname)

    def rmfile(self, filepath):
        if os.path.exists(filepath):
            os.remove(filepath)

    def tearDown(self):
        os.chdir(self.test_dir)
        try:
            self._rmrf('locale/%s' % LOCALE)
        except OSError:
            pass
        os.chdir(self._cwd)

    def _run_makemessages(self, **options):
        os.chdir(self.test_dir)
        out = StringIO()
        management.call_command('makemessages', locale=[LOCALE], verbosity=2,
            stdout=out, **options)
        output = out.getvalue()
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = fp.read()
        return output, po_contents

    def _assertPoKeyword(self, keyword, expected_value, haystack, use_quotes=True):
        q = '"'
        if use_quotes:
            expected_value = '"%s"' % expected_value
            q = "'"
        needle = '%s %s' % (keyword, expected_value)
        expected_value = re.escape(expected_value)
        return self.assertTrue(re.search('^%s %s' % (keyword, expected_value), haystack, re.MULTILINE),
                               'Could not find %(q)s%(n)s%(q)s in generated PO file' % {'n': needle, 'q': q})

    def assertMsgId(self, msgid, haystack, use_quotes=True):
        return self._assertPoKeyword('msgid', msgid, haystack, use_quotes=use_quotes)

    def assertMsgIdPlural(self, msgid, haystack, use_quotes=True):
        return self._assertPoKeyword('msgid_plural', msgid, haystack, use_quotes=use_quotes)

    def assertMsgStr(self, msgstr, haystack, use_quotes=True):
        return self._assertPoKeyword('msgstr', msgstr, haystack, use_quotes=use_quotes)

    def assertNotMsgId(self, msgid, s, use_quotes=True):
        if use_quotes:
            msgid = '"%s"' % msgid
        msgid = re.escape(msgid)
        return self.assertTrue(not re.search('^msgid %s' % msgid, s, re.MULTILINE))

    def _assertPoLocComment(self, assert_presence, po_filename, line_number, *comment_parts):
        with open(po_filename, 'r') as fp:
            po_contents = force_text(fp.read())
        if os.name == 'nt':
            # #: .\path\to\file.html:123
            cwd_prefix = '%s%s' % (os.curdir, os.sep)
        else:
            # #: path/to/file.html:123
            cwd_prefix = ''
        parts = ['#: ']

        path = os.path.join(cwd_prefix, *comment_parts)
        parts.append(path)

        if isinstance(line_number, six.string_types):
            line_number = self._get_token_line_number(path, line_number)
        if line_number is not None:
            parts.append(':%d' % line_number)

        needle = ''.join(parts)
        if assert_presence:
            return self.assertIn(needle, po_contents, '"%s" not found in final .po file.' % needle)
        else:
            return self.assertNotIn(needle, po_contents, '"%s" shouldn\'t be in final .po file.' % needle)

    def _get_token_line_number(self, path, token):
        with open(path) as f:
            for line, content in enumerate(f, 1):
                if token in force_text(content):
                    return line
        self.fail("The token '%s' could not be found in %s, please check the test config" % (token, path))

    def assertLocationCommentPresent(self, po_filename, line_number, *comment_parts):
        """
        self.assertLocationCommentPresent('django.po', 42, 'dirA', 'dirB', 'foo.py')

        verifies that the django.po file has a gettext-style location comment of the form

        `#: dirA/dirB/foo.py:42`

        (or `#: .\dirA\dirB\foo.py:42` on Windows)

        None can be passed for the line_number argument to skip checking of
        the :42 suffix part.
        A string token can also be passed as line_number, in which case it
        will be searched in the template, and its line number will be used.
        A msgid is a suitable candidate.
        """
        return self._assertPoLocComment(True, po_filename, line_number, *comment_parts)

    def assertLocationCommentNotPresent(self, po_filename, line_number, *comment_parts):
        """Check the opposite of assertLocationComment()"""
        return self._assertPoLocComment(False, po_filename, line_number, *comment_parts)

    def assertRecentlyModified(self, path):
        """
        Assert that file was recently modified (modification time was less than 10 seconds ago).
        """
        delta = time.time() - os.stat(path).st_mtime
        self.assertLess(delta, 10, "%s was recently modified" % path)

    def assertNotRecentlyModified(self, path):
        """
        Assert that file was not recently modified (modification time was more than 10 seconds ago).
        """
        delta = time.time() - os.stat(path).st_mtime
        self.assertGreater(delta, 10, "%s wasn't recently modified" % path)


class BasicExtractorTests(ExtractorTests):

    def test_comments_extractor(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with io.open(self.PO_FILE, 'r', encoding='utf-8') as fp:
            po_contents = fp.read()
            self.assertNotIn('This comment should not be extracted', po_contents)

            # Comments in templates
            self.assertIn('#. Translators: This comment should be extracted', po_contents)
            self.assertIn(
                "#. Translators: Django comment block for translators\n#. "
                "string's meaning unveiled",
                po_contents
            )
            self.assertIn('#. Translators: One-line translator comment #1', po_contents)
            self.assertIn('#. Translators: Two-line translator comment #1\n#. continued here.', po_contents)
            self.assertIn('#. Translators: One-line translator comment #2', po_contents)
            self.assertIn('#. Translators: Two-line translator comment #2\n#. continued here.', po_contents)
            self.assertIn('#. Translators: One-line translator comment #3', po_contents)
            self.assertIn('#. Translators: Two-line translator comment #3\n#. continued here.', po_contents)
            self.assertIn('#. Translators: One-line translator comment #4', po_contents)
            self.assertIn('#. Translators: Two-line translator comment #4\n#. continued here.', po_contents)
            self.assertIn(
                '#. Translators: One-line translator comment #5 -- with '
                'non ASCII characters: áéíóúö',
                po_contents
            )
            self.assertIn(
                '#. Translators: Two-line translator comment #5 -- with '
                'non ASCII characters: áéíóúö\n#. continued here.',
                po_contents
            )

    def test_blocktrans_trimmed(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            # should not be trimmed
            self.assertNotMsgId('Text with a few line breaks.', po_contents)
            # should be trimmed
            self.assertMsgId("Again some text with a few line breaks, this time should be trimmed.", po_contents)
        # #21406 -- Should adjust for eaten line numbers
        self.assertMsgId("Get my line number", po_contents)
        self.assertLocationCommentPresent(self.PO_FILE, 'Get my line number', 'templates', 'test.html')

    def test_force_en_us_locale(self):
        """Value of locale-munging option used by the command is the right one"""
        self.assertTrue(MakeMessagesCommand.leave_locale_alone)

    def test_extraction_error(self):
        os.chdir(self.test_dir)
        msg = (
            'Translation blocks must not include other block tags: blocktrans '
            '(file %s, line 3)' % os.path.join('templates', 'template_with_error.tpl')
        )
        with self.assertRaisesMessage(SyntaxError, msg):
            management.call_command('makemessages', locale=[LOCALE], extensions=['tpl'], verbosity=0)
        # Check that the temporary file was cleaned up
        self.assertFalse(os.path.exists('./templates/template_with_error.tpl.py'))

    def test_unicode_decode_error(self):
        os.chdir(self.test_dir)
        shutil.copyfile('./not_utf8.sample', './not_utf8.txt')
        self.addCleanup(self.rmfile, os.path.join(self.test_dir, 'not_utf8.txt'))
        out = StringIO()
        management.call_command('makemessages', locale=[LOCALE], stdout=out)
        self.assertIn("UnicodeDecodeError: skipped file not_utf8.txt in .",
                      force_text(out.getvalue()))

    def test_extraction_warning(self):
        """test xgettext warning about multiple bare interpolation placeholders"""
        os.chdir(self.test_dir)
        shutil.copyfile('./code.sample', './code_sample.py')
        self.addCleanup(self.rmfile, os.path.join(self.test_dir, 'code_sample.py'))
        out = StringIO()
        management.call_command('makemessages', locale=[LOCALE], stdout=out)
        self.assertIn("code_sample.py:4", force_text(out.getvalue()))

    def test_template_message_context_extractor(self):
        """
        Ensure that message contexts are correctly extracted for the
        {% trans %} and {% blocktrans %} template tags.
        Refs #14806.
        """
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            # {% trans %}
            self.assertIn('msgctxt "Special trans context #1"', po_contents)
            self.assertMsgId("Translatable literal #7a", po_contents)
            self.assertIn('msgctxt "Special trans context #2"', po_contents)
            self.assertMsgId("Translatable literal #7b", po_contents)
            self.assertIn('msgctxt "Special trans context #3"', po_contents)
            self.assertMsgId("Translatable literal #7c", po_contents)

            # {% trans %} with a filter
            for minor_part in 'abcdefgh':  # Iterate from #7.1a to #7.1h template markers
                self.assertIn('msgctxt "context #7.1{}"'.format(minor_part), po_contents)
                self.assertMsgId('Translatable literal #7.1{}'.format(minor_part), po_contents)

            # {% blocktrans %}
            self.assertIn('msgctxt "Special blocktrans context #1"', po_contents)
            self.assertMsgId("Translatable literal #8a", po_contents)
            self.assertIn('msgctxt "Special blocktrans context #2"', po_contents)
            self.assertMsgId("Translatable literal #8b-singular", po_contents)
            self.assertIn("Translatable literal #8b-plural", po_contents)
            self.assertIn('msgctxt "Special blocktrans context #3"', po_contents)
            self.assertMsgId("Translatable literal #8c-singular", po_contents)
            self.assertIn("Translatable literal #8c-plural", po_contents)
            self.assertIn('msgctxt "Special blocktrans context #4"', po_contents)
            self.assertMsgId("Translatable literal #8d %(a)s", po_contents)

    def test_context_in_single_quotes(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            # {% trans %}
            self.assertIn('msgctxt "Context wrapped in double quotes"', po_contents)
            self.assertIn('msgctxt "Context wrapped in single quotes"', po_contents)

            # {% blocktrans %}
            self.assertIn('msgctxt "Special blocktrans context wrapped in double quotes"', po_contents)
            self.assertIn('msgctxt "Special blocktrans context wrapped in single quotes"', po_contents)

    def test_template_comments(self):
        """Template comment tags on the same line of other constructs (#19552)"""
        os.chdir(self.test_dir)
        # Test detection/end user reporting of old, incorrect templates
        # translator comments syntax
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always')
            management.call_command('makemessages', locale=[LOCALE], extensions=['thtml'], verbosity=0)
            self.assertEqual(len(ws), 3)
            for w in ws:
                self.assertTrue(issubclass(w.category, TranslatorCommentWarning))
            six.assertRegex(
                self, str(ws[0].message),
                r"The translator-targeted comment 'Translators: ignored i18n "
                r"comment #1' \(file templates[/\\]comments.thtml, line 4\) "
                r"was ignored, because it wasn't the last item on the line\."
            )
            six.assertRegex(
                self, str(ws[1].message),
                r"The translator-targeted comment 'Translators: ignored i18n "
                r"comment #3' \(file templates[/\\]comments.thtml, line 6\) "
                r"was ignored, because it wasn't the last item on the line\."
            )
            six.assertRegex(
                self, str(ws[2].message),
                r"The translator-targeted comment 'Translators: ignored i18n "
                r"comment #4' \(file templates[/\\]comments.thtml, line 8\) "
                "was ignored, because it wasn't the last item on the line\."
            )
        # Now test .po file contents
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())

            self.assertMsgId('Translatable literal #9a', po_contents)
            self.assertNotIn('ignored comment #1', po_contents)

            self.assertNotIn('Translators: ignored i18n comment #1', po_contents)
            self.assertMsgId("Translatable literal #9b", po_contents)

            self.assertNotIn('ignored i18n comment #2', po_contents)
            self.assertNotIn('ignored comment #2', po_contents)
            self.assertMsgId('Translatable literal #9c', po_contents)

            self.assertNotIn('ignored comment #3', po_contents)
            self.assertNotIn('ignored i18n comment #3', po_contents)
            self.assertMsgId('Translatable literal #9d', po_contents)

            self.assertNotIn('ignored comment #4', po_contents)
            self.assertMsgId('Translatable literal #9e', po_contents)
            self.assertNotIn('ignored comment #5', po_contents)

            self.assertNotIn('ignored i18n comment #4', po_contents)
            self.assertMsgId('Translatable literal #9f', po_contents)
            self.assertIn('#. Translators: valid i18n comment #5', po_contents)

            self.assertMsgId('Translatable literal #9g', po_contents)
            self.assertIn('#. Translators: valid i18n comment #6', po_contents)
            self.assertMsgId('Translatable literal #9h', po_contents)
            self.assertIn('#. Translators: valid i18n comment #7', po_contents)
            self.assertMsgId('Translatable literal #9i', po_contents)

            six.assertRegex(self, po_contents, r'#\..+Translators: valid i18n comment #8')
            six.assertRegex(self, po_contents, r'#\..+Translators: valid i18n comment #9')
            self.assertMsgId("Translatable literal #9j", po_contents)

    def test_makemessages_find_files(self):
        """
        Test that find_files only discover files having the proper extensions.
        """
        cmd = MakeMessagesCommand()
        cmd.ignore_patterns = ['CVS', '.*', '*~', '*.pyc']
        cmd.symlinks = False
        cmd.domain = 'django'
        cmd.extensions = ['html', 'txt', 'py']
        cmd.verbosity = 0
        cmd.locale_paths = []
        cmd.default_locale_path = os.path.join(self.test_dir, 'locale')
        found_files = cmd.find_files(self.test_dir)
        found_exts = set([os.path.splitext(tfile.file)[1] for tfile in found_files])
        self.assertEqual(found_exts.difference({'.py', '.html', '.txt'}), set())

        cmd.extensions = ['js']
        cmd.domain = 'djangojs'
        found_files = cmd.find_files(self.test_dir)
        found_exts = set([os.path.splitext(tfile.file)[1] for tfile in found_files])
        self.assertEqual(found_exts.difference({'.js'}), set())

    @mock.patch('django.core.management.commands.makemessages.popen_wrapper')
    def test_makemessages_gettext_version(self, mocked_popen_wrapper):
        # "Normal" output:
        mocked_popen_wrapper.return_value = (
            "xgettext (GNU gettext-tools) 0.18.1\n"
            "Copyright (C) 1995-1998, 2000-2010 Free Software Foundation, Inc.\n"
            "License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>\n"
            "This is free software: you are free to change and redistribute it.\n"
            "There is NO WARRANTY, to the extent permitted by law.\n"
            "Written by Ulrich Drepper.\n", '', 0)
        cmd = MakeMessagesCommand()
        self.assertEqual(cmd.gettext_version, (0, 18, 1))

        # Version number with only 2 parts (#23788)
        mocked_popen_wrapper.return_value = (
            "xgettext (GNU gettext-tools) 0.17\n", '', 0)
        cmd = MakeMessagesCommand()
        self.assertEqual(cmd.gettext_version, (0, 17))

        # Bad version output
        mocked_popen_wrapper.return_value = (
            "any other return value\n", '', 0)
        cmd = MakeMessagesCommand()
        with six.assertRaisesRegex(self, CommandError, "Unable to get gettext version. Is it installed?"):
            cmd.gettext_version

    def test_po_file_encoding_when_updating(self):
        """Update of PO file doesn't corrupt it with non-UTF-8 encoding on Python3+Windows (#23271)"""
        BR_PO_BASE = 'locale/pt_BR/LC_MESSAGES/django'
        os.chdir(self.test_dir)
        shutil.copyfile(BR_PO_BASE + '.pristine', BR_PO_BASE + '.po')
        self.addCleanup(self.rmfile, os.path.join(self.test_dir, 'locale', 'pt_BR', 'LC_MESSAGES', 'django.po'))
        management.call_command('makemessages', locale=['pt_BR'], verbosity=0)
        self.assertTrue(os.path.exists(BR_PO_BASE + '.po'))
        with io.open(BR_PO_BASE + '.po', 'r', encoding='utf-8') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgStr("Größe", po_contents)


class JavascriptExtractorTests(ExtractorTests):

    PO_FILE = 'locale/%s/LC_MESSAGES/djangojs.po' % LOCALE

    def test_javascript_literals(self):
        os.chdir(self.test_dir)
        _, po_contents = self._run_makemessages(domain='djangojs')
        self.assertMsgId('This literal should be included.', po_contents)
        self.assertMsgId('gettext_noop should, too.', po_contents)
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

    @override_settings(
        STATIC_ROOT=os.path.join(this_directory, 'commands', 'static/'),
        MEDIA_ROOT=os.path.join(this_directory, 'commands', 'media_root/'))
    def test_media_static_dirs_ignored(self):
        """
        Regression test for #23583.
        """
        _, po_contents = self._run_makemessages(domain='djangojs')
        self.assertMsgId("Static content inside app should be included.", po_contents)
        self.assertNotMsgId("Content from STATIC_ROOT should not be included", po_contents)

    @override_settings(STATIC_ROOT=None, MEDIA_ROOT='')
    def test_default_root_settings(self):
        """
        Regression test for #23717.
        """
        _, po_contents = self._run_makemessages(domain='djangojs')
        self.assertMsgId("Static content inside app should be included.", po_contents)


class IgnoredExtractorTests(ExtractorTests):

    def test_ignore_directory(self):
        out, po_contents = self._run_makemessages(ignore_patterns=[
            os.path.join('ignore_dir', '*'),
        ])
        self.assertIn("ignoring directory ignore_dir", out)
        self.assertMsgId('This literal should be included.', po_contents)
        self.assertNotMsgId('This should be ignored.', po_contents)

    def test_ignore_subdirectory(self):
        out, po_contents = self._run_makemessages(ignore_patterns=[
            'templates/*/ignore.html',
            'templates/subdir/*',
        ])
        self.assertIn("ignoring directory subdir", out)
        self.assertNotMsgId('This subdir should be ignored too.', po_contents)

    def test_ignore_file_patterns(self):
        out, po_contents = self._run_makemessages(ignore_patterns=[
            'xxx_*',
        ])
        self.assertIn("ignoring file xxx_ignored.html", out)
        self.assertNotMsgId('This should be ignored too.', po_contents)

    @override_settings(
        STATIC_ROOT=os.path.join(this_directory, 'commands', 'static/'),
        MEDIA_ROOT=os.path.join(this_directory, 'commands', 'media_root/'))
    def test_media_static_dirs_ignored(self):
        out, _ = self._run_makemessages()
        self.assertIn("ignoring directory static", out)
        self.assertIn("ignoring directory media_root", out)


class SymlinkExtractorTests(ExtractorTests):

    def setUp(self):
        super(SymlinkExtractorTests, self).setUp()
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
        # On Python < 3.2 os.symlink() exists only on Unix
        if hasattr(os, 'symlink'):
            if os.path.exists(self.symlinked_dir):
                self.assertTrue(os.path.islink(self.symlinked_dir))
            else:
                # On Python >= 3.2) os.symlink() exists always but then can
                # fail at runtime when user hasn't the needed permissions on
                # Windows versions that support symbolink links (>= 6/Vista).
                # See Python issue 9333 (http://bugs.python.org/issue9333).
                # Skip the test in that case
                try:
                    os.symlink(os.path.join(self.test_dir, 'templates'), self.symlinked_dir)
                except (OSError, NotImplementedError):
                    raise SkipTest("os.symlink() is available on this OS but can't be used by this user.")
            os.chdir(self.test_dir)
            management.call_command('makemessages', locale=[LOCALE], verbosity=0, symlinks=True)
            self.assertTrue(os.path.exists(self.PO_FILE))
            with open(self.PO_FILE, 'r') as fp:
                po_contents = force_text(fp.read())
                self.assertMsgId('This literal should be included.', po_contents)
                self.assertIn('templates_symlinked/test.html', po_contents)


class CopyPluralFormsExtractorTests(ExtractorTests):

    PO_FILE_ES = 'locale/es/LC_MESSAGES/django.po'

    def tearDown(self):
        super(CopyPluralFormsExtractorTests, self).tearDown()
        os.chdir(self.test_dir)
        try:
            self._rmrf('locale/es')
        except OSError:
            pass
        os.chdir(self._cwd)

    def test_copy_plural_forms(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertIn('Plural-Forms: nplurals=2; plural=(n != 1)', po_contents)

    def test_override_plural_forms(self):
        """Ticket #20311."""
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=['es'], extensions=['djtpl'], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE_ES))
        with io.open(self.PO_FILE_ES, 'r', encoding='utf-8') as fp:
            po_contents = fp.read()
            found = re.findall(r'^(?P<value>"Plural-Forms.+?\\n")\s*$', po_contents, re.MULTILINE | re.DOTALL)
            self.assertEqual(1, len(found))

    def test_trans_and_plural_blocktrans_collision(self):
        """
        Ensures a correct workaround for the gettext bug when handling a literal
        found inside a {% trans %} tag and also in another file inside a
        {% blocktrans %} with a plural (#17375).
        """
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], extensions=['html', 'djtpl'], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertNotIn("#-#-#-#-#  django.pot (PACKAGE VERSION)  #-#-#-#-#\\n", po_contents)
            self.assertMsgId('First `trans`, then `blocktrans` with a plural', po_contents)
            self.assertMsgIdPlural('Plural for a `trans` and `blocktrans` collision case', po_contents)


class NoWrapExtractorTests(ExtractorTests):

    def test_no_wrap_enabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0, no_wrap=True)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId(
                'This literal should also be included wrapped or not wrapped '
                'depending on the use of the --no-wrap option.',
                po_contents
            )

    def test_no_wrap_disabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0, no_wrap=False)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId(
                '""\n"This literal should also be included wrapped or not '
                'wrapped depending on the "\n"use of the --no-wrap option."',
                po_contents,
                use_quotes=False
            )


class LocationCommentsTests(ExtractorTests):

    def test_no_location_enabled(self):
        """Behavior is correct if --no-location switch is specified. See #16903."""
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0, no_location=True)
        self.assertTrue(os.path.exists(self.PO_FILE))
        self.assertLocationCommentNotPresent(self.PO_FILE, 55, 'templates', 'test.html.py')

    def test_no_location_disabled(self):
        """Behavior is correct if --no-location switch isn't specified."""
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0, no_location=False)
        self.assertTrue(os.path.exists(self.PO_FILE))
        # #16903 -- Standard comment with source file relative path should be present
        self.assertLocationCommentPresent(self.PO_FILE, 'Translatable literal #6b', 'templates', 'test.html')

        # #21208 -- Leaky paths in comments on Windows e.g. #: path\to\file.html.py:123
        self.assertLocationCommentNotPresent(self.PO_FILE, None, 'templates', 'test.html.py')


class KeepPotFileExtractorTests(ExtractorTests):

    POT_FILE = 'locale/django.pot'

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
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertFalse(os.path.exists(self.POT_FILE))

    def test_keep_pot_explicitly_disabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0,
                                keep_pot=False)
        self.assertFalse(os.path.exists(self.POT_FILE))

    def test_keep_pot_enabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0,
                                keep_pot=True)
        self.assertTrue(os.path.exists(self.POT_FILE))


class MultipleLocaleExtractionTests(ExtractorTests):
    PO_FILE_PT = 'locale/pt/LC_MESSAGES/django.po'
    PO_FILE_DE = 'locale/de/LC_MESSAGES/django.po'
    LOCALES = ['pt', 'de', 'ch']

    def tearDown(self):
        super(MultipleLocaleExtractionTests, self).tearDown()
        os.chdir(self.test_dir)
        for locale in self.LOCALES:
            try:
                self._rmrf('locale/%s' % locale)
            except OSError:
                pass
        os.chdir(self._cwd)

    def test_multiple_locales(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=['pt', 'de'], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE_PT))
        self.assertTrue(os.path.exists(self.PO_FILE_DE))


class ExcludedLocaleExtractionTests(ExtractorTests):

    LOCALES = ['en', 'fr', 'it']
    PO_FILE = 'locale/%s/LC_MESSAGES/django.po'

    test_dir = os.path.abspath(os.path.join(this_directory, 'exclude'))

    def _set_times_for_all_po_files(self):
        """
        Set access and modification times to the Unix epoch time for all the .po files.
        """
        for locale in self.LOCALES:
            os.utime(self.PO_FILE % locale, (0, 0))

    def setUp(self):
        super(ExcludedLocaleExtractionTests, self).setUp()
        os.chdir(self.test_dir)  # ExtractorTests.tearDown() takes care of restoring.
        shutil.copytree('canned_locale', 'locale')
        self._set_times_for_all_po_files()
        self.addCleanup(self._rmrf, os.path.join(self.test_dir, 'locale'))

    def test_command_help(self):
        with captured_stdout(), captured_stderr():
            # `call_command` bypasses the parser; by calling
            # `execute_from_command_line` with the help subcommand we
            # ensure that there are no issues with the parser itself.
            execute_from_command_line(['django-admin', 'help', 'makemessages'])

    def test_one_locale_excluded(self):
        management.call_command('makemessages', exclude=['it'], stdout=StringIO())
        self.assertRecentlyModified(self.PO_FILE % 'en')
        self.assertRecentlyModified(self.PO_FILE % 'fr')
        self.assertNotRecentlyModified(self.PO_FILE % 'it')

    def test_multiple_locales_excluded(self):
        management.call_command('makemessages', exclude=['it', 'fr'], stdout=StringIO())
        self.assertRecentlyModified(self.PO_FILE % 'en')
        self.assertNotRecentlyModified(self.PO_FILE % 'fr')
        self.assertNotRecentlyModified(self.PO_FILE % 'it')

    def test_one_locale_excluded_with_locale(self):
        management.call_command('makemessages', locale=['en', 'fr'], exclude=['fr'], stdout=StringIO())
        self.assertRecentlyModified(self.PO_FILE % 'en')
        self.assertNotRecentlyModified(self.PO_FILE % 'fr')
        self.assertNotRecentlyModified(self.PO_FILE % 'it')

    def test_multiple_locales_excluded_with_locale(self):
        management.call_command('makemessages', locale=['en', 'fr', 'it'], exclude=['fr', 'it'],
                                stdout=StringIO())
        self.assertRecentlyModified(self.PO_FILE % 'en')
        self.assertNotRecentlyModified(self.PO_FILE % 'fr')
        self.assertNotRecentlyModified(self.PO_FILE % 'it')


class CustomLayoutExtractionTests(ExtractorTests):

    def setUp(self):
        super(CustomLayoutExtractionTests, self).setUp()
        self.test_dir = os.path.join(this_directory, 'project_dir')

    def test_no_locale_raises(self):
        os.chdir(self.test_dir)
        with six.assertRaisesRegex(self, management.CommandError,
                "Unable to find a locale path to store translations for file"):
            management.call_command('makemessages', locale=LOCALE, verbosity=0)

    @override_settings(
        LOCALE_PATHS=[os.path.join(this_directory, 'project_dir', 'project_locale')],
    )
    def test_project_locale_paths(self):
        """
        Test that:
          * translations for an app containing a locale folder are stored in that folder
          * translations outside of that app are in LOCALE_PATHS[0]
        """
        os.chdir(self.test_dir)
        self.addCleanup(shutil.rmtree,
            os.path.join(settings.LOCALE_PATHS[0], LOCALE), True)
        self.addCleanup(shutil.rmtree,
            os.path.join(self.test_dir, 'app_with_locale', 'locale', LOCALE), True)

        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        project_de_locale = os.path.join(
            self.test_dir, 'project_locale', 'de', 'LC_MESSAGES', 'django.po')
        app_de_locale = os.path.join(
            self.test_dir, 'app_with_locale', 'locale', 'de', 'LC_MESSAGES', 'django.po')
        self.assertTrue(os.path.exists(project_de_locale))
        self.assertTrue(os.path.exists(app_de_locale))

        with open(project_de_locale, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('This app has no locale directory', po_contents)
            self.assertMsgId('This is a project-level string', po_contents)
        with open(app_de_locale, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('This app has a locale directory', po_contents)
