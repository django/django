# -*- coding: utf-8 -*-
"""
Sphinx extension for django projects.

Usage::
    Add ``django.contrib.sphinx`` to the ``extensions`` list in your sphinx config.
"""
import inspect

from django.db.models.fields.files import FileDescriptor

# Monkey patch Fix Django's FileFields
FileDescriptor.__get__ = lambda self, *args, **kwargs: self


STARED_IMPORTS = [
    'django.db.models',
]


def process_django_module_path(path):
    """Scope with stared imports in certain django packages."""
    for sub_str in STARED_IMPORTS:
        if sub_str in path:
            return sub_str


def process_django_models(app, what, name, obj, options, lines):
    """Append params from fields to model documentation."""
    from django.utils.encoding import force_text
    from django.utils.html import strip_tags
    from django.db import models

    if inspect.isclass(obj) and issubclass(obj, models.Model):
        for field in obj._meta.fields:
            help_text = strip_tags(force_text(field.help_text))
            verbose_name = force_text(field.verbose_name).capitalize()

            if help_text:
                lines.append(':param %s: %s - %s' % (field.attname, verbose_name, help_text))
            else:
                lines.append(':param %s: %s' % (field.attname, verbose_name))

            field_type = type(field)
            module = process_django_module_path(field_type.__module__)

            lines.append(':type %s: %s.%s' % (field.attname, module, field_type.__name__))

    return lines


def skip_queryset(app, what, name, obj, skip, options):
    """Skip queryset subclasses to avoid database queries."""
    from django.db import models
    if isinstance(obj, (models.QuerySet, models.Manager)):
        return True
    return skip


def setup(app):
    # Register the docstring processor with sphinx
    app.connect('autodoc-process-docstring', process_django_models)
    app.connect('autodoc-skip-member', skip_queryset)
