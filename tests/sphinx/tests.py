from django.test import SimpleTestCase
from django.test.sphinx_utils import github_linkcode_resolve
from django.test.testdata import github_linkcode_module


class SphinxTests(SimpleTestCase):

    MODULE_URL = (
        "https://github.com/django/django/blob/main/"
        "django/test/testdata/github_linkcode_module.py"
    )

    def test_unspecified_domain(self):
        domain = "unspecified"
        info = {}
        self.assertIsNone(github_linkcode_resolve(domain, info))

    def test_unspecified_info(self):
        domain = "py"
        info = {}
        self.assertIsNone(github_linkcode_resolve(domain, info))

    def test_link_to_class(self):
        domain = "py"
        info = {}
        info["module"] = github_linkcode_module.__name__
        info["fullname"] = "MyClass"
        self.assertIn(
            github_linkcode_resolve(domain, info),
            [
                self.MODULE_URL + "#L7",
                self.MODULE_URL + "#L8",
            ],
        )

    def test_link_to_def(self):
        domain = "py"
        info = {}
        info["module"] = github_linkcode_module.__name__
        info["fullname"] = "my_toplevel_def"
        self.assertIn(
            github_linkcode_resolve(domain, info),
            [
                self.MODULE_URL + "#L19",
                self.MODULE_URL + "#L20",
            ],
        )

    def test_link_to_cached_property(self):
        domain = "py"
        info = {}
        info["module"] = github_linkcode_module.__name__
        info["fullname"] = "MyClass.my_cached_property"
        self.assertIn(
            github_linkcode_resolve(domain, info),
            [
                self.MODULE_URL + "#L14",
                self.MODULE_URL + "#L15",
            ],
        )
