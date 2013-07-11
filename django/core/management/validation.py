import collections
import sys

from django.conf import settings
from django.core.management.color import color_style
from django.utils.encoding import force_str
from django.utils.itercompat import is_iterable
from django.utils import six


class ModelErrorCollection:
    def __init__(self, outfile=sys.stdout):
        self.errors = []
        self.outfile = outfile
        self.style = color_style()

    def add(self, context, error):
        self.errors.append((context, error))
        self.outfile.write(self.style.ERROR(force_str("%s: %s\n" % (context, error))))


def get_validation_errors(outfile, app=None):
    """
    Validates all models that are part of the specified app. If no app name is provided,
    validates all models of all installed apps. Writes errors, if any, to outfile.
    Returns number of errors.
    """
    from django.db import models
    from django.db.models.loading import get_app_errors

    e = ModelErrorCollection(outfile)

    for (app_name, error) in get_app_errors().items():
        e.add(app_name, error)

    for cls in models.get_models(app, include_swapped=True):
        opts = cls._meta

        errors = cls.check()
        #assert not errors, errors

        # Check swappable attribute.
        if opts.swapped:
            continue

        # Store a list of column names which have already been used by other fields.
        used_column_names = []

        # Model isn't swapped; do field-specific validation.
        for f in opts.local_fields:
            # Column name validation.
            # Determine which column name this field wants to use.
            _, column_name = f.get_attname_column()

            # Ensure the column name is not already in use.
            if column_name and column_name in used_column_names:
                e.add(opts, "Field '%s' has column name '%s' that is already used." % (f.name, column_name))
            else:
                used_column_names.append(column_name)

            if isinstance(f, models.ImageField):
                try:
                    from django.utils.image import Image
                except ImportError:
                    e.add(opts, '"%s": To use ImageFields, you need to install Pillow. Get it at https://pypi.python.org/pypi/Pillow.' % f.name)

        seen_intermediary_signatures = []
        for f in opts.local_many_to_many:
            # Check to see if the related m2m field will clash with any
            # existing fields, m2m fields, m2m related objects or related
            # objects

            # it is a string and we could not find the model it refers to
            # so skip the next section
            if (f.rel.to not in models.get_models() and
                isinstance(f.rel.to, six.string_types)):
                continue

            if f.rel.through is not None and not isinstance(f.rel.through, six.string_types):
                from_model, to_model = cls, f.rel.to
                signature = (f.rel.to, cls, f.rel.through)
                if signature in seen_intermediary_signatures:
                    e.add(opts, "The model %s has two manually-defined m2m "
                        "relations through the model %s, which is not "
                        "permitted. Please consider using an extra field on "
                        "your intermediary model instead." % (
                            cls._meta.object_name,
                            f.rel.through._meta.object_name
                        )
                    )
                else:
                    seen_intermediary_signatures.append(signature)

        # Check unique_together.
        for ut in opts.unique_together:
            validate_local_fields(e, opts, "unique_together", ut)

    return len(e.errors)


def validate_local_fields(e, opts, field_name, fields):
    from django.db import models

    if not isinstance(fields, collections.Sequence):
        e.add(opts, 'all %s elements must be sequences' % field_name)
    else:
        for field in fields:
            try:
                f = opts.get_field(field, many_to_many=True)
            except models.FieldDoesNotExist:
                e.add(opts, '"%s" refers to %s, a field that doesn\'t exist.' % (field_name, field))
            else:
                if isinstance(f.rel, models.ManyToManyRel):
                    e.add(opts, '"%s" refers to %s. ManyToManyFields are not supported in %s.' % (field_name, f.name, field_name))
                if f not in opts.local_fields:
                    e.add(opts, '"%s" refers to %s. This is not in the same model as the %s statement.' % (field_name, f.name, field_name))
