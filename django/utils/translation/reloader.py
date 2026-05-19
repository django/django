from pathlib import Path

from django.apps import apps
from django.utils.autoreload import is_django_module


def watch_for_translation_changes(sender, **kwargs):
    """Register file watchers for .mo files in potential locale paths."""
    from django.conf import settings

    if settings.USE_I18N:
        directories = [Path("locale")]
        directories.extend(
            Path(config.path) / "locale"
            for config in apps.get_app_configs()
            if not is_django_module(config.module)
        )
        directories.extend(Path(p) for p in settings.LOCALE_PATHS)
        for path in directories:
            sender.watch_dir(path, "**/*.mo")


def translation_file_changed(sender, file_path, **kwargs):
    """Notify the active translation backend that a .mo file was modified."""
    if file_path.suffix == ".mo":
        from django.utils.translation import _trans

        _trans.on_translation_files_changed(sender, file_path, **kwargs)
        return True
