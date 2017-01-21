import os

from django.conf import settings
from django.contrib.staticfiles import finders, storage
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from .cases import StaticFilesTestCase
from .settings import TEST_ROOT


class TestFinders:
    """
    Base finder test mixin.

    On Windows, sometimes the case of the path we ask the finders for and the
    path(s) they find can differ. Compare them using os.path.normcase() to
    avoid false negatives.
    """
    def test_find_first(self):
        src, dst = self.find_first
        found = self.finder.find(src)
        self.assertEqual(os.path.normcase(found), os.path.normcase(dst))

    def test_find_all(self):
        src, dst = self.find_all
        found = self.finder.find(src, all=True)
        found = [os.path.normcase(f) for f in found]
        dst = [os.path.normcase(d) for d in dst]
        self.assertEqual(found, dst)


class TestFileSystemFinder(TestFinders, StaticFilesTestCase):
    """
    Test FileSystemFinder.
    """
    def setUp(self):
        super().setUp()
        self.finder = finders.FileSystemFinder()
        test_file_path = os.path.join(TEST_ROOT, 'project', 'documents', 'test', 'file.txt')
        self.find_first = (os.path.join('test', 'file.txt'), test_file_path)
        self.find_all = (os.path.join('test', 'file.txt'), [test_file_path])


class TestAppDirectoriesFinder(TestFinders, StaticFilesTestCase):
    """
    Test AppDirectoriesFinder.
    """
    def setUp(self):
        super().setUp()
        self.finder = finders.AppDirectoriesFinder()
        test_file_path = os.path.join(TEST_ROOT, 'apps', 'test', 'static', 'test', 'file1.txt')
        self.find_first = (os.path.join('test', 'file1.txt'), test_file_path)
        self.find_all = (os.path.join('test', 'file1.txt'), [test_file_path])


class TestDefaultStorageFinder(TestFinders, StaticFilesTestCase):
    """
    Test DefaultStorageFinder.
    """
    def setUp(self):
        super().setUp()
        self.finder = finders.DefaultStorageFinder(
            storage=storage.StaticFilesStorage(location=settings.MEDIA_ROOT))
        test_file_path = os.path.join(settings.MEDIA_ROOT, 'media-file.txt')
        self.find_first = ('media-file.txt', test_file_path)
        self.find_all = ('media-file.txt', [test_file_path])


@override_settings(
    STATICFILES_FINDERS=['django.contrib.staticfiles.finders.FileSystemFinder'],
    STATICFILES_DIRS=[os.path.join(TEST_ROOT, 'project', 'documents')],
)
class TestMiscFinder(SimpleTestCase):
    """
    A few misc finder tests.
    """
    def test_get_finder(self):
        self.assertIsInstance(finders.get_finder(
            'django.contrib.staticfiles.finders.FileSystemFinder'),
            finders.FileSystemFinder)

    def test_get_finder_bad_classname(self):
        with self.assertRaises(ImportError):
            finders.get_finder('django.contrib.staticfiles.finders.FooBarFinder')

    def test_get_finder_bad_module(self):
        with self.assertRaises(ImportError):
            finders.get_finder('foo.bar.FooBarFinder')

    def test_cache(self):
        finders.get_finder.cache_clear()
        for n in range(10):
            finders.get_finder('django.contrib.staticfiles.finders.FileSystemFinder')
        cache_info = finders.get_finder.cache_info()
        self.assertEqual(cache_info.hits, 9)
        self.assertEqual(cache_info.currsize, 1)

    def test_searched_locations(self):
        finders.find('spam')
        self.assertEqual(
            finders.searched_locations,
            [os.path.join(TEST_ROOT, 'project', 'documents')]
        )

    @override_settings(STATICFILES_DIRS='a string')
    def test_non_tuple_raises_exception(self):
        """
        We can't determine if STATICFILES_DIRS is set correctly just by
        looking at the type, but we can determine if it's definitely wrong.
        """
        with self.assertRaises(ImproperlyConfigured):
            finders.FileSystemFinder()

    @override_settings(MEDIA_ROOT='')
    def test_location_empty(self):
        with self.assertRaises(ImproperlyConfigured):
            finders.DefaultStorageFinder()
