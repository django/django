import sys
from django.core.management.color import color_style
from django.utils.itercompat import is_iterable

class ModelErrorCollection:
    def __init__(self, outfile=sys.stdout):
        self.errors = []
        self.outfile = outfile
        self.style = color_style()

    def add(self, context, error):
        self.errors.append((context, error))
        self.outfile.write(self.style.ERROR("%s: %s\n" % (context, error)))

def get_validation_errors(outfile, app=None):
    """
    Validates all models that are part of the specified app. If no app name is provided,
    validates all models of all installed apps. Writes errors, if any, to outfile.
    Returns number of errors.
    """
    from django.conf import settings
    from django.db import models, connection
    from django.db.models.loading import get_app_errors
    from django.db.models.fields.related import RelatedObject

    e = ModelErrorCollection(outfile)

    for (app_name, error) in get_app_errors().items():
        e.add(app_name, error)

    for cls in models.get_models(app):
        opts = cls._meta

        # Do field-specific validation.
        for f in opts.local_fields:
            if f.name == 'id' and not f.primary_key and opts.pk.name == 'id':
                e.add(opts, '"%s": You can\'t use "id" as a field name, because each model automatically gets an "id" field if none of the fields have primary_key=True. You need to either remove/rename your "id" field or add primary_key=True to a field.' % f.name)
            if f.name.endswith('_'):
                e.add(opts, '"%s": Field names cannot end with underscores, because this would lead to ambiguous queryset filters.' % f.name)
            if isinstance(f, models.CharField) and f.max_length in (None, 0):
                e.add(opts, '"%s": CharFields require a "max_length" attribute.' % f.name)
            if isinstance(f, models.DecimalField):
                if f.decimal_places is None:
                    e.add(opts, '"%s": DecimalFields require a "decimal_places" attribute.' % f.name)
                if f.max_digits is None:
                    e.add(opts, '"%s": DecimalFields require a "max_digits" attribute.' % f.name)
            if isinstance(f, models.FileField) and not f.upload_to:
                e.add(opts, '"%s": FileFields require an "upload_to" attribute.' % f.name)
            if isinstance(f, models.ImageField):
                try:
                    from PIL import Image
                except ImportError:
                    e.add(opts, '"%s": To use ImageFields, you need to install the Python Imaging Library. Get it at http://www.pythonware.com/products/pil/ .' % f.name)
            if f.choices:
                if isinstance(f.choices, basestring) or not is_iterable(f.choices):
                    e.add(opts, '"%s": "choices" should be iterable (e.g., a tuple or list).' % f.name)
                else:
                    for c in f.choices:
                        if not type(c) in (tuple, list) or len(c) != 2:
                            e.add(opts, '"%s": "choices" should be a sequence of two-tuples.' % f.name)
            if f.db_index not in (None, True, False):
                e.add(opts, '"%s": "db_index" should be either None, True or False.' % f.name)

            # Perform any backend-specific field validation.
            connection.validation.validate_field(e, opts, f)

            # Check to see if the related field will clash with any existing
            # fields, m2m fields, m2m related objects or related objects
            if f.rel:
                if f.rel.to not in models.get_models():
                    e.add(opts, "'%s' has a relation with model %s, which has either not been installed or is abstract." % (f.name, f.rel.to))
                # it is a string and we could not find the model it refers to
                # so skip the next section
                if isinstance(f.rel.to, (str, unicode)):
                    continue

                rel_opts = f.rel.to._meta
                rel_name = RelatedObject(f.rel.to, cls, f).get_accessor_name()
                rel_query_name = f.related_query_name()
                for r in rel_opts.fields:
                    if r.name == rel_name:
                        e.add(opts, "Accessor for field '%s' clashes with field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                    if r.name == rel_query_name:
                        e.add(opts, "Reverse query name for field '%s' clashes with field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                for r in rel_opts.local_many_to_many:
                    if r.name == rel_name:
                        e.add(opts, "Accessor for field '%s' clashes with m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                    if r.name == rel_query_name:
                        e.add(opts, "Reverse query name for field '%s' clashes with m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                for r in rel_opts.get_all_related_many_to_many_objects():
                    if r.get_accessor_name() == rel_name:
                        e.add(opts, "Accessor for field '%s' clashes with related m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                    if r.get_accessor_name() == rel_query_name:
                        e.add(opts, "Reverse query name for field '%s' clashes with related m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                for r in rel_opts.get_all_related_objects():
                    if r.field is not f:
                        if r.get_accessor_name() == rel_name:
                            e.add(opts, "Accessor for field '%s' clashes with related field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                        if r.get_accessor_name() == rel_query_name:
                            e.add(opts, "Reverse query name for field '%s' clashes with related field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))

        seen_intermediary_signatures = [] 
        for i, f in enumerate(opts.local_many_to_many):
            # Check to see if the related m2m field will clash with any
            # existing fields, m2m fields, m2m related objects or related
            # objects
            if f.rel.to not in models.get_models():
                e.add(opts, "'%s' has an m2m relation with model %s, which has either not been installed or is abstract." % (f.name, f.rel.to))
                # it is a string and we could not find the model it refers to
                # so skip the next section
                if isinstance(f.rel.to, (str, unicode)):
                    continue
            if getattr(f.rel, 'through', None) is not None:
                if hasattr(f.rel, 'through_model'):
                    from_model, to_model = cls, f.rel.to
                    if from_model == to_model and f.rel.symmetrical:
                        e.add(opts, "Many-to-many fields with intermediate tables cannot be symmetrical.")
                    seen_from, seen_to, seen_self = False, False, 0
                    for inter_field in f.rel.through_model._meta.fields:
                        rel_to = getattr(inter_field.rel, 'to', None)
                        if from_model == to_model: # relation to self
                            if rel_to == from_model:
                                seen_self += 1
                            if seen_self > 2:
                                e.add(opts, "Intermediary model %s has more than two foreign keys to %s, which is ambiguous and is not permitted." % (f.rel.through_model._meta.object_name, from_model._meta.object_name))
                        else:
                            if rel_to == from_model:
                                if seen_from:
                                    e.add(opts, "Intermediary model %s has more than one foreign key to %s, which is ambiguous and is not permitted." % (f.rel.through_model._meta.object_name, rel_from._meta.object_name))
                                else:
                                    seen_from = True
                            elif rel_to == to_model:
                                if seen_to:
                                    e.add(opts, "Intermediary model %s has more than one foreign key to %s, which is ambiguous and is not permitted." % (f.rel.through_model._meta.object_name, rel_to._meta.object_name))
                                else:
                                    seen_to = True
                    if f.rel.through_model not in models.get_models():
                        e.add(opts, "'%s' specifies an m2m relation through model %s, which has not been installed." % (f.name, f.rel.through))
                    signature = (f.rel.to, cls, f.rel.through_model)
                    if signature in seen_intermediary_signatures:
                        e.add(opts, "The model %s has two manually-defined m2m relations through the model %s, which is not permitted. Please consider using an extra field on your intermediary model instead." % (cls._meta.object_name, f.rel.through_model._meta.object_name))
                    else:
                        seen_intermediary_signatures.append(signature)
                    seen_related_fk, seen_this_fk = False, False
                    for field in f.rel.through_model._meta.fields:
                        if field.rel:
                            if not seen_related_fk and field.rel.to == f.rel.to:
                                seen_related_fk = True
                            elif field.rel.to == cls:
                                seen_this_fk = True
                    if not seen_related_fk or not seen_this_fk:
                        e.add(opts, "'%s' has a manually-defined m2m relation through model %s, which does not have foreign keys to %s and %s" % (f.name, f.rel.through, f.rel.to._meta.object_name, cls._meta.object_name))
                else:
                    e.add(opts, "'%s' specifies an m2m relation through model %s, which has not been installed" % (f.name, f.rel.through))
            
            rel_opts = f.rel.to._meta
            rel_name = RelatedObject(f.rel.to, cls, f).get_accessor_name()
            rel_query_name = f.related_query_name()
            # If rel_name is none, there is no reverse accessor (this only
            # occurs for symmetrical m2m relations to self). If this is the
            # case, there are no clashes to check for this field, as there are
            # no reverse descriptors for this field.
            if rel_name is not None:
                for r in rel_opts.fields:
                    if r.name == rel_name:
                        e.add(opts, "Accessor for m2m field '%s' clashes with field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                    if r.name == rel_query_name:
                        e.add(opts, "Reverse query name for m2m field '%s' clashes with field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                for r in rel_opts.local_many_to_many:
                    if r.name == rel_name:
                        e.add(opts, "Accessor for m2m field '%s' clashes with m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                    if r.name == rel_query_name:
                        e.add(opts, "Reverse query name for m2m field '%s' clashes with m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.name, f.name))
                for r in rel_opts.get_all_related_many_to_many_objects():
                    if r.field is not f:
                        if r.get_accessor_name() == rel_name:
                            e.add(opts, "Accessor for m2m field '%s' clashes with related m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                        if r.get_accessor_name() == rel_query_name:
                            e.add(opts, "Reverse query name for m2m field '%s' clashes with related m2m field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                for r in rel_opts.get_all_related_objects():
                    if r.get_accessor_name() == rel_name:
                        e.add(opts, "Accessor for m2m field '%s' clashes with related field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))
                    if r.get_accessor_name() == rel_query_name:
                        e.add(opts, "Reverse query name for m2m field '%s' clashes with related field '%s.%s'. Add a related_name argument to the definition for '%s'." % (f.name, rel_opts.object_name, r.get_accessor_name(), f.name))

        # Check ordering attribute.
        if opts.ordering:
            for field_name in opts.ordering:
                if field_name == '?': continue
                if field_name.startswith('-'):
                    field_name = field_name[1:]
                if opts.order_with_respect_to and field_name == '_order':
                    continue
                # Skip ordering in the format field1__field2 (FIXME: checking
                # this format would be nice, but it's a little fiddly).
                if '_' in field_name:
                    continue
                try:
                    opts.get_field(field_name, many_to_many=False)
                except models.FieldDoesNotExist:
                    e.add(opts, '"ordering" refers to "%s", a field that doesn\'t exist.' % field_name)

        # Check unique_together.
        for ut in opts.unique_together:
            for field_name in ut:
                try:
                    f = opts.get_field(field_name, many_to_many=True)
                except models.FieldDoesNotExist:
                    e.add(opts, '"unique_together" refers to %s, a field that doesn\'t exist. Check your syntax.' % field_name)
                else:
                    if isinstance(f.rel, models.ManyToManyRel):
                        e.add(opts, '"unique_together" refers to %s. ManyToManyFields are not supported in unique_together.' % f.name)
                    if f not in opts.local_fields:
                        e.add(opts, '"unique_together" refers to %s. This is not in the same model as the unique_together statement.' % f.name)

    return len(e.errors)
