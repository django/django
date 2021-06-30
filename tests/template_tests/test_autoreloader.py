from pathlib import Path
from unittest import mock

from mango.template import autoreload
from mango.test import SimpleTestCase, override_settings
from mango.test.utils import require_jinja2

ROOT = Path(__file__).parent.absolute()
EXTRA_TEMPLATES_DIR = ROOT / "templates_extra"


@override_settings(
    INSTALLED_APPS=['template_tests'],
    TEMPLATES=[{
        'BACKEND': 'mango.template.backends.dummy.TemplateStrings',
        'APP_DIRS': True,
    }, {
        'BACKEND': 'mango.template.backends.mango.MangoTemplates',
        'DIRS': [EXTRA_TEMPLATES_DIR],
        'OPTIONS': {
            'context_processors': [
                'mango.template.context_processors.request',
            ],
            'loaders': [
                'mango.template.loaders.filesystem.Loader',
                'mango.template.loaders.app_directories.Loader',
            ]
        },
    }])
class TemplateReloadTests(SimpleTestCase):
    @mock.patch('mango.template.autoreload.reset_loaders')
    def test_template_changed(self, mock_reset):
        template_path = Path(__file__).parent / 'templates' / 'index.html'
        self.assertTrue(autoreload.template_changed(None, template_path))
        mock_reset.assert_called_once()

    @mock.patch('mango.template.autoreload.reset_loaders')
    def test_non_template_changed(self, mock_reset):
        self.assertIsNone(autoreload.template_changed(None, Path(__file__)))
        mock_reset.assert_not_called()

    def test_watch_for_template_changes(self):
        mock_reloader = mock.MagicMock()
        autoreload.watch_for_template_changes(mock_reloader)
        self.assertSequenceEqual(
            sorted(mock_reloader.watch_dir.call_args_list),
            [
                mock.call(ROOT / 'templates', '**/*'),
                mock.call(ROOT / 'templates_extra', '**/*')
            ]
        )

    def test_get_template_directories(self):
        self.assertSetEqual(
            autoreload.get_template_directories(),
            {
                ROOT / 'templates_extra',
                ROOT / 'templates',
            }
        )

    @mock.patch('mango.template.loaders.base.Loader.reset')
    def test_reset_all_loaders(self, mock_reset):
        autoreload.reset_loaders()
        self.assertEqual(mock_reset.call_count, 2)

    @override_settings(
        TEMPLATES=[{
            'DIRS': [
                str(ROOT) + '/absolute_str',
                'template_tests/relative_str',
                Path('template_tests/relative_path'),
            ],
            'BACKEND': 'mango.template.backends.mango.MangoTemplates',
        }]
    )
    def test_template_dirs_normalized_to_paths(self):
        self.assertSetEqual(
            autoreload.get_template_directories(),
            {
                ROOT / 'absolute_str',
                Path.cwd() / 'template_tests/relative_str',
                Path.cwd() / 'template_tests/relative_path',
            }
        )


@require_jinja2
@override_settings(INSTALLED_APPS=['template_tests'])
class Jinja2TemplateReloadTests(SimpleTestCase):
    def test_watch_for_template_changes(self):
        mock_reloader = mock.MagicMock()
        autoreload.watch_for_template_changes(mock_reloader)
        self.assertSequenceEqual(
            sorted(mock_reloader.watch_dir.call_args_list),
            [
                mock.call(ROOT / 'templates', '**/*'),
            ]
        )

    def test_get_template_directories(self):
        self.assertSetEqual(
            autoreload.get_template_directories(),
            {
                ROOT / 'templates',
            }
        )

    @mock.patch('mango.template.loaders.base.Loader.reset')
    def test_reset_all_loaders(self, mock_reset):
        autoreload.reset_loaders()
        self.assertEqual(mock_reset.call_count, 0)
