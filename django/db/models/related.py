from django.db.models.manipulators import ManipulatorCollection

class RelatedManipulatorCollection(ManipulatorCollection):
    def __init__(self,related, parent_name_parts , instance, follow):
        name_parts = parent_name_parts + (related.var_name, )
        self.instance = instance
        self.related = related
        super(RelatedManipulatorCollection, self).__init__(
            related.model,follow,name_parts)

    def _save_child(self, manip, parent_key):
        setattr(manip.original_object, self.related.field.attname, parent_key)
        super(RelatedManipulatorCollection, self)._save_child(manip, parent_key)

    def _get_list(self):
        if self.instance != None:
            meth_name = 'get_%s_list' % self.related.get_method_name_part()
            list = getattr(self.instance, meth_name)()
        else:
            list = []
        return list

class BoundRelatedObject(object):
    def __init__(self, related_object, field_mapping, original):
        self.relation = related_object
        self.field_mappings = field_mapping[related_object.opts.module_name]

    def template_name(self):
        raise NotImplementedError

    def __repr__(self):
        return repr(self.__dict__)

class RelatedObject(object):
    def __init__(self, parent_opts, model, field):
        self.parent_opts = parent_opts
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
        if parent_instance != None:
            func_name = 'get_%s_list' % self.get_method_name_part()
            func = getattr(parent_instance, func_name)
            return func()
        else:
            return []

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

    def __repr__(self):
        return "<RelatedObject: %s related to %s>" % (self.name, self.field.name)

    def get_fields_and_manipulators(self, opts, manipulator, follow):
        return ([], self.get_manipulators(manipulator, follow))

    def get_manipulators(self, parent_manipulator, follow):
        name_parts = parent_manipulator.name_parts
        obj = parent_manipulator.original_object
        return RelatedManipulatorCollection(self, name_parts, obj, follow)

    def bind(self, field_mapping, original, bound_related_object_class=BoundRelatedObject):
        return bound_related_object_class(self, field_mapping, original)

    def get_method_name_part(self):
        # This method encapsulates the logic that decides what name to give a
        # method that retrieves related many-to-one or many-to-many objects.
        # Usually it just uses the lower-cased object_name, but if the related
        # object is in another app, the related object's app_label is appended.
        #
        # Examples:
        #
        #   # Normal case -- a related object in the same app.
        #   # This method returns "choice".
        #   Poll.get_choice_list()
        #
        #   # A related object in a different app.
        #   # This method returns "lcom_bestofaward".
        #   Place.get_lcom_bestofaward_list() # "lcom_bestofaward"
        rel_obj_name = self.field.rel.related_name or self.opts.object_name.lower()
        if self.parent_opts.app_label != self.opts.app_label:
            rel_obj_name = '%s_%s' % (self.opts.app_label, rel_obj_name)
        return rel_obj_name
