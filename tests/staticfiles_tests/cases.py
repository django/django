import codecs
import os
import shutil
import tempfile

from django.conf import settings
from django.core.management import call_command
from django.template import Context, Template
from django.test import SimpleTestCase, override_settings
from django.utils.encoding import force_text

from .settings import TEST_SETTINGS


class BaseStaticFilesMixin(object):
    """
    Test case with a couple utility assertions.
    """

    def assertFileContains(self, filepath, text):
        self.assertIn(
            text,
            self._get_file(force_text(filepath)),
            "'%s' not in '%s'" % (text, filepath),
        )

    def assertFileNotFound(self, filepath):
        with self.assertRaises(IOError):
            self._get_file(filepath)

    def render_template(self, template, **kwargs):
        if isinstance(template, str):
            template = Template(template)
        return template.render(Context(**kwargs)).strip()

    def static_template_snippet(self, path, asvar=False):
        if asvar:
            return "{%% load static from staticfiles %%}{%% static '%s' as var %%}{{ var }}" % path
        return "{%% load static from staticfiles %%}{%% static '%s' %%}" % path

    def assertStaticRenders(self, path, result, asvar=False, **kwargs):
        template = self.static_template_snippet(path, asvar)
        self.assertEqual(self.render_template(template, **kwargs), result)

    def assertStaticRaises(self, exc, path, result, asvar=False, **kwargs):
        with self.assertRaises(exc):
            self.assertStaticRenders(path, result, **kwargs)


@override_settings(**TEST_SETTINGS)
class StaticFilesTestCase(BaseStaticFilesMixin, SimpleTestCase):
    pass


@override_settings(**TEST_SETTINGS)
class CollectionTestCase(BaseStaticFilesMixin, SimpleTestCase):
    """
    Tests shared by all file finding features (collectstatic,
    findstatic, and static serve view).

    This relies on the asserts defined in BaseStaticFilesTestCase, but
    is separated because some test cases need those asserts without
    all these tests.
    """
    def setUp(self):
        super(CollectionTestCase, self).setUp()
        temp_dir = tempfile.mkdtemp()
        # Override the STATIC_ROOT for all tests from setUp to tearDown
        # rather than as a context manager
        self.patched_settings = self.settings(STATIC_ROOT=temp_dir)
        self.patched_settings.enable()
        self.run_collectstatic()
        # Same comment as in runtests.teardown.
        self.addCleanup(shutil.rmtree, temp_dir)

    def tearDown(self):
        self.patched_settings.disable()
        super(CollectionTestCase, self).tearDown()

    def run_collectstatic(self, **kwargs):
        verbosity = kwargs.pop('verbosity', 0)
        call_command('collectstatic', interactive=False, verbosity=verbosity,
                     ignore_patterns=['*.ignoreme'], **kwargs)

    def _get_file(self, filepath):
        assert filepath, 'filepath is empty.'
        filepath = os.path.join(settings.STATIC_ROOT, filepath)
        with codecs.open(filepath, "r", "utf-8") as f:
            return f.read()


class TestDefaults(object):
    """
    A few standard test cases.
    """
    def test_staticfiles_dirs(self):
        """
        Can find a file in a STATICFILES_DIRS directory.
        """
        self.assertFileContains('test.txt', 'Can we find')
        self.assertFileContains(os.path.join('prefix', 'test.txt'), 'Prefix')

    def test_staticfiles_dirs_subdir(self):
        """
        Can find a file in a subdirectory of a STATICFILES_DIRS
        directory.
        """
        self.assertFileContains('subdir/test.txt', 'Can we find')

    def test_staticfiles_dirs_priority(self):
        """
        File in STATICFILES_DIRS has priority over file in app.
        """
        self.assertFileContains('test/file.txt', 'STATICFILES_DIRS')

    def test_app_files(self):
        """
        Can find a file in an app static/ directory.
        """
        self.assertFileContains('test/file1.txt', 'file1 in the app dir')

    def test_nonascii_filenames(self):
        """
        Can find a file with non-ASCII character in an app static/ directory.
        """
        self.assertFileContains('test/⊗.txt', '⊗ in the app dir')

    def test_camelcase_filenames(self):
        """
        Can find a file with capital letters.
        """
        self.assertFileContains('test/camelCase.txt', 'camelCase')
