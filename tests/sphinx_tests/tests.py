import io
import pathlib
import sys
import tempfile
import textwrap

from django.test import SimpleTestCase

try:
    import sphinx
    from sphinx.testing.util import SphinxTestApp
except ImportError:
    sphinx = None


class BuildSphinxResult:
    def __init__(self):
        self.files = {}
        self.status = ""
        self.warning = ""


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

    # Sphinx conf.py content used for build_sphinx().
    sphinx_conf = ""

    def build_sphinx(
        self,
        source,
        *,
        buildername="html",
        confoverrides=None,
        verbosity=0,
    ):
        """Run sphinx-build on source and capture the result.

        Create a temporary directory with an index.rst from ``source`` and
        a conf.py from ``self.sphinx_conf``. (Leading whitespace is stripped
        from both using :func:`textwrap.dedent`.)

        Run the equivalent of ``sphinx-build`` in that directory and return
        a ``BuildSphinxResult`` object with the rendered files plus status
        (stdout) and warning (stderr) output.

        ``buildername``, ``confoverrides``, and ``verbosity`` can be provided
        as documented for :class:`sphinx.application.Sphinx`.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            srcdir = pathlib.Path(tmpdir)
            (srcdir / "conf.py").write_text(textwrap.dedent(self.sphinx_conf))
            (srcdir / "index.rst").write_text(textwrap.dedent(source))
            status = io.StringIO()
            warning = io.StringIO()
            app = SphinxTestApp(
                buildername=buildername,
                srcdir=srcdir,
                confoverrides=confoverrides,
                verbosity=verbosity,
                status=status,
                warning=warning,
            )
            try:
                app.build()
                result = BuildSphinxResult()
                for f in app.outdir.rglob("*"):
                    if f.is_file():
                        rel = str(f.relative_to(app.outdir))
                        try:
                            result.files[rel] = f.read_text(encoding="utf-8")
                        except UnicodeDecodeError:
                            result.files[rel] = f.read_bytes()
                result.status = status.getvalue()
                result.warning = warning.getvalue()
                return result
            finally:
                app.cleanup()
