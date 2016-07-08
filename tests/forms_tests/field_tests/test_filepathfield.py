from __future__ import unicode_literals

import os.path

from django.forms import FilePathField, ValidationError, forms
from django.test import SimpleTestCase
from django.utils import six
from django.utils._os import upath


def fix_os_paths(x):
    if isinstance(x, six.string_types):
        return x.replace('\\', '/')
    elif isinstance(x, tuple):
        return tuple(fix_os_paths(list(x)))
    elif isinstance(x, list):
        return [fix_os_paths(y) for y in x]
    else:
        return x


class FilePathFieldTest(SimpleTestCase):

    def test_filepathfield_1(self):
        path = os.path.abspath(upath(forms.__file__))
        path = os.path.dirname(path) + '/'
        self.assertTrue(fix_os_paths(path).endswith('/django/forms/'))

    def test_filepathfield_2(self):
        path = upath(forms.__file__)
        path = os.path.dirname(os.path.abspath(path)) + '/'
        f = FilePathField(path=path)
        f.choices = [p for p in f.choices if p[0].endswith('.py')]
        f.choices.sort()
        expected = [
            ('/django/forms/__init__.py', '__init__.py'),
            ('/django/forms/boundfield.py', 'boundfield.py'),
            ('/django/forms/fields.py', 'fields.py'),
            ('/django/forms/forms.py', 'forms.py'),
            ('/django/forms/formsets.py', 'formsets.py'),
            ('/django/forms/models.py', 'models.py'),
            ('/django/forms/utils.py', 'utils.py'),
            ('/django/forms/widgets.py', 'widgets.py')
        ]
        for exp, got in zip(expected, fix_os_paths(f.choices)):
            self.assertEqual(exp[1], got[1])
            self.assertTrue(got[0].endswith(exp[0]))
        msg = "'Select a valid choice. fields.py is not one of the available choices.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('fields.py')
        self.assertTrue(fix_os_paths(f.clean(path + 'fields.py')).endswith('/django/forms/fields.py'))

    def test_filepathfield_3(self):
        path = upath(forms.__file__)
        path = os.path.dirname(os.path.abspath(path)) + '/'
        f = FilePathField(path=path, match='^.*?\.py$')
        f.choices.sort()
        expected = [
            ('/django/forms/__init__.py', '__init__.py'),
            ('/django/forms/boundfield.py', 'boundfield.py'),
            ('/django/forms/fields.py', 'fields.py'),
            ('/django/forms/forms.py', 'forms.py'),
            ('/django/forms/formsets.py', 'formsets.py'),
            ('/django/forms/models.py', 'models.py'),
            ('/django/forms/utils.py', 'utils.py'),
            ('/django/forms/widgets.py', 'widgets.py')
        ]
        for exp, got in zip(expected, fix_os_paths(f.choices)):
            self.assertEqual(exp[1], got[1])
            self.assertTrue(got[0].endswith(exp[0]))

    def test_filepathfield_4(self):
        path = os.path.abspath(upath(forms.__file__))
        path = os.path.dirname(path) + '/'
        f = FilePathField(path=path, recursive=True, match='^.*?\.py$')
        f.choices.sort()
        expected = [
            ('/django/forms/__init__.py', '__init__.py'),
            ('/django/forms/boundfield.py', 'boundfield.py'),
            ('/django/forms/extras/__init__.py', 'extras/__init__.py'),
            ('/django/forms/extras/widgets.py', 'extras/widgets.py'),
            ('/django/forms/fields.py', 'fields.py'),
            ('/django/forms/forms.py', 'forms.py'),
            ('/django/forms/formsets.py', 'formsets.py'),
            ('/django/forms/models.py', 'models.py'),
            ('/django/forms/utils.py', 'utils.py'),
            ('/django/forms/widgets.py', 'widgets.py')
        ]
        for exp, got in zip(expected, fix_os_paths(f.choices)):
            self.assertEqual(exp[1], got[1])
            self.assertTrue(got[0].endswith(exp[0]))

    def test_filepathfield_folders(self):
        path = os.path.abspath(os.path.join(upath(__file__), '..', '..')) + '/tests/filepath_test_files/'
        f = FilePathField(path=path, allow_folders=True, allow_files=False)
        f.choices.sort()
        expected = [
            ('/forms_tests/tests/filepath_test_files/directory', 'directory'),
        ]
        actual = fix_os_paths(f.choices)
        self.assertEqual(len(expected), len(actual))
        for exp, got in zip(expected, actual):
            self.assertEqual(exp[1], got[1])
            self.assertTrue(got[0].endswith(exp[0]))

        f = FilePathField(path=path, allow_folders=True, allow_files=True)
        f.choices.sort()
        expected = [
            ('/forms_tests/tests/filepath_test_files/.dot-file', '.dot-file'),
            ('/forms_tests/tests/filepath_test_files/1x1.bmp', '1x1.bmp'),
            ('/forms_tests/tests/filepath_test_files/1x1.png', '1x1.png'),
            ('/forms_tests/tests/filepath_test_files/directory', 'directory'),
            ('/forms_tests/tests/filepath_test_files/fake-image.jpg', 'fake-image.jpg'),
            ('/forms_tests/tests/filepath_test_files/real-text-file.txt', 'real-text-file.txt'),
        ]

        actual = fix_os_paths(f.choices)
        self.assertEqual(len(expected), len(actual))
        for exp, got in zip(expected, actual):
            self.assertEqual(exp[1], got[1])
            self.assertTrue(got[0].endswith(exp[0]))
