import tempfile

from .tests import SimpleSphinxTestCase


class DjangoDocsTestCase(SimpleSphinxTestCase):
    skip_if_sphinx_unavailable = True
    sphinx_conf = "extensions = ['djangodocs']"


class DjangoDocsExtensionTests(DjangoDocsTestCase):

    maxDiff = None

    def test_crossrefs(self):
        crossref_types = [
            # directive, role, example name, index description.
            ("setting", "setting", "DEBUG", "setting"),
            ("templatetag", "ttag", "cycle", "template tag"),
            (
                "templatefilter",
                "tfilter",
                "date",
                "template filter",
            ),
            (
                "fieldlookup",
                "lookup",
                "exact",
                "field lookup type",
            ),
        ]
        for directive, role, name, index_desc in crossref_types:
            with self.subTest(directive=directive, role=role):
                result = self.build_sphinx(f"""
                    .. {directive}:: {name}

                    Description of {name}.

                    See :{role}:`{name}`.
                    """)
                html = result.files["index.html"]
                genindex = result.files["genindex.html"]
                self.assertEqual(result.warning, "")
                id = f"std-{directive}-{name}"
                self.assertInHTML(
                    f'<p id="{id}">Description of {name}.</p>',
                    html,
                )
                self.assertInHTML(
                    f'<a class="reference internal" href="#{id}">'
                    f'<code class="xref std std-{role} docutils literal notranslate">'
                    f'<span class="pre">{name}</span></code></a>',
                    html,
                )
                # Appears in the index under both name and index_desc.
                self.assertInHTML(
                    f'<li>{name} <ul><li><a href="index.html#{id}">{index_desc}</a>'
                    "</li></ul></li>",
                    genindex,
                )
                self.assertInHTML(
                    f'<li>{index_desc} <ul><li><a href="index.html#{id}">{name}</a>'
                    "</li></ul></li>",
                    genindex,
                )

    def test_automatic_section_ids(self):
        result = self.build_sphinx("""
            First Section
            =============

            Second Section
            ==============

            Nested Section
            --------------
            """)
        html = result.files["index.html"]
        self.assertIn('<section id="s-first-section">', html)
        self.assertIn('<section id="s-second-section">', html)
        self.assertIn('<section id="s-nested-section">', html)

    def test_django_admin_directive(self):
        result = self.build_sphinx("""
            .. django-admin:: check [app_label ...]

            Description of check command.

            .. django-admin-option:: --tag TAG

            Tag option description.

            See :djadmin:`check` and :option:`check --tag`.
            """)
        self.assertEqual(result.warning, "")
        html = result.files["index.html"]

        # .. django-admin::
        self.assertIn('<dl class="std django-admin">', html)
        self.assertIn('<dt class="sig sig-object std" id="django-admin-check">', html)
        self.assertInHTML(
            '<span class="sig-name descname"><span class="pre">django-admin</span>'
            ' <span class="pre">check</span> <span class="pre">[app_label</span>'
            ' <span class="pre">...]</span></span>',
            html,
        )

        # .. django-admin-option::
        self.assertIn('<dl class="django-admin-option">', html)
        self.assertIn('<dt class="sig sig-object" id="cmdoption-check-tag">', html)
        self.assertInHTML(
            '<span class="sig-name descname"><span class="pre">--tag</span></span>'
            '<span class="sig-prename descclassname">'
            '<span class="pre">TAG</span></span>',
            html,
        )

        # References.
        self.assertInHTML(
            '<a class="reference internal" href="#django-admin-check">'
            '<code class="xref std std-djadmin docutils literal notranslate">'
            '<span class="pre">check</span></code></a>',
            html,
        )
        self.assertInHTML(
            '<a class="reference internal" href="#cmdoption-check-tag">'
            '<code class="xref std std-option docutils literal notranslate">'
            '<span class="pre">check</span> <span class="pre">--tag</span></code></a>',
            html,
        )

        # Index entries.
        genindex = result.files["genindex.html"]
        self.assertIn("check", genindex)
        self.assertIn("django-admin command", genindex)

    def test_default_role_error(self):
        result = self.build_sphinx(
            "Some `single backticks` text.",
            confoverrides={"default_role": "default-role-error"},
        )
        self.assertIn(
            "Default role used (`single backticks`): `single backticks`", result.warning
        )
        self.assertIn(
            "Did you mean to use two backticks for ``code``, or miss an underscore"
            " for a `link`_ ?",
            result.warning,
        )


class ConsoleDirectiveTests(DjangoDocsTestCase):
    def test_html_output_tabs(self):
        result = self.build_sphinx("""
            .. console::

                $ ./manage.py runserver
            """)
        self.assertEqual(result.warning, "")
        html = result.files["index.html"]
        self.assertIn('<div class="console-block" id="console-block-0">', html)

        # Radio buttons.
        self.assertInHTML(
            '<input class="c-tab-unix" id="c-tab-0-unix" type="radio" name="console-0"'
            " checked>",
            html,
        )
        self.assertInHTML(
            '<label for="c-tab-0-unix"><span>Unix/macOS</span></label>', html
        )
        self.assertInHTML(
            '<input class="c-tab-win" id="c-tab-0-win" type="radio" name="console-0">',
            html,
        )
        self.assertInHTML('<label for="c-tab-0-win"><span>Windows</span></label>', html)

        # Tab content.
        self.assertInHTML(
            """
            <section class="c-content-unix" id="c-content-0-unix">
                <div class="highlight-console notranslate"><div class="highlight"><pre>
                    <span></span><span class="gp">$ </span>./manage.py
                    <span class="w"> </span>runserver
                </pre></div></div>
            </section>
            """,
            html,
        )
        self.assertInHTML(
            """
            <section class="c-content-win" id="c-content-0-win">
                <div class="highlight-doscon notranslate"><div class="highlight"><pre>
                    <span></span><span class="gp">...\\&gt;</span> manage.py runserver
                </pre></div></div>
            </section>
            """,
            html,
        )

    def test_multiple_blocks_have_unique_ids(self):
        result = self.build_sphinx("""
            .. console::

                $ ./manage.py runserver

            .. console::

                $ ./manage.py migrate
            """)
        self.assertEqual(result.warning, "")
        html = result.files["index.html"]

        # First console block.
        self.assertIn('<div class="console-block" id="console-block-0">', html)
        self.assertInHTML(
            '<input class="c-tab-unix" id="c-tab-0-unix" type="radio" name="console-0"'
            " checked>",
            html,
        )
        self.assertInHTML(
            '<input class="c-tab-win" id="c-tab-0-win" type="radio" name="console-0">',
            html,
        )
        self.assertIn('<section class="c-content-unix" id="c-content-0-unix">', html)
        self.assertIn('<section class="c-content-win" id="c-content-0-win">', html)

        # Second console block.
        self.assertIn('<div class="console-block" id="console-block-1">', html)
        self.assertInHTML(
            '<input class="c-tab-unix" id="c-tab-1-unix" type="radio" name="console-1"'
            " checked>",
            html,
        )
        self.assertInHTML(
            '<input class="c-tab-win" id="c-tab-1-win" type="radio" name="console-1">',
            html,
        )
        self.assertIn('<section class="c-content-unix" id="c-content-1-unix">', html)
        self.assertIn('<section class="c-content-win" id="c-content-1-win">', html)

    def test_class_and_name_options(self):
        result = self.build_sphinx("""
            .. console::
                :class: custom-class
                :name: custom-name

                $ ./manage.py runserver
            """)
        self.assertEqual(result.warning, "")
        html = result.files["index.html"]
        # The class is attached to both tabs' content blocks. The name is only
        # attached to the first. (Arguably a specified name should be hoisted
        # to the wrapper div.console-block, replacing the generated id there.
        # The current implementation doesn't do that, but this test is not
        # meant to discourage that change in the future.)
        self.assertIn(
            '<div class="custom-class highlight-console notranslate" id="custom-name">',
            html,
        )
        self.assertIn('<div class="custom-class highlight-doscon notranslate">', html)
        # Ensure id is unique.
        self.assertEqual(html.count("custom-name"), 1)

    def test_no_tabs_when_no_win_command(self):
        result = self.build_sphinx("""
            .. console::

                Plain text without shell commands.
            """)
        html = result.files["index.html"]
        self.assertNotIn("console-block", html)
        self.assertNotIn("c-tab-unix", html)
        self.assertIn("Plain text without shell commands.", html)

    def test_no_tabs_in_non_html_output(self):
        source = """
            .. console::

                $ ./manage.py runserver
            """

        with self.subTest(buildername="text"):
            result = self.build_sphinx(source, buildername="text")
            text_content = result.files["index.txt"]
            self.assertIn("$ ./manage.py runserver", text_content)
            self.assertNotIn("console-block", text_content)
            self.assertNotIn(r"...\>", text_content)

        with self.subTest(buildername="latex"):
            result = self.build_sphinx(
                source,
                buildername="latex",
                confoverrides={
                    "latex_documents": [
                        ("index", "output.tex", "Title", "Author", "manual"),
                    ]
                },
            )
            latex_content = result.files["output.tex"]
            # "PYGZdl" is a Pygments-generated "$" for LaTeX.
            self.assertRegex(latex_content, r"PYGZdl.*\./manage\.py.*runserver")
            self.assertNotIn("console-block", latex_content)
            self.assertNotIn(r"...\>", latex_content)

        with self.subTest(buildername="man"):
            result = self.build_sphinx(
                source,
                buildername="man",
                confoverrides={
                    "man_pages": [("index", "output", "Description", ["Author"], 1)]
                },
            )
            man_content = result.files["output.1"]
            self.assertIn("$ ./manage.py runserver", man_content)
            self.assertNotIn("console-block", man_content)
            self.assertNotIn(r"...\>", man_content)

        with self.subTest(buildername="epub"):
            # epub actually is a variant of html, but cannot support tabs.
            result = self.build_sphinx(source, buildername="epub")
            epub_content = result.files["index.xhtml"]
            # No tab controls are rendered.
            self.assertNotIn("console-block", epub_content)
            self.assertNotIn("input", epub_content)
            self.assertNotIn("label", epub_content)
            self.assertNotIn("c-tab", epub_content)
            # The content is still included and is highlighted as console.
            self.assertIn("highlight-console", epub_content)
            self.assertInHTML(
                '<pre><span></span><span class="gp">$ </span>'
                './manage.py<span class="w"> </span>runserver</pre>',
                epub_content,
            )
            # No win content is rendered.
            self.assertNotIn("highlight-doscon", epub_content)
            self.assertNotIn(r"...\>", epub_content)

    def test_doctree_is_cacheable(self):
        # The console directive must not create a builder-specific doctree,
        # which would cause inconsistent outputs when reusing the doctreedir.
        source = """
            .. console::

                $ ./manage.py runserver
            """
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.build_sphinx(source, working_dir=tmpdir, buildername="text")
            text_content = result.files["index.txt"]
            result = self.build_sphinx(source, working_dir=tmpdir, buildername="html")
            html_content = result.files["index.html"]
        self.assertNotIn("console-block", text_content)
        self.assertIn("console-block", html_content)


class SourcefileRoleTests(DjangoDocsTestCase):
    def render_html(self, source, *, version="6.2", next_version="6.2"):
        result = self.build_sphinx(
            source,
            confoverrides={
                "version": version,
                "django_next_version": next_version,
            },
        )
        self.assertEqual(result.warning, "")
        return result.files["index.html"]

    def test_sourcefile_uses_main_branch(self):
        html = self.render_html(":sourcefile:`django/forms/forms.py`")
        self.assertInHTML(
            """
            <a class="reference external"
                href="https://github.com/django/django/blob/main/django/forms/forms.py">
                <code class="docutils literal notranslate">
                    <span class="pre">django/forms/forms.py</span>
                </code>
            </a>
            """,
            html,
        )

    def test_sourcefile_uses_stable_branch(self):
        html = self.render_html(
            ":sourcefile:`django/forms/forms.py`", version="6.0", next_version="6.2"
        )
        url = "https://github.com/django/django/blob/stable/6.0.x/django/forms/forms.py"
        self.assertIn(f'href="{url}"', html)

    def test_sourcefile_supports_explicit_title(self):
        html = self.render_html(":sourcefile:`explicit_title <django/forms/forms.py>`")
        url = "https://github.com/django/django/blob/main/django/forms/forms.py"
        self.assertIn(f'href="{url}"', html)
        self.assertIn('<span class="pre">explicit_title</span>', html)
