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
        assert not errors, errors

        # Check swappable attribute.
        if opts.swapped:
            try:
                app_label, model_name = opts.swapped.split('.')
            except ValueError:
                e.add(opts, "%s is not of the form 'app_label.app_name'." % opts.swappable)
                continue
            if not models.get_model(app_label, model_name):
                e.add(opts, "Model has been swapped out for '%s' which has not been installed or is abstract." % opts.swapped)
            # No need to perform any other validation checks on a swapped model.
            continue

        # If this is the current User model, check known validation problems with User models
        if settings.AUTH_USER_MODEL == '%s.%s' % (opts.app_label, opts.object_name):
            # Check that REQUIRED_FIELDS is a list
            if not isinstance(cls.REQUIRED_FIELDS, (list, tuple)):
                e.add(opts, 'The REQUIRED_FIELDS must be a list or tuple.')

            # Check that the USERNAME FIELD isn't included in REQUIRED_FIELDS.
            if cls.USERNAME_FIELD in cls.REQUIRED_FIELDS:
                e.add(opts, 'The field named as the USERNAME_FIELD should not be included in REQUIRED_FIELDS on a swappable User model.')

            # Check that the username field is unique
            if not opts.get_field(cls.USERNAME_FIELD).unique:
                e.add(opts, 'The USERNAME_FIELD must be unique. Add unique=True to the field parameters.')

        # Store a list of column names which have already been used by other fields.
        used_column_names = []

        # Model isn't swapped; do field-specific validation.
        for f in opts.local_fields:
            if f.name == 'id' and not f.primary_key and opts.pk.name == 'id':
                e.add(opts, '"%s": You can\'t use "id" as a field name, because each model automatically gets an "id" field if none of the fields have primary_key=True. You need to either remove/rename your "id" field or add primary_key=True to a field.' % f.name)
            if f.name.endswith('_'):
                e.add(opts, '"%s": Field names cannot end with underscores, because this would lead to ambiguous queryset filters.' % f.name)

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

        for f in opts.local_fields + opts.local_many_to_many:
            m2m = f in opts.local_many_to_many

            # Skip all non-relative fields, because opts.local_fields may
            # contain them.
            if not f.rel:
                continue

            # It is a string and we could not find the model it refers to so
            # skip the next section
            if isinstance(f.rel.to, six.string_types):
                continue

            if not m2m and f.rel.is_hidden():
                continue

            rel_opts = f.rel.to._meta
            rel_name = f.related.get_accessor_name()
            rel_query_name = f.related_query_name()

            # If rel_name is None, there is no reverse accessor (this only
            # occurs for symmetrical m2m relations to self). If this is the
            # case, there are no clashes to check for this field, as there are
            # no reverse descriptors for this field.
            if m2m and rel_name is None:
                continue

            if f in opts.local_fields:
                # Check to see if the related field will clash with any existing
                # fields, m2m fields, m2m related objects or related objects

                for r in rel_opts.fields + rel_opts.local_many_to_many:
                    m2m_part = "m2m " if r in rel_opts.many_to_many else ""
                    if r.name == rel_name:
                        e.add(opts, "Accessor for field '%s' clashes with %sfield '%s.%s'. "
                            "Add a related_name argument to the definition for '%s'."
                            % (f.name, m2m_part, rel_opts.object_name, r.name, f.name))
                    if r.name == rel_query_name:
                        e.add(opts, "Reverse query name for field '%s' clashes with %sfield '%s.%s'. "
                            "Add a related_name argument to the definition for '%s'."
                            % (f.name, m2m_part, rel_opts.object_name, r.name, f.name))

                for r in rel_opts.get_all_related_many_to_many_objects() + rel_opts.get_all_related_objects():
                    m2m_part = "m2m " if r in rel_opts.get_all_related_many_to_many_objects() else ""
                    if r in rel_opts.get_all_related_objects() and r.field is f:
                        continue
                    if r.get_accessor_name() == rel_name:
                        e.add(opts, "Accessor for field '%s' clashes with related %sfield '%s.%s'. "
                            "Add a related_name argument to the definition for '%s'."
                            % (f.name, m2m_part, rel_opts.object_name, r.get_accessor_name(), f.name))
                    if r.get_accessor_name() == rel_query_name:
                        e.add(opts, "Reverse query name for field '%s' clashes with related %sfield '%s.%s'. "
                            "Add a related_name argument to the definition for '%s'."
                            % (f.name, m2m_part, rel_opts.object_name, r.get_accessor_name(), f.name))

            else: # f in opts.local_many_to_many

                for r in rel_opts.fields + rel_opts.local_many_to_many:
                    m2m_part = "m2m " if r in rel_opts.many_to_many else ""
                    if r.name == rel_name:
                        e.add(opts, "Accessor for m2m field '%s' clashes with %sfield '%s.%s'. "
                            "Add a related_name argument to the definition for '%s'."
                            % (f.name, m2m_part, rel_opts.object_name, r.name, f.name))
                    if r.name == rel_query_name:
                        e.add(opts, "Reverse query name for m2m field '%s' clashes with %sfield '%s.%s'. "
                            "Add a related_name argument to the definition for '%s'."
                            % (f.name, m2m_part, rel_opts.object_name, r.name, f.name))

                for r in rel_opts.get_all_related_many_to_many_objects() + rel_opts.get_all_related_objects():
                    m2m_part = "m2m " if r in rel_opts.get_all_related_many_to_many_objects() else ""
                    if r in rel_opts.get_all_related_many_to_many_objects() and r.field is f:
                        continue
                    if r.get_accessor_name() == rel_name:
                        e.add(opts, "Accessor for m2m field '%s' clashes with related %sfield '%s.%s'. "
                            "Add a related_name argument to the definition for '%s'."
                            % (f.name, m2m_part, rel_opts.object_name, r.get_accessor_name(), f.name))
                    if r.get_accessor_name() == rel_query_name:
                        e.add(opts, "Reverse query name for m2m field '%s' clashes with related %sfield '%s.%s'. "
                            "Add a related_name argument to the definition for '%s'."
                            % (f.name, m2m_part, rel_opts.object_name, r.get_accessor_name(), f.name))

        # Check ordering attribute.
        if opts.ordering:
            for field_name in opts.ordering:
                if field_name == '?':
                    continue
                if field_name.startswith('-'):
                    field_name = field_name[1:]
                if opts.order_with_respect_to and field_name == '_order':
                    continue
                # Skip ordering in the format field1__field2 (FIXME: checking
                # this format would be nice, but it's a little fiddly).
                if '__' in field_name:
                    continue
                # Skip ordering on pk. This is always a valid order_by field
                # but is an alias and therefore won't be found by opts.get_field.
                if field_name == 'pk':
                    continue
                try:
                    opts.get_field(field_name, many_to_many=False)
                except models.FieldDoesNotExist:
                    e.add(opts, '"ordering" refers to "%s", a field that doesn\'t exist.' % field_name)

        # Check unique_together.
        for ut in opts.unique_together:
            validate_local_fields(e, opts, "unique_together", ut)
        if not isinstance(opts.index_together, collections.Sequence):
            e.add(opts, '"index_together" must a sequence')
        else:
            for it in opts.index_together:
                validate_local_fields(e, opts, "index_together", it)

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
