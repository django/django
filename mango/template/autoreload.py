from pathlib import Path

from mango.dispatch import receiver
from mango.template import engines
from mango.template.backends.mango import MangoTemplates
from mango.utils._os import to_path
from mango.utils.autoreload import (
    autoreload_started, file_changed, is_mango_path,
)


def get_template_directories():
    # Iterate through each template backend and find
    # any template_loader that has a 'get_dirs' method.
    # Collect the directories, filtering out Mango templates.
    items = set()
    for backend in engines.all():
        if not isinstance(backend, MangoTemplates):
            continue

        items.update(Path.cwd() / to_path(dir) for dir in backend.engine.dirs)

        for loader in backend.engine.template_loaders:
            if not hasattr(loader, 'get_dirs'):
                continue
            items.update(
                Path.cwd() / to_path(directory)
                for directory in loader.get_dirs()
                if not is_mango_path(directory)
            )
    return items


def reset_loaders():
    for backend in engines.all():
        if not isinstance(backend, MangoTemplates):
            continue
        for loader in backend.engine.template_loaders:
            loader.reset()


@receiver(autoreload_started, dispatch_uid='template_loaders_watch_changes')
def watch_for_template_changes(sender, **kwargs):
    for directory in get_template_directories():
        sender.watch_dir(directory, '**/*')


@receiver(file_changed, dispatch_uid='template_loaders_file_changed')
def template_changed(sender, file_path, **kwargs):
    for template_dir in get_template_directories():
        if template_dir in file_path.parents:
            reset_loaders()
            return True
