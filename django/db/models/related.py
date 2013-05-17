from collections import namedtuple

from django.utils.encoding import smart_text
from django.db.models.fields import BLANK_CHOICE_DASH

# PathInfo is used when converting lookups (fk__somecol). The contents
# describe the relation in Model terms (model Options and Fields for both
# sides of the relation. The join_field is the field backing the relation.
PathInfo = namedtuple('PathInfo',
                      'from_opts to_opts target_fields join_field '
                      'm2m direct')

class RelatedObject(object):
    def __init__(self, parent_model, model, field):
        self.parent_model = parent_model
        self.model = model
        self.opts = model._meta
        self.field = field
        self.name = '%s:%s' % (self.opts.app_label, self.opts.model_name)
        self.var_name = self.opts.model_name

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH,
                    limit_to_currently_related=False):
        """Returns choices with a default blank choices included, for use
        as SelectField choices for this field.

        Analogue of django.db.models.fields.Field.get_choices, provided
        initially for utilisation by RelatedFieldListFilter.
        """
        first_choice = blank_choice if include_blank else []
        queryset = self.model._default_manager.all()
        if limit_to_currently_related:
            queryset = queryset.complex_filter(
                {'%s__isnull' % self.parent_model._meta.model_name: False})
        lst = [(x._get_pk_val(), smart_text(x)) for x in queryset]
        return first_choice + lst

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        # Defer to the actual field definition for db prep
        return self.field.get_db_prep_lookup(lookup_type, value,
                        connection=connection, prepared=prepared)

    def editable_fields(self):
        "Get the fields in this class that should be edited inline."
        return [f for f in self.opts.fields + self.opts.many_to_many if f.editable and f != self.field]

    def __repr__(self):
        return "<RelatedObject: %s related to %s>" % (self.name, self.field.name)

    def get_accessor_name(self):
        # This method encapsulates the logic that decides what name to give an
        # accessor descriptor that retrieves related many-to-one or
        # many-to-many objects. It uses the lower-cased object_name + "_set",
        # but this can be overridden with the "related_name" option.
        if self.field.rel.multiple:
            # If this is a symmetrical m2m relation on self, there is no reverse accessor.
            if getattr(self.field.rel, 'symmetrical', False) and self.model == self.parent_model:
                return None
            return self.field.rel.related_name or (self.opts.model_name + '_set')
        else:
            return self.field.rel.related_name or (self.opts.model_name)

    def get_cache_name(self):
        return "_%s_cache" % self.get_accessor_name()

    def get_path_info(self):
        return self.field.get_reverse_path_info()
