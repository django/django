import os
import re
import shutil
import tempfile
import time
import warnings
from io import StringIO
from pathlib import Path
from unittest import mock, skipUnless

from admin_scripts.tests import AdminScriptTestCase

from django.core import management
from django.core.management import execute_from_command_line
from django.core.management.base import CommandError
from django.core.management.commands.makemessages import Command as MakeMessagesCommand
from django.core.management.commands.makemessages import write_pot_file
from django.core.management.utils import find_command
from django.test import SimpleTestCase, override_settings
from django.test.utils import captured_stderr, captured_stdout
from django.utils._os import symlinks_supported
from django.utils.translation import TranslatorCommentWarning

from .utils import POFileAssertionMixin, RunInTmpDirMixin, copytree

LOCALE = "de"
has_xgettext = find_command("xgettext")


@skipUnless(has_xgettext, "xgettext is mandatory for extraction tests")
class ExtractorTests(POFileAssertionMixin, RunInTmpDirMixin, SimpleTestCase):
    work_subdir = "commands"

    PO_FILE = "locale/%s/LC_MESSAGES/django.po" % LOCALE

    def _run_makemessages(self, **options):
        out = StringIO()
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=2, stdout=out, **options
        )
        output = out.getvalue()
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
        return output, po_contents

    def assertMsgIdPlural(self, msgid, haystack, use_quotes=True):
        return self._assertPoKeyword(
            "msgid_plural", msgid, haystack, use_quotes=use_quotes
        )

    def assertMsgStr(self, msgstr, haystack, use_quotes=True):
        return self._assertPoKeyword("msgstr", msgstr, haystack, use_quotes=use_quotes)

    def assertNotMsgId(self, msgid, s, use_quotes=True):
        if use_quotes:
            msgid = '"%s"' % msgid
        msgid = re.escape(msgid)
        return self.assertTrue(not re.search("^msgid %s" % msgid, s, re.MULTILINE))

    def _assertPoLocComment(
        self, assert_presence, po_filename, line_number, *comment_parts
    ):
        with open(po_filename) as fp:
            po_contents = fp.read()
        if os.name == "nt":
            # #: .\path\to\file.html:123
            cwd_prefix = "%s%s" % (os.curdir, os.sep)
        else:
            # #: path/to/file.html:123
            cwd_prefix = ""

        path = os.path.join(cwd_prefix, *comment_parts)
        parts = [path]

        if isinstance(line_number, str):
            line_number = self._get_token_line_number(path, line_number)
        if line_number is not None:
            parts.append(":%d" % line_number)

        needle = "".join(parts)
        pattern = re.compile(r"^\#\:.*" + re.escape(needle), re.MULTILINE)
        if assert_presence:
            return self.assertRegex(
                po_contents, pattern, '"%s" not found in final .po file.' % needle
            )
        else:
            return self.assertNotRegex(
                po_contents, pattern, '"%s" shouldn\'t be in final .po file.' % needle
            )

    def _get_token_line_number(self, path, token):
        with open(path) as f:
            for line, content in enumerate(f, 1):
                if token in content:
                    return line
        self.fail(
            "The token '%s' could not be found in %s, please check the test config"
            % (token, path)
        )

    def assertLocationCommentPresent(self, po_filename, line_number, *comment_parts):
        r"""
        self.assertLocationCommentPresent('django.po', 42, 'dirA', 'dirB', 'foo.py')

        verifies that the django.po file has a gettext-style location comment
        of the form

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
        Assert that file was recently modified (modification time was less than
        10 seconds ago).
        """
        delta = time.time() - os.stat(path).st_mtime
        self.assertLess(delta, 10, "%s was recently modified" % path)

    def assertNotRecentlyModified(self, path):
        """
        Assert that file was not recently modified (modification time was more
        than 10 seconds ago).
        """
        delta = time.time() - os.stat(path).st_mtime
        self.assertGreater(delta, 10, "%s wasn't recently modified" % path)


class BasicExtractorTests(ExtractorTests):
    @override_settings(USE_I18N=False)
    def test_use_i18n_false(self):
        """
        makemessages also runs successfully when USE_I18N is False.
        """
        management.call_command("makemessages", locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, encoding="utf-8") as fp:
            po_contents = fp.read()
            # Check two random strings
            self.assertIn("#. Translators: One-line translator comment #1", po_contents)
            self.assertIn('msgctxt "Special trans context #1"', po_contents)

    def test_no_option(self):
        # One of either the --locale, --exclude, or --all options is required.
        msg = "Type 'manage.py help makemessages' for usage information."
        with mock.patch(
            "django.core.management.commands.makemessages.sys.argv",
            ["manage.py", "makemessages"],
        ):
            with self.assertRaisesRegex(CommandError, msg):
                management.call_command("makemessages")

    def test_valid_locale(self):
        out = StringIO()
        management.call_command("makemessages", locale=["de"], stdout=out, verbosity=1)
        self.assertNotIn("invalid locale de", out.getvalue())
        self.assertIn("processing locale de", out.getvalue())
        self.assertIs(Path(self.PO_FILE).exists(), True)

    def test_valid_locale_with_country(self):
        out = StringIO()
        management.call_command(
            "makemessages", locale=["en_GB"], stdout=out, verbosity=1
        )
        self.assertNotIn("invalid locale en_GB", out.getvalue())
        self.assertIn("processing locale en_GB", out.getvalue())
        self.assertIs(Path("locale/en_GB/LC_MESSAGES/django.po").exists(), True)

    def test_valid_locale_with_numeric_region_code(self):
        out = StringIO()
        management.call_command(
            "makemessages", locale=["ar_002"], stdout=out, verbosity=1
        )
        self.assertNotIn("invalid locale ar_002", out.getvalue())
        self.assertIn("processing locale ar_002", out.getvalue())
        self.assertIs(Path("locale/ar_002/LC_MESSAGES/django.po").exists(), True)

    def test_valid_locale_tachelhit_latin_morocco(self):
        out = StringIO()
        management.call_command(
            "makemessages", locale=["shi_Latn_MA"], stdout=out, verbosity=1
        )
        self.assertNotIn("invalid locale shi_Latn_MA", out.getvalue())
        self.assertIn("processing locale shi_Latn_MA", out.getvalue())
        self.assertIs(Path("locale/shi_Latn_MA/LC_MESSAGES/django.po").exists(), True)

    def test_valid_locale_private_subtag(self):
        out = StringIO()
        management.call_command(
            "makemessages", locale=["nl_NL-x-informal"], stdout=out, verbosity=1
        )
        self.assertNotIn("invalid locale nl_NL-x-informal", out.getvalue())
        self.assertIn("processing locale nl_NL-x-informal", out.getvalue())
        self.assertIs(
            Path("locale/nl_NL-x-informal/LC_MESSAGES/django.po").exists(), True
        )

    def test_invalid_locale_uppercase(self):
        out = StringIO()
        management.call_command("makemessages", locale=["PL"], stdout=out, verbosity=1)
        self.assertIn("invalid locale PL, did you mean pl?", out.getvalue())
        self.assertNotIn("processing locale pl", out.getvalue())
        self.assertIs(Path("locale/pl/LC_MESSAGES/django.po").exists(), False)

    def test_invalid_locale_hyphen(self):
        out = StringIO()
        management.call_command(
            "makemessages", locale=["pl-PL"], stdout=out, verbosity=1
        )
        self.assertIn("invalid locale pl-PL, did you mean pl_PL?", out.getvalue())
        self.assertNotIn("processing locale pl-PL", out.getvalue())
        self.assertIs(Path("locale/pl-PL/LC_MESSAGES/django.po").exists(), False)

    def test_invalid_locale_lower_country(self):
        out = StringIO()
        management.call_command(
            "makemessages", locale=["pl_pl"], stdout=out, verbosity=1
        )
        self.assertIn("invalid locale pl_pl, did you mean pl_PL?", out.getvalue())
        self.assertNotIn("processing locale pl_pl", out.getvalue())
        self.assertIs(Path("locale/pl_pl/LC_MESSAGES/django.po").exists(), False)

    def test_invalid_locale_private_subtag(self):
        out = StringIO()
        management.call_command(
            "makemessages", locale=["nl-nl-x-informal"], stdout=out, verbosity=1
        )
        self.assertIn(
            "invalid locale nl-nl-x-informal, did you mean nl_NL-x-informal?",
            out.getvalue(),
        )
        self.assertNotIn("processing locale nl-nl-x-informal", out.getvalue())
        self.assertIs(
            Path("locale/nl-nl-x-informal/LC_MESSAGES/django.po").exists(), False
        )

    def test_invalid_locale_plus(self):
        out = StringIO()
        management.call_command(
            "makemessages", locale=["en+GB"], stdout=out, verbosity=1
        )
        self.assertIn("invalid locale en+GB, did you mean en_GB?", out.getvalue())
        self.assertNotIn("processing locale en+GB", out.getvalue())
        self.assertIs(Path("locale/en+GB/LC_MESSAGES/django.po").exists(), False)

    def test_invalid_locale_end_with_underscore(self):
        out = StringIO()
        management.call_command("makemessages", locale=["en_"], stdout=out, verbosity=1)
        self.assertIn("invalid locale en_", out.getvalue())
        self.assertNotIn("processing locale en_", out.getvalue())
        self.assertIs(Path("locale/en_/LC_MESSAGES/django.po").exists(), False)

    def test_invalid_locale_start_with_underscore(self):
        out = StringIO()
        management.call_command("makemessages", locale=["_en"], stdout=out, verbosity=1)
        self.assertIn("invalid locale _en", out.getvalue())
        self.assertNotIn("processing locale _en", out.getvalue())
        self.assertIs(Path("locale/_en/LC_MESSAGES/django.po").exists(), False)

    def test_comments_extractor(self):
        management.call_command("makemessages", locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, encoding="utf-8") as fp:
            po_contents = fp.read()
            self.assertNotIn("This comment should not be extracted", po_contents)

            # Comments in templates
            self.assertIn(
                "#. Translators: This comment should be extracted", po_contents
            )
            self.assertIn(
                "#. Translators: Django comment block for translators\n#. "
                "string's meaning unveiled",
                po_contents,
            )
            self.assertIn("#. Translators: One-line translator comment #1", po_contents)
            self.assertIn(
                "#. Translators: Two-line translator comment #1\n#. continued here.",
                po_contents,
            )
            self.assertIn("#. Translators: One-line translator comment #2", po_contents)
            self.assertIn(
                "#. Translators: Two-line translator comment #2\n#. continued here.",
                po_contents,
            )
            self.assertIn("#. Translators: One-line translator comment #3", po_contents)
            self.assertIn(
                "#. Translators: Two-line translator comment #3\n#. continued here.",
                po_contents,
            )
            self.assertIn("#. Translators: One-line translator comment #4", po_contents)
            self.assertIn(
                "#. Translators: Two-line translator comment #4\n#. continued here.",
                po_contents,
            )
            self.assertIn(
                "#. Translators: One-line translator comment #5 -- with "
                "non ASCII characters: áéíóúö",
                po_contents,
            )
            self.assertIn(
                "#. Translators: Two-line translator comment #5 -- with "
                "non ASCII characters: áéíóúö\n#. continued here.",
                po_contents,
            )

    def test_special_char_extracted(self):
        management.call_command("makemessages", locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, encoding="utf-8") as fp:
            po_contents = fp.read()
            self.assertMsgId("Non-breaking space\u00a0:", po_contents)

    def test_blocktranslate_trimmed(self):
        management.call_command("makemessages", locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
            # should not be trimmed
            self.assertNotMsgId("Text with a few line breaks.", po_contents)
            # should be trimmed
            self.assertMsgId(
                "Again some text with a few line breaks, this time should be trimmed.",
                po_contents,
            )
        # #21406 -- Should adjust for eaten line numbers
        self.assertMsgId("Get my line number", po_contents)
        self.assertLocationCommentPresent(
            self.PO_FILE, "Get my line number", "templates", "test.html"
        )

    def test_extraction_error(self):
        msg = (
            "Translation blocks must not include other block tags: blocktranslate "
            "(file %s, line 3)" % os.path.join("templates", "template_with_error.tpl")
        )
        with self.assertRaisesMessage(SyntaxError, msg):
            management.call_command(
                "makemessages", locale=[LOCALE], extensions=["tpl"], verbosity=0
            )
        # The temporary files were cleaned up.
        self.assertFalse(os.path.exists("./templates/template_with_error.tpl.py"))
        self.assertFalse(os.path.exists("./templates/template_0_with_no_error.tpl.py"))

    def test_unicode_decode_error(self):
        shutil.copyfile("./not_utf8.sample", "./not_utf8.txt")
        out = StringIO()
        management.call_command("makemessages", locale=[LOCALE], stdout=out)
        self.assertIn(
            "UnicodeDecodeError: skipped file not_utf8.txt in .", out.getvalue()
        )

    def test_unicode_file_name(self):
        open(os.path.join(self.test_dir, "vidéo.txt"), "a").close()
        management.call_command("makemessages", locale=[LOCALE], verbosity=0)

    def test_extraction_warning(self):
        """test xgettext warning about multiple bare interpolation placeholders"""
        shutil.copyfile("./code.sample", "./code_sample.py")
        out = StringIO()
        management.call_command("makemessages", locale=[LOCALE], stdout=out)
        self.assertIn("code_sample.py:4", out.getvalue())

    def test_template_message_context_extractor(self):
        """
        Message contexts are correctly extracted for the {% translate %} and
        {% blocktranslate %} template tags (#14806).
        """
        management.call_command("makemessages", locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
            # {% translate %}
            self.assertIn('msgctxt "Special trans context #1"', po_contents)
            self.assertMsgId("Translatable literal #7a", po_contents)
            self.assertIn('msgctxt "Special trans context #2"', po_contents)
            self.assertMsgId("Translatable literal #7b", po_contents)
            self.assertIn('msgctxt "Special trans context #3"', po_contents)
            self.assertMsgId("Translatable literal #7c", po_contents)

            # {% translate %} with a filter
            for (
                minor_part
            ) in "abcdefgh":  # Iterate from #7.1a to #7.1h template markers
                self.assertIn(
                    'msgctxt "context #7.1{}"'.format(minor_part), po_contents
                )
                self.assertMsgId(
                    "Translatable literal #7.1{}".format(minor_part), po_contents
                )

            # {% blocktranslate %}
            self.assertIn('msgctxt "Special blocktranslate context #1"', po_contents)
            self.assertMsgId("Translatable literal #8a", po_contents)
            self.assertIn('msgctxt "Special blocktranslate context #2"', po_contents)
            self.assertMsgId("Translatable literal #8b-singular", po_contents)
            self.assertIn("Translatable literal #8b-plural", po_contents)
            self.assertIn('msgctxt "Special blocktranslate context #3"', po_contents)
            self.assertMsgId("Translatable literal #8c-singular", po_contents)
            self.assertIn("Translatable literal #8c-plural", po_contents)
            self.assertIn('msgctxt "Special blocktranslate context #4"', po_contents)
            self.assertMsgId("Translatable literal #8d %(a)s", po_contents)

            # {% trans %} and {% blocktrans %}
            self.assertMsgId("trans text", po_contents)
            self.assertMsgId("blocktrans text", po_contents)

    def test_context_in_single_quotes(self):
        management.call_command("makemessages", locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
            # {% translate %}
            self.assertIn('msgctxt "Context wrapped in double quotes"', po_contents)
            self.assertIn('msgctxt "Context wrapped in single quotes"', po_contents)

            # {% blocktranslate %}
            self.assertIn(
                'msgctxt "Special blocktranslate context wrapped in double quotes"',
                po_contents,
            )
            self.assertIn(
                'msgctxt "Special blocktranslate context wrapped in single quotes"',
                po_contents,
            )

    def test_template_comments(self):
        """Template comment tags on the same line of other constructs (#19552)"""
        # Test detection/end user reporting of old, incorrect templates
        # translator comments syntax
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            management.call_command(
                "makemessages", locale=[LOCALE], extensions=["thtml"], verbosity=0
            )
            self.assertEqual(len(ws), 3)
            for w in ws:
                self.assertTrue(issubclass(w.category, TranslatorCommentWarning))
            self.assertRegex(
                str(ws[0].message),
                r"The translator-targeted comment 'Translators: ignored i18n "
                r"comment #1' \(file templates[/\\]comments.thtml, line 4\) "
                r"was ignored, because it wasn't the last item on the line\.",
            )
            self.assertRegex(
                str(ws[1].message),
                r"The translator-targeted comment 'Translators: ignored i18n "
                r"comment #3' \(file templates[/\\]comments.thtml, line 6\) "
                r"was ignored, because it wasn't the last item on the line\.",
            )
            self.assertRegex(
                str(ws[2].message),
                r"The translator-targeted comment 'Translators: ignored i18n "
                r"comment #4' \(file templates[/\\]comments.thtml, line 8\) "
                r"was ignored, because it wasn't the last item on the line\.",
            )
        # Now test .po file contents
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()

            self.assertMsgId("Translatable literal #9a", po_contents)
            self.assertNotIn("ignored comment #1", po_contents)

            self.assertNotIn("Translators: ignored i18n comment #1", po_contents)
            self.assertMsgId("Translatable literal #9b", po_contents)

            self.assertNotIn("ignored i18n comment #2", po_contents)
            self.assertNotIn("ignored comment #2", po_contents)
            self.assertMsgId("Translatable literal #9c", po_contents)

            self.assertNotIn("ignored comment #3", po_contents)
            self.assertNotIn("ignored i18n comment #3", po_contents)
            self.assertMsgId("Translatable literal #9d", po_contents)

            self.assertNotIn("ignored comment #4", po_contents)
            self.assertMsgId("Translatable literal #9e", po_contents)
            self.assertNotIn("ignored comment #5", po_contents)

            self.assertNotIn("ignored i18n comment #4", po_contents)
            self.assertMsgId("Translatable literal #9f", po_contents)
            self.assertIn("#. Translators: valid i18n comment #5", po_contents)

            self.assertMsgId("Translatable literal #9g", po_contents)
            self.assertIn("#. Translators: valid i18n comment #6", po_contents)
            self.assertMsgId("Translatable literal #9h", po_contents)
            self.assertIn("#. Translators: valid i18n comment #7", po_contents)
            self.assertMsgId("Translatable literal #9i", po_contents)

            self.assertRegex(po_contents, r"#\..+Translators: valid i18n comment #8")
            self.assertRegex(po_contents, r"#\..+Translators: valid i18n comment #9")
            self.assertMsgId("Translatable literal #9j", po_contents)

    def test_makemessages_find_files(self):
        """
        find_files only discover files having the proper extensions.
        """
        cmd = MakeMessagesCommand()
        cmd.ignore_patterns = ["CVS", ".*", "*~", "*.pyc"]
        cmd.symlinks = False
        cmd.domain = "django"
        cmd.extensions = [".html", ".txt", ".py"]
        cmd.verbosity = 0
        cmd.locale_paths = []
        cmd.default_locale_path = os.path.join(self.test_dir, "locale")
        found_files = cmd.find_files(self.test_dir)
        self.assertGreater(len(found_files), 1)
        found_exts = {os.path.splitext(tfile.file)[1] for tfile in found_files}
        self.assertEqual(found_exts.difference({".py", ".html", ".txt"}), set())

        cmd.extensions = [".js"]
        cmd.domain = "djangojs"
        found_files = cmd.find_files(self.test_dir)
        self.assertGreater(len(found_files), 1)
        found_exts = {os.path.splitext(tfile.file)[1] for tfile in found_files}
        self.assertEqual(found_exts.difference({".js"}), set())

    @mock.patch("django.core.management.commands.makemessages.popen_wrapper")
    def test_makemessages_gettext_version(self, mocked_popen_wrapper):
        # "Normal" output:
        mocked_popen_wrapper.return_value = (
            "xgettext (GNU gettext-tools) 0.18.1\n"
            "Copyright (C) 1995-1998, 2000-2010 Free Software Foundation, Inc.\n"
            "License GPLv3+: GNU GPL version 3 or later "
            "<http://gnu.org/licenses/gpl.html>\n"
            "This is free software: you are free to change and redistribute it.\n"
            "There is NO WARRANTY, to the extent permitted by law.\n"
            "Written by Ulrich Drepper.\n",
            "",
            0,
        )
        cmd = MakeMessagesCommand()
        self.assertEqual(cmd.gettext_version, (0, 18, 1))

        # Version number with only 2 parts (#23788)
        mocked_popen_wrapper.return_value = (
            "xgettext (GNU gettext-tools) 0.17\n",
            "",
            0,
        )
        cmd = MakeMessagesCommand()
        self.assertEqual(cmd.gettext_version, (0, 17))

        # Bad version output
        mocked_popen_wrapper.return_value = ("any other return value\n", "", 0)
        cmd = MakeMessagesCommand()
        with self.assertRaisesMessage(
            CommandError, "Unable to get gettext version. Is it installed?"
        ):
            cmd.gettext_version

    def test_po_file_encoding_when_updating(self):
        """
        Update of PO file doesn't corrupt it with non-UTF-8 encoding on Windows
        (#23271).
        """
        BR_PO_BASE = "locale/pt_BR/LC_MESSAGES/django"
        shutil.copyfile(BR_PO_BASE + ".pristine", BR_PO_BASE + ".po")
        management.call_command("makemessages", locale=["pt_BR"], verbosity=0)
        self.assertTrue(os.path.exists(BR_PO_BASE + ".po"))
        with open(BR_PO_BASE + ".po", encoding="utf-8") as fp:
            po_contents = fp.read()
            self.assertMsgStr("Größe", po_contents)

    def test_pot_charset_header_is_utf8(self):
        """Content-Type: ... charset=CHARSET is replaced with charset=UTF-8"""
        msgs = (
            "# SOME DESCRIPTIVE TITLE.\n"
            "# (some lines truncated as they are not relevant)\n"
            '"Content-Type: text/plain; charset=CHARSET\\n"\n'
            '"Content-Transfer-Encoding: 8bit\\n"\n'
            "\n"
            "#: somefile.py:8\n"
            'msgid "mañana; charset=CHARSET"\n'
            'msgstr ""\n'
        )
        with tempfile.NamedTemporaryFile() as pot_file:
            pot_filename = pot_file.name
        write_pot_file(pot_filename, msgs)
        with open(pot_filename, encoding="utf-8") as fp:
            pot_contents = fp.read()
            self.assertIn("Content-Type: text/plain; charset=UTF-8", pot_contents)
            self.assertIn("mañana; charset=CHARSET", pot_contents)


class JavaScriptExtractorTests(ExtractorTests):
    PO_FILE = "locale/%s/LC_MESSAGES/djangojs.po" % LOCALE

    def test_javascript_literals(self):
        _, po_contents = self._run_makemessages(domain="djangojs")
        self.assertMsgId("This literal should be included.", po_contents)
        self.assertMsgId("gettext_noop should, too.", po_contents)
        self.assertMsgId("This one as well.", po_contents)
        self.assertMsgId(r"He said, \"hello\".", po_contents)
        self.assertMsgId("okkkk", po_contents)
        self.assertMsgId("TEXT", po_contents)
        self.assertMsgId("It's at http://example.com", po_contents)
        self.assertMsgId("String", po_contents)
        self.assertMsgId(
            "/* but this one will be too */ 'cause there is no way of telling...",
            po_contents,
        )
        self.assertMsgId("foo", po_contents)
        self.assertMsgId("bar", po_contents)
        self.assertMsgId("baz", po_contents)
        self.assertMsgId("quz", po_contents)
        self.assertMsgId("foobar", po_contents)

    def test_media_static_dirs_ignored(self):
        """
        Regression test for #23583.
        """
        with override_settings(
            STATIC_ROOT=os.path.join(self.test_dir, "static/"),
            MEDIA_ROOT=os.path.join(self.test_dir, "media_root/"),
        ):
            _, po_contents = self._run_makemessages(domain="djangojs")
            self.assertMsgId(
                "Static content inside app should be included.", po_contents
            )
            self.assertNotMsgId(
                "Content from STATIC_ROOT should not be included", po_contents
            )

    @override_settings(STATIC_ROOT=None, MEDIA_ROOT="")
    def test_default_root_settings(self):
        """
        Regression test for #23717.
        """
        _, po_contents = self._run_makemessages(domain="djangojs")
        self.assertMsgId("Static content inside app should be included.", po_contents)

    def test_i18n_catalog_ignored_when_invoked_for_django(self):
        # Create target file so it exists in the filesystem and can be ignored.
        # "invoked_for_django" is True when "conf/locale" folder exists.
        os.makedirs(os.path.join("conf", "locale"))
        i18n_catalog_js_dir = os.path.join(os.path.curdir, "views", "templates")
        os.makedirs(i18n_catalog_js_dir)
        open(os.path.join(i18n_catalog_js_dir, "i18n_catalog.js"), "w").close()

        out, _ = self._run_makemessages(domain="djangojs")
        self.assertIn(f"ignoring file i18n_catalog.js in {i18n_catalog_js_dir}", out)

    def test_i18n_catalog_not_ignored_when_not_invoked_for_django(self):
        # Create target file so it exists in the filesystem but is NOT ignored.
        # "invoked_for_django" is False when "conf/locale" folder does not exist.
        self.assertIs(os.path.exists(os.path.join("conf", "locale")), False)
        i18n_catalog_js = os.path.join("views", "templates", "i18n_catalog.js")
        os.makedirs(os.path.dirname(i18n_catalog_js))
        open(i18n_catalog_js, "w").close()

        out, _ = self._run_makemessages(domain="djangojs")
        self.assertNotIn("ignoring file i18n_catalog.js", out)


class IgnoredExtractorTests(ExtractorTests):
    def test_ignore_directory(self):
        out, po_contents = self._run_makemessages(
            ignore_patterns=[
                os.path.join("ignore_dir", "*"),
            ]
        )
        self.assertIn("ignoring directory ignore_dir", out)
        self.assertMsgId("This literal should be included.", po_contents)
        self.assertNotMsgId("This should be ignored.", po_contents)

    def test_ignore_subdirectory(self):
        out, po_contents = self._run_makemessages(
            ignore_patterns=[
                "templates/*/ignore.html",
                "templates/subdir/*",
            ]
        )
        self.assertIn("ignoring directory subdir", out)
        self.assertNotMsgId("This subdir should be ignored too.", po_contents)

    def test_ignore_file_patterns(self):
        out, po_contents = self._run_makemessages(
            ignore_patterns=[
                "xxx_*",
            ]
        )
        self.assertIn("ignoring file xxx_ignored.html", out)
        self.assertNotMsgId("This should be ignored too.", po_contents)

    def test_media_static_dirs_ignored(self):
        with override_settings(
            STATIC_ROOT=os.path.join(self.test_dir, "static/"),
            MEDIA_ROOT=os.path.join(self.test_dir, "media_root/"),
        ):
            out, _ = self._run_makemessages()
            self.assertIn("ignoring directory static", out)
            self.assertIn("ignoring directory media_root", out)


class SymlinkExtractorTests(ExtractorTests):
    def setUp(self):
        super().setUp()
        self.symlinked_dir = os.path.join(self.test_dir, "templates_symlinked")

    def test_symlink(self):
        if symlinks_supported():
            os.symlink(os.path.join(self.test_dir, "templates"), self.symlinked_dir)
        else:
            self.skipTest(
                "os.symlink() not available on this OS + Python version combination."
            )
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, symlinks=True
        )
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
            self.assertMsgId("This literal should be included.", po_contents)
        self.assertLocationCommentPresent(
            self.PO_FILE, None, "templates_symlinked", "test.html"
        )


class CopyPluralFormsExtractorTests(ExtractorTests):
    PO_FILE_ES = "locale/es/LC_MESSAGES/django.po"

    def test_copy_plural_forms(self):
        management.call_command("makemessages", locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
            self.assertIn("Plural-Forms: nplurals=2; plural=(n != 1)", po_contents)

    def test_override_plural_forms(self):
        """Ticket #20311."""
        management.call_command(
            "makemessages", locale=["es"], extensions=["djtpl"], verbosity=0
        )
        self.assertTrue(os.path.exists(self.PO_FILE_ES))
        with open(self.PO_FILE_ES, encoding="utf-8") as fp:
            po_contents = fp.read()
            found = re.findall(
                r'^(?P<value>"Plural-Forms.+?\\n")\s*$',
                po_contents,
                re.MULTILINE | re.DOTALL,
            )
            self.assertEqual(1, len(found))

    def test_translate_and_plural_blocktranslate_collision(self):
        """
        Ensures a correct workaround for the gettext bug when handling a literal
        found inside a {% translate %} tag and also in another file inside a
        {% blocktranslate %} with a plural (#17375).
        """
        management.call_command(
            "makemessages", locale=[LOCALE], extensions=["html", "djtpl"], verbosity=0
        )
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
            self.assertNotIn(
                "#-#-#-#-#  django.pot (PACKAGE VERSION)  #-#-#-#-#\\n", po_contents
            )
            self.assertMsgId(
                "First `translate`, then `blocktranslate` with a plural", po_contents
            )
            self.assertMsgIdPlural(
                "Plural for a `translate` and `blocktranslate` collision case",
                po_contents,
            )


class NoWrapExtractorTests(ExtractorTests):
    def test_no_wrap_enabled(self):
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, no_wrap=True
        )
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
            self.assertMsgId(
                "This literal should also be included wrapped or not wrapped "
                "depending on the use of the --no-wrap option.",
                po_contents,
            )

    def test_no_wrap_disabled(self):
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, no_wrap=False
        )
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
            self.assertMsgId(
                '""\n"This literal should also be included wrapped or not '
                'wrapped depending on the "\n"use of the --no-wrap option."',
                po_contents,
                use_quotes=False,
            )


class LocationCommentsTests(ExtractorTests):
    def test_no_location_enabled(self):
        """Behavior is correct if --no-location switch is specified. See #16903."""
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, no_location=True
        )
        self.assertTrue(os.path.exists(self.PO_FILE))
        self.assertLocationCommentNotPresent(self.PO_FILE, None, "test.html")

    def test_no_location_disabled(self):
        """Behavior is correct if --no-location switch isn't specified."""
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, no_location=False
        )
        self.assertTrue(os.path.exists(self.PO_FILE))
        # #16903 -- Standard comment with source file relative path should be present
        self.assertLocationCommentPresent(
            self.PO_FILE, "Translatable literal #6b", "templates", "test.html"
        )

    def test_location_comments_for_templatized_files(self):
        """
        Ensure no leaky paths in comments, e.g. #: path\to\file.html.py:123
        Refs #21209/#26341.
        """
        management.call_command("makemessages", locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
        self.assertMsgId("#: templates/test.html.py", po_contents)
        self.assertLocationCommentNotPresent(self.PO_FILE, None, ".html.py")
        self.assertLocationCommentPresent(self.PO_FILE, 5, "templates", "test.html")

    def test_add_location_full(self):
        """makemessages --add-location=full"""
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, add_location="full"
        )
        self.assertTrue(os.path.exists(self.PO_FILE))
        # Comment with source file relative path and line number is present.
        self.assertLocationCommentPresent(
            self.PO_FILE, "Translatable literal #6b", "templates", "test.html"
        )

    def test_add_location_file(self):
        """makemessages --add-location=file"""
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, add_location="file"
        )
        self.assertTrue(os.path.exists(self.PO_FILE))
        # Comment with source file relative path is present.
        self.assertLocationCommentPresent(self.PO_FILE, None, "templates", "test.html")
        # But it should not contain the line number.
        self.assertLocationCommentNotPresent(
            self.PO_FILE, "Translatable literal #6b", "templates", "test.html"
        )

    def test_add_location_never(self):
        """makemessages --add-location=never"""
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, add_location="never"
        )
        self.assertTrue(os.path.exists(self.PO_FILE))
        self.assertLocationCommentNotPresent(self.PO_FILE, None, "test.html")


class NoObsoleteExtractorTests(ExtractorTests):
    work_subdir = "obsolete_translations"

    def test_no_obsolete(self):
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, no_obsolete=True
        )
        self.assertIs(os.path.exists(self.PO_FILE), True)
        with open(self.PO_FILE) as fp:
            po_contents = fp.read()
            self.assertNotIn('#~ msgid "Obsolete string."', po_contents)
            self.assertNotIn('#~ msgstr "Translated obsolete string."', po_contents)
            self.assertMsgId("This is a translatable string.", po_contents)
            self.assertMsgStr("This is a translated string.", po_contents)


class KeepPotFileExtractorTests(ExtractorTests):
    POT_FILE = "locale/django.pot"

    def test_keep_pot_disabled_by_default(self):
        management.call_command("makemessages", locale=[LOCALE], verbosity=0)
        self.assertFalse(os.path.exists(self.POT_FILE))

    def test_keep_pot_explicitly_disabled(self):
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, keep_pot=False
        )
        self.assertFalse(os.path.exists(self.POT_FILE))

    def test_keep_pot_enabled(self):
        management.call_command(
            "makemessages", locale=[LOCALE], verbosity=0, keep_pot=True
        )
        self.assertTrue(os.path.exists(self.POT_FILE))


class MultipleLocaleExtractionTests(ExtractorTests):
    PO_FILE_PT = "locale/pt/LC_MESSAGES/django.po"
    PO_FILE_DE = "locale/de/LC_MESSAGES/django.po"
    PO_FILE_KO = "locale/ko/LC_MESSAGES/django.po"
    LOCALES = ["pt", "de", "ch"]

    def test_multiple_locales(self):
        management.call_command("makemessages", locale=["pt", "de"], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE_PT))
        self.assertTrue(os.path.exists(self.PO_FILE_DE))

    def test_all_locales(self):
        """
        When the `locale` flag is absent, all dirs from the parent locale dir
        are considered as language directories, except if the directory doesn't
        start with two letters (which excludes __pycache__, .gitignore, etc.).
        """
        os.mkdir(os.path.join("locale", "_do_not_pick"))
        # Excluding locales that do not compile
        management.call_command("makemessages", exclude=["ja", "es_AR"], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE_KO))
        self.assertFalse(os.path.exists("locale/_do_not_pick/LC_MESSAGES/django.po"))


class ExcludedLocaleExtractionTests(ExtractorTests):
    work_subdir = "exclude"

    LOCALES = ["en", "fr", "it"]
    PO_FILE = "locale/%s/LC_MESSAGES/django.po"

    def _set_times_for_all_po_files(self):
        """
        Set access and modification times to the Unix epoch time for all the .po files.
        """
        for locale in self.LOCALES:
            os.utime(self.PO_FILE % locale, (0, 0))

    def setUp(self):
        super().setUp()
        copytree("canned_locale", "locale")
        self._set_times_for_all_po_files()

    def test_command_help(self):
        with captured_stdout(), captured_stderr():
            # `call_command` bypasses the parser; by calling
            # `execute_from_command_line` with the help subcommand we
            # ensure that there are no issues with the parser itself.
            execute_from_command_line(["django-admin", "help", "makemessages"])

    def test_one_locale_excluded(self):
        management.call_command("makemessages", exclude=["it"], verbosity=0)
        self.assertRecentlyModified(self.PO_FILE % "en")
        self.assertRecentlyModified(self.PO_FILE % "fr")
        self.assertNotRecentlyModified(self.PO_FILE % "it")

    def test_multiple_locales_excluded(self):
        management.call_command("makemessages", exclude=["it", "fr"], verbosity=0)
        self.assertRecentlyModified(self.PO_FILE % "en")
        self.assertNotRecentlyModified(self.PO_FILE % "fr")
        self.assertNotRecentlyModified(self.PO_FILE % "it")

    def test_one_locale_excluded_with_locale(self):
        management.call_command(
            "makemessages", locale=["en", "fr"], exclude=["fr"], verbosity=0
        )
        self.assertRecentlyModified(self.PO_FILE % "en")
        self.assertNotRecentlyModified(self.PO_FILE % "fr")
        self.assertNotRecentlyModified(self.PO_FILE % "it")

    def test_multiple_locales_excluded_with_locale(self):
        management.call_command(
            "makemessages", locale=["en", "fr", "it"], exclude=["fr", "it"], verbosity=0
        )
        self.assertRecentlyModified(self.PO_FILE % "en")
        self.assertNotRecentlyModified(self.PO_FILE % "fr")
        self.assertNotRecentlyModified(self.PO_FILE % "it")


class CustomLayoutExtractionTests(ExtractorTests):
    work_subdir = "project_dir"

    def test_no_locale_raises(self):
        msg = (
            "Unable to find a locale path to store translations for file "
            "__init__.py. Make sure the 'locale' directory exists in an app "
            "or LOCALE_PATHS setting is set."
        )
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command("makemessages", locale=[LOCALE], verbosity=0)
        # Working files are cleaned up on an error.
        self.assertFalse(os.path.exists("./app_no_locale/test.html.py"))

    def test_project_locale_paths(self):
        self._test_project_locale_paths(os.path.join(self.test_dir, "project_locale"))

    def test_project_locale_paths_pathlib(self):
        self._test_project_locale_paths(Path(self.test_dir) / "project_locale")

    def _test_project_locale_paths(self, locale_path):
        """
        * translations for an app containing a locale folder are stored in that folder
        * translations outside of that app are in LOCALE_PATHS[0]
        """
        with override_settings(LOCALE_PATHS=[locale_path]):
            management.call_command("makemessages", locale=[LOCALE], verbosity=0)
            project_de_locale = os.path.join(
                self.test_dir, "project_locale", "de", "LC_MESSAGES", "django.po"
            )
            app_de_locale = os.path.join(
                self.test_dir,
                "app_with_locale",
                "locale",
                "de",
                "LC_MESSAGES",
                "django.po",
            )
            self.assertTrue(os.path.exists(project_de_locale))
            self.assertTrue(os.path.exists(app_de_locale))

            with open(project_de_locale) as fp:
                po_contents = fp.read()
                self.assertMsgId("This app has no locale directory", po_contents)
                self.assertMsgId("This is a project-level string", po_contents)
            with open(app_de_locale) as fp:
                po_contents = fp.read()
                self.assertMsgId("This app has a locale directory", po_contents)


@skipUnless(has_xgettext, "xgettext is mandatory for extraction tests")
class NoSettingsExtractionTests(AdminScriptTestCase):
    def test_makemessages_no_settings(self):
        out, err = self.run_django_admin(["makemessages", "-l", "en", "-v", "0"])
        self.assertNoOutput(err)
        self.assertNoOutput(out)


class UnchangedPoExtractionTests(ExtractorTests):
    work_subdir = "unchanged"

    def setUp(self):
        super().setUp()
        po_file = Path(self.PO_FILE)
        po_file_tmp = Path(self.PO_FILE + ".tmp")
        if os.name == "nt":
            # msgmerge outputs Windows style paths on Windows.
            po_contents = po_file_tmp.read_text().replace(
                "#: __init__.py",
                "#: .\\__init__.py",
            )
            po_file.write_text(po_contents)
        else:
            po_file_tmp.rename(po_file)
        self.original_po_contents = po_file.read_text()

    def test_po_remains_unchanged(self):
        """PO files are unchanged unless there are new changes."""
        _, po_contents = self._run_makemessages()
        self.assertEqual(po_contents, self.original_po_contents)

    def test_po_changed_with_new_strings(self):
        """PO files are updated when new changes are detected."""
        Path("models.py.tmp").rename("models.py")
        _, po_contents = self._run_makemessages()
        self.assertNotEqual(po_contents, self.original_po_contents)
        self.assertMsgId(
            "This is a hitherto undiscovered translatable string.",
            po_contents,
        )
