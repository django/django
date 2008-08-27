class BoundRelatedObject(object):
    def __init__(self, related_object, field_mapping, original):
        self.relation = related_object
        self.field_mappings = field_mapping[related_object.name]

    def template_name(self):
        raise NotImplementedError

    def __repr__(self):
        return repr(self.__dict__)

class RelatedObject(object):
    def __init__(self, parent_model, model, field):
        self.parent_model = parent_model
        self.model = model
        self.opts = model._meta
        self.field = field
        self.name = '%s:%s' % (self.opts.app_label, self.opts.module_name)
        self.var_name = self.opts.object_name.lower()

    def get_db_prep_lookup(self, lookup_type, value):
        # Defer to the actual field definition for db prep
        return self.field.get_db_prep_lookup(lookup_type, value)

    def editable_fields(self):
        "Get the fields in this class that should be edited inline."
        return [f for f in self.opts.fields + self.opts.many_to_many if f.editable and f != self.field]

    def __repr__(self):
        return "<RelatedObject: %s related to %s>" % (self.name, self.field.name)

    def bind(self, field_mapping, original, bound_related_object_class=BoundRelatedObject):
        return bound_related_object_class(self, field_mapping, original)

    def get_accessor_name(self):
        # This method encapsulates the logic that decides what name to give an
        # accessor descriptor that retrieves related many-to-one or
        # many-to-many objects. It uses the lower-cased object_name + "_set",
        # but this can be overridden with the "related_name" option.
        if self.field.rel.multiple:
            # If this is a symmetrical m2m relation on self, there is no reverse accessor.
            if getattr(self.field.rel, 'symmetrical', False) and self.model == self.parent_model:
                return None
            return self.field.rel.related_name or (self.opts.object_name.lower() + '_set')
        else:
            return self.field.rel.related_name or (self.opts.object_name.lower())
