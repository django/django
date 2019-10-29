from pathlib import Path

from asgiref.local import Local

from django.apps import apps


def watch_for_translation_changes(sender, **kwargs):
    """Register file watchers for .mo files in potential locale paths."""
    from django.conf import settings

    if settings.USE_I18N:
        directories = [Path('locale')]
        directories.extend(Path(config.path) / 'locale' for config in apps.get_app_configs())
        directories.extend(Path(p) for p in settings.LOCALE_PATHS)
        for path in directories:
            sender.watch_dir(path, '**/*.mo')


def translation_file_changed(sender, file_path, **kwargs):
    """Clear the internal translations cache if a .mo file is modified."""
    if file_path.suffix == '.mo':
        import gettext
        from django.utils.translation import trans_real
        gettext._translations = {}
        trans_real._translations = {}
        trans_real._default = None
        trans_real._active = Local()
        return True
