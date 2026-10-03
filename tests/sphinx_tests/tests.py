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
        self.srcdir = None
        self.builddir = None
        self.doctreedir = None


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

    skip_if_sphinx_unavailable = False

    def setUp(self):
        if self.skip_if_sphinx_unavailable and sphinx is None:
            self.skipTest("sphinx required")

    # Sphinx conf.py content used for build_sphinx().
    sphinx_conf = ""

    def build_sphinx(
        self,
        source,
        *,
        buildername="html",
        confoverrides=None,
        verbosity=0,
        warningiserror=False,
        working_dir=None,
    ):
        """Run sphinx-build on source and capture the result.

        Create a temporary directory with an index.rst from ``source`` and
        a conf.py from ``self.sphinx_conf``. (Leading whitespace is stripped
        from both using :func:`textwrap.dedent`.)

        Run the equivalent of ``sphinx-build`` in that directory and return
        a ``BuildSphinxResult`` object with the rendered files plus status
        (stdout) and warning (stderr) output.

        ``buildername``, ``confoverrides``, ``warningiserror``, and
        ``verbosity`` can be provided as documented for
        :class:`sphinx.application.Sphinx`.

        ``working_dir`` must be an existing directory (str or Path) if given.
        This is useful for reusing a doctree across builds. If not provided, a
        temporary directory will be created and cleaned up at the end of the
        test case.
        """
        if working_dir is None:
            tmpdir = tempfile.TemporaryDirectory()
            self.addCleanup(tmpdir.cleanup)
            srcdir = pathlib.Path(tmpdir.name)
        else:
            srcdir = pathlib.Path(working_dir)

        # Match builddir and doctreedir (-d) from docs/Makefile.
        builddir = srcdir / "_build"
        doctreedir = builddir / "doctrees"

        def write_file_if_changed(path, content):
            if not path.exists() or path.read_text() != content:
                path.write_text(content)

        write_file_if_changed(srcdir / "conf.py", textwrap.dedent(self.sphinx_conf))
        write_file_if_changed(srcdir / "index.rst", textwrap.dedent(source))
        status = io.StringIO()
        warning = io.StringIO()
        app = SphinxTestApp(
            buildername=buildername,
            srcdir=srcdir,
            builddir=builddir,
            doctreedir=doctreedir,
            confoverrides=confoverrides,
            verbosity=verbosity,
            warningiserror=warningiserror,
            status=status,
            warning=warning,
        )
        try:
            app.build()
        finally:
            # Reset Sphinx global state for the next build.
            app.cleanup()

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
        result.srcdir = srcdir
        result.builddir = builddir
        result.doctreedir = doctreedir
        return result
