import datetime
import os.path
import time
from pathlib import Path

from django.core.exceptions import ValidationError
from django.forms import FilePathField
from django.test import SimpleTestCase

PATH = os.path.dirname(os.path.abspath(__file__))


def fix_os_paths(x):
    if isinstance(x, str):
        return x.removeprefix(PATH).replace("\\", "/")
    elif isinstance(x, tuple):
        return tuple(fix_os_paths(list(x)))
    elif isinstance(x, list):
        return [fix_os_paths(y) for y in x]
    else:
        return x


class FilePathFieldTest(SimpleTestCase):
    expected_choices = [
        ("/filepathfield_test_dir/__init__.py", "__init__.py"),
        ("/filepathfield_test_dir/a.py", "a.py"),
        ("/filepathfield_test_dir/ab.py", "ab.py"),
        ("/filepathfield_test_dir/b.py", "b.py"),
        ("/filepathfield_test_dir/c/__init__.py", "__init__.py"),
        ("/filepathfield_test_dir/c/d.py", "d.py"),
        ("/filepathfield_test_dir/c/e.py", "e.py"),
        ("/filepathfield_test_dir/c/f/__init__.py", "__init__.py"),
        ("/filepathfield_test_dir/c/f/g.py", "g.py"),
        ("/filepathfield_test_dir/h/__init__.py", "__init__.py"),
        ("/filepathfield_test_dir/j/__init__.py", "__init__.py"),
    ]
    path = os.path.join(PATH, "filepathfield_test_dir") + "/"

    def assertChoices(self, field, expected_choices):
        self.assertEqual(fix_os_paths(field.choices), expected_choices)

    def test_fix_os_paths(self):
        self.assertEqual(fix_os_paths(self.path), ("/filepathfield_test_dir/"))

    def test_nonexistent_path(self):
        with self.assertRaisesMessage(FileNotFoundError, "nonexistent"):
            FilePathField(path="nonexistent")

    def test_no_options(self):
        f = FilePathField(path=self.path)
        expected = [
            ("/filepathfield_test_dir/README", "README"),
        ] + self.expected_choices[:4]
        self.assertChoices(f, expected)

    def test_clean(self):
        f = FilePathField(path=self.path)
        msg = "'Select a valid choice. a.py is not one of the available choices.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("a.py")
        self.assertEqual(
            fix_os_paths(f.clean(self.path + "a.py")), "/filepathfield_test_dir/a.py"
        )

    def test_match(self):
        f = FilePathField(path=self.path, match=r"^.*?\.py$")
        self.assertChoices(f, self.expected_choices[:4])

    def test_recursive(self):
        f = FilePathField(path=self.path, recursive=True, match=r"^.*?\.py$")
        expected = [
            ("/filepathfield_test_dir/__init__.py", "__init__.py"),
            ("/filepathfield_test_dir/a.py", "a.py"),
            ("/filepathfield_test_dir/ab.py", "ab.py"),
            ("/filepathfield_test_dir/b.py", "b.py"),
            ("/filepathfield_test_dir/c/__init__.py", "c/__init__.py"),
            ("/filepathfield_test_dir/c/d.py", "c/d.py"),
            ("/filepathfield_test_dir/c/e.py", "c/e.py"),
            ("/filepathfield_test_dir/c/f/__init__.py", "c/f/__init__.py"),
            ("/filepathfield_test_dir/c/f/g.py", "c/f/g.py"),
            ("/filepathfield_test_dir/h/__init__.py", "h/__init__.py"),
            ("/filepathfield_test_dir/j/__init__.py", "j/__init__.py"),
        ]
        self.assertChoices(f, expected)

    def test_allow_folders(self):
        f = FilePathField(path=self.path, allow_folders=True, allow_files=False)
        self.assertChoices(
            f,
            [
                ("/filepathfield_test_dir/c", "c"),
                ("/filepathfield_test_dir/h", "h"),
                ("/filepathfield_test_dir/j", "j"),
            ],
        )

    def test_recursive_no_folders_or_files(self):
        f = FilePathField(
            path=self.path, recursive=True, allow_folders=False, allow_files=False
        )
        self.assertChoices(f, [])

    def test_recursive_folders_without_files(self):
        f = FilePathField(
            path=self.path, recursive=True, allow_folders=True, allow_files=False
        )
        self.assertChoices(
            f,
            [
                ("/filepathfield_test_dir/c", "c"),
                ("/filepathfield_test_dir/h", "h"),
                ("/filepathfield_test_dir/j", "j"),
                ("/filepathfield_test_dir/c/f", "c/f"),
            ],
        )

    def test_cache_true(self):
        insulated_path = Path(self.path).parent / "filepathfield_test_cache_true_dir"
        f = FilePathField(path=insulated_path, cache=True)
        # Then add a new file
        new_file = insulated_path / "z.py"
        new_file.touch()
        # Check that z.py is not a choice before calling refresh_cache()
        expected = [
            ("/filepathfield_test_cache_true_dir/README", "README"),
            ("/filepathfield_test_cache_true_dir/__init__.py", "__init__.py"),
            ("/filepathfield_test_cache_true_dir/a.py", "a.py"),
            ("/filepathfield_test_cache_true_dir/ab.py", "ab.py"),
            ("/filepathfield_test_cache_true_dir/b.py", "b.py"),
        ]
        try:
            self.assertChoices(f, expected)
            # Check that z.py is a not choice after calling refresh_cache()
            # (which should do nothing since the cache is not invalidated
            # when set to True)
            f.refresh_cache()
            self.assertChoices(f, expected)
        finally:
            # Check that z.py is not a choice before calling refresh_cache()
            new_file.unlink()

    def test_cache_false(self):
        insulated_path = Path(self.path).parent / "filepathfield_test_cache_false_dir"
        f = FilePathField(path=insulated_path, cache=False)
        # Then add a new file
        new_file = insulated_path / "z.py"
        new_file.touch()
        # Check that z.py is not a choice before calling refresh_cache()
        expected = [
            ("/filepathfield_test_cache_false_dir/README", "README"),
            ("/filepathfield_test_cache_false_dir/__init__.py", "__init__.py"),
            ("/filepathfield_test_cache_false_dir/a.py", "a.py"),
            ("/filepathfield_test_cache_false_dir/ab.py", "ab.py"),
            ("/filepathfield_test_cache_false_dir/b.py", "b.py"),
        ]
        try:
            self.assertChoices(f, expected)
            # Check that z.py is a choice after calling refresh_cache()
            f.refresh_cache()
            expected.append(("/filepathfield_test_cache_false_dir/z.py", "z.py"))
            self.assertChoices(f, expected)
        finally:
            # delete z.py even if test fails
            new_file.unlink()

    def test_cache_timedelta(self):
        insulated_path = (
            Path(self.path).parent / "filepathfield_test_cache_timedelta_dir"
        )
        f = FilePathField(path=insulated_path, cache=datetime.timedelta(seconds=5))
        # Then add a new file
        new_file = insulated_path / "z.py"
        new_file.touch()
        # Check that z.py is not a choice before calling refresh_cache()
        expected = [
            ("/filepathfield_test_cache_timedelta_dir/README", "README"),
            ("/filepathfield_test_cache_timedelta_dir/__init__.py", "__init__.py"),
            ("/filepathfield_test_cache_timedelta_dir/a.py", "a.py"),
            ("/filepathfield_test_cache_timedelta_dir/ab.py", "ab.py"),
            ("/filepathfield_test_cache_timedelta_dir/b.py", "b.py"),
        ]
        try:
            self.assertChoices(f, expected)
            # Check that z.py is a not choice after calling refresh_cache()
            # within the timedelta
            f.refresh_cache()
            self.assertChoices(f, expected)
            # Check that z.py is a choice after calling refresh_cache()
            # after the timedelta
            time.sleep(5)
            f.refresh_cache()
            expected.append(("/filepathfield_test_cache_timedelta_dir/z.py", "z.py"))
            self.assertChoices(f, expected)
        finally:
            # delete z.py even if test fails
            new_file.unlink()
