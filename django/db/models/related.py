class BoundRelatedObject(object):
    def __init__(self, related_object, field_mapping, original):
        self.relation = related_object
        self.field_mappings = field_mapping[related_object.opts.module_name]

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
        self.edit_inline = field.rel.edit_inline
        self.name = self.opts.module_name
        self.var_name = self.opts.object_name.lower()

    def flatten_data(self, follow, obj=None):
        new_data = {}
        rel_instances = self.get_list(obj)
        for i, rel_instance in enumerate(rel_instances):
            instance_data = {}
            for f in self.opts.fields + self.opts.many_to_many:
                # TODO: Fix for recursive manipulators.
                fol = follow.get(f.name, None)
                if fol:
                    field_data = f.flatten_data(fol, rel_instance)
                    for name, value in field_data.items():
                        instance_data['%s.%d.%s' % (self.var_name, i, name)] = value
            new_data.update(instance_data)
        return new_data

    def extract_data(self, data):
        """
        Pull out the data meant for inline objects of this class,
        i.e. anything starting with our module name.
        """
        return data # TODO

    def get_list(self, parent_instance=None):
        "Get the list of this type of object from an instance of the parent class."
        if parent_instance is not None:
            attr = getattr(parent_instance, self.get_accessor_name())
            if self.field.rel.multiple:
                # For many-to-many relationships, return a list of objects
                # corresponding to the xxx_num_in_admin options of the field
                objects = list(attr.all())

                count = len(objects) + self.field.rel.num_extra_on_change
                if self.field.rel.min_num_in_admin:
                    count = max(count, self.field.rel.min_num_in_admin)
                if self.field.rel.max_num_in_admin:
                    count = min(count, self.field.rel.max_num_in_admin)

                change = count - len(objects)
                if change > 0:
                    return objects + [None] * change
                if change < 0:
                    return objects[:change]
                else: # Just right
                    return objects
            else:
                # A one-to-one relationship, so just return the single related
                # object
                return [attr]
        else:
            if self.field.rel.min_num_in_admin:
                return [None] * max(self.field.rel.num_in_admin, self.field.rel.min_num_in_admin)
            else:
                return [None] * self.field.rel.num_in_admin

    def get_db_prep_lookup(self, lookup_type, value):
        # Defer to the actual field definition for db prep
        return self.field.get_db_prep_lookup(lookup_type, value)
        
    def editable_fields(self):
        "Get the fields in this class that should be edited inline."
        return [f for f in self.opts.fields + self.opts.many_to_many if f.editable and f != self.field]

    def get_follow(self, override=None):
        if isinstance(override, bool):
            if override:
                over = {}
            else:
                return None
        else:
            if override:
                over = override.copy()
            elif self.edit_inline:
                over = {}
            else:
                return None

        over[self.field.name] = False
        return self.opts.get_follow(over)

    def get_manipulator_fields(self, opts, manipulator, change, follow):
        if self.field.rel.multiple:
            if change:
                attr = getattr(manipulator.original_object, self.get_accessor_name())
                count = attr.count()
                count += self.field.rel.num_extra_on_change
                if self.field.rel.min_num_in_admin:
                    count = max(count, self.field.rel.min_num_in_admin)
                if self.field.rel.max_num_in_admin:
                    count = min(count, self.field.rel.max_num_in_admin)
            else:
                count = self.field.rel.num_in_admin
        else:
            count = 1

        fields = []
        for i in range(count):
            for f in self.opts.fields + self.opts.many_to_many:
                if follow.get(f.name, False):
                    prefix = '%s.%d.' % (self.var_name, i)
                    fields.extend(f.get_manipulator_fields(self.opts, manipulator, change,
                                                           name_prefix=prefix, rel=True))
        return fields

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
