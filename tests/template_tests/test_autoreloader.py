from pathlib import Path
from unittest import mock

from thibaud.template import autoreload
from thibaud.test import SimpleTestCase, override_settings
from thibaud.test.utils import require_jinja2

ROOT = Path(__file__).parent.absolute()
EXTRA_TEMPLATES_DIR = ROOT / "templates_extra"


@override_settings(
    INSTALLED_APPS=["template_tests"],
    TEMPLATES=[
        {
            "BACKEND": "thibaud.template.backends.dummy.TemplateStrings",
            "APP_DIRS": True,
        },
        {
            "BACKEND": "thibaud.template.backends.thibaud.ThibaudTemplates",
            "DIRS": [EXTRA_TEMPLATES_DIR],
            "OPTIONS": {
                "context_processors": [
                    "thibaud.template.context_processors.request",
                ],
                "loaders": [
                    "thibaud.template.loaders.filesystem.Loader",
                    "thibaud.template.loaders.app_directories.Loader",
                ],
            },
        },
    ],
)
class TemplateReloadTests(SimpleTestCase):
    @mock.patch("thibaud.template.autoreload.reset_loaders")
    def test_template_changed(self, mock_reset):
        template_path = Path(__file__).parent / "templates" / "index.html"
        self.assertTrue(autoreload.template_changed(None, template_path))
        mock_reset.assert_called_once()

    @mock.patch("thibaud.template.autoreload.reset_loaders")
    def test_non_template_changed(self, mock_reset):
        self.assertIsNone(autoreload.template_changed(None, Path(__file__)))
        mock_reset.assert_not_called()

    @override_settings(
        TEMPLATES=[
            {
                "DIRS": [ROOT],
                "BACKEND": "thibaud.template.backends.thibaud.ThibaudTemplates",
            }
        ]
    )
    @mock.patch("thibaud.template.autoreload.reset_loaders")
    def test_non_template_changed_in_template_directory(self, mock_reset):
        self.assertIsNone(autoreload.template_changed(None, Path(__file__)))
        mock_reset.assert_not_called()

    @mock.patch("thibaud.forms.renderers.get_default_renderer")
    def test_form_template_reset_template_change(self, mock_renderer):
        template_path = Path(__file__).parent / "templates" / "index.html"
        self.assertIs(autoreload.template_changed(None, template_path), True)
        mock_renderer.assert_called_once()

    @mock.patch("thibaud.template.loaders.cached.Loader.reset")
    def test_form_template_reset_template_change_reset_call(self, mock_loader_reset):
        template_path = Path(__file__).parent / "templates" / "index.html"
        self.assertIs(autoreload.template_changed(None, template_path), True)
        mock_loader_reset.assert_called_once()

    @override_settings(FORM_RENDERER="thibaud.forms.renderers.TemplatesSetting")
    @mock.patch("thibaud.template.loaders.cached.Loader.reset")
    def test_form_template_reset_template_change_no_thibaudtemplates(
        self, mock_loader_reset
    ):
        template_path = Path(__file__).parent / "templates" / "index.html"
        self.assertIs(autoreload.template_changed(None, template_path), True)
        mock_loader_reset.assert_not_called()

    @mock.patch("thibaud.forms.renderers.get_default_renderer")
    def test_form_template_reset_non_template_change(self, mock_renderer):
        self.assertIsNone(autoreload.template_changed(None, Path(__file__)))
        mock_renderer.assert_not_called()

    def test_watch_for_template_changes(self):
        mock_reloader = mock.MagicMock()
        autoreload.watch_for_template_changes(mock_reloader)
        self.assertSequenceEqual(
            sorted(mock_reloader.watch_dir.call_args_list),
            [
                mock.call(ROOT / "templates", "**/*"),
                mock.call(ROOT / "templates_extra", "**/*"),
            ],
        )

    def test_get_template_directories(self):
        self.assertSetEqual(
            autoreload.get_template_directories(),
            {
                ROOT / "templates_extra",
                ROOT / "templates",
            },
        )

    @mock.patch("thibaud.template.loaders.base.Loader.reset")
    def test_reset_all_loaders(self, mock_reset):
        autoreload.reset_loaders()
        self.assertEqual(mock_reset.call_count, 2)

    @override_settings(
        TEMPLATES=[
            {
                "DIRS": [""],
                "BACKEND": "thibaud.template.backends.thibaud.ThibaudTemplates",
            }
        ]
    )
    def test_template_dirs_ignore_empty_path(self):
        self.assertEqual(autoreload.get_template_directories(), set())

    @override_settings(
        TEMPLATES=[
            {
                "DIRS": [
                    str(ROOT) + "/absolute_str",
                    "template_tests/relative_str",
                    Path("template_tests/relative_path"),
                ],
                "BACKEND": "thibaud.template.backends.thibaud.ThibaudTemplates",
            }
        ]
    )
    def test_template_dirs_normalized_to_paths(self):
        self.assertSetEqual(
            autoreload.get_template_directories(),
            {
                ROOT / "absolute_str",
                Path.cwd() / "template_tests/relative_str",
                Path.cwd() / "template_tests/relative_path",
            },
        )


@require_jinja2
@override_settings(INSTALLED_APPS=["template_tests"])
class Jinja2TemplateReloadTests(SimpleTestCase):
    def test_watch_for_template_changes(self):
        mock_reloader = mock.MagicMock()
        autoreload.watch_for_template_changes(mock_reloader)
        self.assertSequenceEqual(
            sorted(mock_reloader.watch_dir.call_args_list),
            [
                mock.call(ROOT / "templates", "**/*"),
            ],
        )

    def test_get_template_directories(self):
        self.assertSetEqual(
            autoreload.get_template_directories(),
            {
                ROOT / "templates",
            },
        )

    @mock.patch("thibaud.template.loaders.base.Loader.reset")
    def test_reset_all_loaders(self, mock_reset):
        autoreload.reset_loaders()
        self.assertEqual(mock_reset.call_count, 0)
