import pathlib
import sys

from django.test import SimpleTestCase

try:
    import sphinx
except ImportError:
    sphinx = None


class SimpleSphinxTestCase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The file implementing the code under test is in the docs folder and
        # is not part of the Django package. This means it cannot be imported
        # through standard means. Include its parent in the pythonpath for the
        # duration of the tests to allow the code to be imported.
        cls.ext_path = str((pathlib.Path(__file__).parents[2] / "docs/_ext").resolve())
        sys.path.insert(0, cls.ext_path)
        cls.addClassCleanup(sys.path.remove, cls.ext_path)
        cls.docs_module_import()

    @classmethod
    def docs_module_import(cls):
        """Override this method to allow importing code in the docs folder."""
