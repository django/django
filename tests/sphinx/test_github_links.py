import pathlib
import sys

from django.test import SimpleTestCase


class GitHubLinkTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        # The file implementing the code under test cannot be imported through
        # standard means, so include its parent in the pythonpath for the 
        # duration of the tests.
        cls.ext_path = str((pathlib.Path(__file__).parents[2] / "docs/_ext").resolve())
        sys.path.insert(0, cls.ext_path)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(cls.ext_path)
        sys.modules.pop("github_links", None)

    @property
    def github_links(self):
        # The import must happen after setUpClass, so it can't be imported at
        # the top of the file. A property is used to avoid the import in every test.
        # Linters/IDEs may not be able to detect this as a valid import.
        import github_links

        return github_links

    def test_code_locator(self):
        locator = self.github_links.CodeLocator.from_code(
            """
from a import b, c
from .d import e, f as g

def h():
    pass

class I:
    def j(self):
        pass"""
        )

        self.assertEqual(locator.node_line_numbers, {"h": 5, "I": 8, "I.j": 9})
        self.assertEqual(locator.import_locations, {"b": "a", "c": "a", "e": ".d"})

    def test_module_name_to_file_path_package(self):
        self.assertTrue(
            str(self.github_links.module_name_to_file_path("django")).endswith(
                "/django/__init__.py"
            )
        )

    def test_module_name_to_file_path_module(self):
        self.assertTrue(
            str(
                self.github_links.module_name_to_file_path("django.shortcuts")
            ).endswith("/django/shortcuts.py")
        )

    def test_get_path_and_line_class(self):
        path, line = self.github_links.get_path_and_line(
            module="tests.sphinx.testdata.package.module", fullname="MyClass"
        )

        self.assertEqual(
            "/".join(path.parts[-5:]), "tests/sphinx/testdata/package/module.py"
        )
        self.assertEqual(line, 15)

    def test_get_path_and_line_func(self):
        path, line = self.github_links.get_path_and_line(
            module="tests.sphinx.testdata.package.module", fullname="my_function"
        )

        self.assertEqual(
            "/".join(path.parts[-5:]), "tests/sphinx/testdata/package/module.py"
        )
        self.assertEqual(line, 27)

    def test_get_path_and_line_method(self):
        path, line = self.github_links.get_path_and_line(
            module="tests.sphinx.testdata.package.module", fullname="MyClass.my_method"
        )

        self.assertEqual(
            "/".join(path.parts[-5:]), "tests/sphinx/testdata/package/module.py"
        )
        self.assertEqual(line, 19)

    def test_get_path_and_line_cached_property(self):
        path, line = self.github_links.get_path_and_line(
            module="tests.sphinx.testdata.package.module",
            fullname="MyClass.my_cached_property",
        )

        self.assertEqual(
            "/".join(path.parts[-5:]), "tests/sphinx/testdata/package/module.py"
        )
        self.assertEqual(line, 23)

    def test_get_path_and_line_forwarded_import(self):
        path, line = self.github_links.get_path_and_line(
            module="tests.sphinx.testdata.package.module", fullname="MyOtherClass"
        )

        self.assertEqual(
            "/".join(path.parts[-5:]), "tests/sphinx/testdata/package/other_module.py"
        )
        self.assertEqual(line, 1)

    def test_get_path_and_line_forwarded_import_module(self):
        path, line = self.github_links.get_path_and_line(
            module="tests.sphinx.testdata.package.module",
            fullname="other_module.MyOtherClass",
        )

        self.assertEqual(
            "/".join(path.parts[-5:]), "tests/sphinx/testdata/package/other_module.py"
        )
        self.assertEqual(line, 1)

    def test_get_branch_stable(self):
        branch = self.github_links.get_branch(version="2.2", next_version="3.2")
        self.assertEqual(branch, "stable/2.2.x")

    def test_get_branch_latest(self):
        branch = self.github_links.get_branch(version="3.2", next_version="3.2")
        self.assertEqual(branch, "main")

    def test_github_linkcode_resolve_unspecified_domain(self):
        domain = "unspecified"
        info = {}
        self.assertIsNone(
            self.github_links.github_linkcode_resolve(
                domain, info, version="3.2", next_version="3.2"
            )
        )

    def test_github_linkcode_resolve_unspecified_info(self):
        domain = "py"
        info = {}
        self.assertIsNone(
            self.github_links.github_linkcode_resolve(
                domain, info, version="3.2", next_version="3.2"
            )
        )

    def test_github_linkcode_resolve_not_found(self):
        info = {
            "module": "foo.bar.baz.hopefully_non_existant_module",
            "fullname": "MyClass",
        }
        self.assertIsNone(
            self.github_links.github_linkcode_resolve(
                "py", info, version="3.2", next_version="3.2"
            )
        )

    def test_github_linkcode_resolve_link_to_object(self):
        info = {
            "module": "tests.sphinx.testdata.package.module",
            "fullname": "MyClass",
        }
        self.assertEqual(
            self.github_links.github_linkcode_resolve(
                "py", info, version="3.2", next_version="3.2"
            ),
            "https://github.com/django/django/blob/main/tests/sphinx/"
            "testdata/package/module.py#L15",
        )

    def test_github_linkcode_resolve_link_to_class_older_version(self):
        info = {
            "module": "tests.sphinx.testdata.package.module",
            "fullname": "MyClass",
        }
        self.assertEqual(
            self.github_links.github_linkcode_resolve(
                "py", info, version="2.2", next_version="3.2"
            ),
            "https://github.com/django/django/blob/stable/2.2.x/tests/sphinx/"
            "testdata/package/module.py#L15",
        )
