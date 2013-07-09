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

        # Model isn't swapped; do field-specific validation.
        for f in opts.local_fields:
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

        fields = opts.local_fields + opts.local_many_to_many

        # Skip all non-relative fields, because opts.local_fields may
        # contain them.
        fields = (f for f in fields if f.rel)

        # If `f.rel.to` is a string, it wasn't resolved into a model; that means
        # that we couldn't find the model and we skip in that case.
        fields = (f for f in fields
            if not isinstance(f.rel.to, six.string_types))

        # If the field doesn't install backward relation on the target model (so
        # `is_hidden` returns True), then there are no clashes to check and we
        # can skip.
        fields = (f for f in fields if not f.rel.is_hidden())

        # Skip all fields without reverse accessors (this only occurs for
        # symmetrical m2m relations to self). If this is the case, there are no
        # clashes to check for this field, as there are no reverse descriptors
        # for this field.
        fields = (f for f in fields if f.related.get_accessor_name())

        for field in fields:
            is_field_m2m = field in opts.local_many_to_many
            rel_opts = field.rel.to._meta
            rel_name = field.related.get_accessor_name()
            rel_query_name = field.related_query_name()
            field_name = ("m2m " if is_field_m2m else "") \
                + ("field '%s'" % field.name) # e.g. "m2m field 'mym2m'"

            # Consider the following (invalid) models:
            #
            #     class Target(models.Model):
            #         model = models.IntegerField()
            #         model_set = models.IntegerField()
            #
            #     class Model(models.Model):
            #         foreign = ForeignKey(Target)
            #         m2m = ManyToManyField(Target)
            #
            # In that case, when the checked field is `Model.foreign`, local
            # variable values are:
            #
            #     field = cls.foreign.field
            #     field_name = "field 'foreign'"
            #     is_field_m2m = False
            #     opts.local_field = [cls.id.field, cls.foreign.field]
            #     opts.local_many_to_many = [cls.m2m.field]
            #     rel_name = "model_set"
            #     rel_query_name = "model"
            #     rel_opts.fields = [Target.id.field, Target.model.field, Target.model_set.field]
            #     rel_opts.local_many_to_many = []
            #     rel_opts.get_all_related_objects() = \
            #         [<RelatedObject: invalid_models:model related to foreign>]
            #     rel_opts.get_all_related_many_to_many_objects() = \
            #         [<RelatedObject: invalid_models:model related to m2m>]
            #     rel_opts.object_name = "Target"
            #
            # When we check clash between field `Target.model` and reverse
            # query name for field `Model.foreign` which is `Target.model`
            # too, we are in the first loop and local variables values are:
            #
            #     r = Target.model.field
            #     r.name = "model"
            #
            # When we check clash between related m2m field `Target.model_set`
            # and accessor for `Model.foreign` field which is
            # `Target.model_set` too, we are in the second loop and local
            # variables values are:
            #
            #     r.field = Model.m2m.field
            #     r.get_accessor_name() = "model_set"

            def check():
                if compare_to == rel_name:
                    e.add(opts, "Accessor for %s clashes with %s. "
                        "Add a related_name argument to the definition for '%s'."
                        % (field_name, r_name, field.name))
                if compare_to == rel_query_name:
                    e.add(opts, "Reverse query name for %s clashes with %s. "
                        "Add a related_name argument to the definition for '%s'."
                        % (field_name, r_name, field.name))

            # The first loop.
            for r in rel_opts.fields + rel_opts.local_many_to_many:
                r_name = ("m2m " if r in rel_opts.many_to_many else "") \
                    + "field '%s.%s'" % (rel_opts.object_name, r.name)
                compare_to = r.name
                check()

            # The second loop.
            for r in rel_opts.get_all_related_many_to_many_objects() + rel_opts.get_all_related_objects():
                m2m_part = "m2m " if r in rel_opts.get_all_related_many_to_many_objects() else ""
                r_name = "related " + m2m_part + "field '%s.%s'" % (rel_opts.object_name, r.get_accessor_name())
                compare_to = r.get_accessor_name()
                if r.field is field:
                    if (not is_field_m2m and r in rel_opts.get_all_related_objects() or
                        is_field_m2m and r in rel_opts.get_all_related_many_to_many_objects()):
                        continue
                check()

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
