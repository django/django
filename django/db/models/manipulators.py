from django.core.exceptions import ObjectDoesNotExist
from django import forms
from django.db.models.fields import FileField, AutoField
from django.db.models.exceptions import BadCommand
from django.dispatch import dispatcher
from django.db.models import signals
from django.utils.functional import curry
from django.utils.datastructures import dot_expand, MultiValueDict
import types

def add_manipulators(sender):
    cls = sender
    cls.add_to_class('AddManipulator', ModelAddManipulator)
    cls.add_to_class('ChangeManipulator', ModelChangeManipulator)

dispatcher.connect(add_manipulators, signal=signals.class_prepared)

class ManipulatorDescriptor(object):
    def __init__(self, name, base):
        self.man = None
        self.name = name
        self.base = base

    def __get__(self, instance, type=None):
        if instance != None:
            raise "Manipulator can not be accessed via instance"
        else:
            if not self.man:
                # Create a class which inherits from the MANIPULATOR class given in the class,
                # and the appropriate automatic manipulator,
                bases = [self.base]
                if hasattr(type, 'MANIPULATOR'):
                    bases = [type.MANIPULATOR] + bases
                self.man = types.ClassType(self.name, tuple(bases), {})
                self.man._prepare(type)
            return self.man

class Naming(object):
    def __init__(self, name_parts):
        self.name_parts = name_parts

    def _get_dotted_name(self):
        if len(self.name_parts) == 0:
            return ""
        else:
            return ".".join(self.name_parts) + "."

    dotted_name = property(_get_dotted_name)
    name_prefix = dotted_name

    def _get_name(self):
        if len(self.name_parts) == 0:
            return ""
        else:
            return self.name[-1]

    name = property(_get_name)

class AutomaticManipulator(forms.Manipulator, Naming):
    def _prepare(cls, model):
        cls.model = model
        cls.manager = model._default_manager
        cls.opts = model._meta
        for field_name_list in cls.opts.unique_together:
            setattr(cls, 'isUnique%s' % '_'.join(field_name_list), curry(manipulator_validator_unique_together, field_name_list, cls.opts))
        for f in cls.opts.fields:
            if f.unique_for_date:
                setattr(cls, 'isUnique%sFor%s' % (f.name, f.unique_for_date), curry(manipulator_validator_unique_for_date, f, cls.opts.get_field(f.unique_for_date), cls.opts, 'date'))
            if f.unique_for_month:
                setattr(cls, 'isUnique%sFor%s' % (f.name, f.unique_for_month), curry(manipulator_validator_unique_for_date, f, cls.opts.get_field(f.unique_for_month), cls.opts, 'month'))
            if f.unique_for_year:
                setattr(cls, 'isUnique%sFor%s' % (f.name, f.unique_for_year), curry(manipulator_validator_unique_for_date, f, cls.opts.get_field(f.unique_for_year), cls.opts, 'year'))
    _prepare = classmethod(_prepare)

    def contribute_to_class(cls, other_cls, name):
        setattr(other_cls, name, ManipulatorDescriptor(name, cls))
    contribute_to_class = classmethod(contribute_to_class)

    def __init__(self, original_object=None, follow=None, name_parts=()):
        Naming.__init__(self, name_parts)
        if name_parts == ():
            self.follow = self.model._meta.get_follow(follow)
        else:
            self.follow = follow
        self.fields_, self.children = [], {}
        self.original_object = original_object
        for f in self.opts.get_data_holders(self.follow):
            fol = self.follow[f.name]
            fields,manipulators = f.get_fields_and_manipulators(self.opts, self, follow=fol)

            if fields != None:
                self.fields_.extend(fields)
            if manipulators != None:
                self.children[f] = manipulators
        self.needs_deletion = False
        self.ignore_errors = False

    def get_fields(self):
        if self.needs_deletion:
            return []
        else:
            return self.fields_
            #l = list(self.fields_)
            #for child_manips in self.children.values():
            #    for manip in child_manips:
            #        if manip:
            #            l.extend(manip.fields)
            #return l

    fields = property(get_fields)

    def get_validation_errors(self, new_data):
        "Returns dictionary mapping field_names to error-message lists"
        if self.needs_deletion or self.ignore_errors:
            return {}

        errors = super(AutomaticManipulator, self).get_validation_errors(new_data)

        for manips in self.children.values():
            errors.update(manips.get_validation_errors(new_data))
        return errors

    def do_html2python(self, new_data):
        super(AutomaticManipulator, self).do_html2python(new_data)
        for child in self.children.values():
            child.do_html2python(new_data)

    def get_original_value(self, field):
        raise NotImplementedError

    def get_new_object(self, expanded_data, overrides=None):
        params = {}
        overrides = overrides or {}
        for f in self.opts.fields:
            over = overrides.get(f, None)
            if over:
                param = over
            else:
                # Fields with auto_now_add should keep their original value in the change stage.
                auto_now_add = self.change and getattr(f, 'auto_now_add', False)
                if self.follow.get(f.name, None) and not auto_now_add:
                    param = f.get_manipulator_new_data(expanded_data)
                else:
                    param = self.get_original_value(f)
            params[f.attname] = param
        if self.change:
            params[self.opts.pk.attname] = self.obj_key
        return self.model(**params)

    def _fill_data(self, expanded_data):
        if self.needs_deletion:
            raise BadCommand, "Filling %s with %r when it needs deletion" % (self, expanded_data)
        self.original_object = self.get_new_object(expanded_data)
        # TODO: many_to_many
        for related, manips in self.children.items():
            child_data = MultiValueDict(expanded_data.get(related.var_name, MultiValueDict()) )
            manips._fill_data(child_data)

    def update(self, new_data):
        expanded_data = dot_expand(new_data, MultiValueDict)
        # Deal with the effects of previous commands
        self._fill_data(expanded_data)

    def save_from_update(self, parent_key=None):
        if self.needs_deletion:
            if self.original_object != None:
               self.original_object.delete()
            return
        # TODO: many to many
        self.original_object.save()
        if not hasattr(self, 'obj_key'):
            self.obj_key = self.original_object._get_pk_val()

        for related, manips in self.children.items():
            manips.save_from_update(self.obj_key)

        return self.original_object

    def do_command(self, command):
        # Do this command
        command_parts = command.split('.')
        self._do_command_expanded(command_parts)

    def _do_command_expanded(self, command_parts):
        try:
            part = command_parts.pop(0)
        except IndexError:
            raise BadCommand, "Not enough parts in command"
        if part == "delete":
            self.needs_deletion = True
        else:
            # must be the name of a child manipulator collection
            child_manips = None
            for rel,manips in self.children.items():
                if rel.var_name == part:
                    child_manips = manips
                    break
            if child_manips == None:
                raise BadCommand, "'%s': unknown manipulator collection name." % (part,)
            else:
                child_manips._do_command_expanded(command_parts)

    def save(self, new_data):
        self.update(new_data)
        self.save_from_update()
        return self.original_object

#    def _save_expanded(self, expanded_data, overrides = None):
#        add, change, opts, klass = self.add, self.change, self.opts, self.model
#
#        new_object = self.get_new_object(expanded_data, overrides)
#
#        # First, save the basic object itself.
#        new_object.save()
#
#        # Save the key for use in creating new related objects.
#        if not hasattr(self, 'obj_key'):
#            self.obj_key = getattr(new_object, self.opts.pk.attname)
#
#        # Now that the object's been saved, save any uploaded files.
#        for f in opts.fields:
#            if isinstance(f, FileField):
#                f.save_file(new_data, new_object, change and self.original_object or None, change)
#
#        # Calculate which primary fields have changed.
#
#
#        #    for f in opts.fields:
#        #        if not f.primary_key and str(getattr(self.original_object, f.attname)) != str(getattr(new_object, f.attname)):
#        #            self.fields_changed.append(f.verbose_name)
#
#        # Save many-to-many objects. Example: Poll.set_sites()
#        for f in opts.many_to_many:
#            if self.follow.get(f.name, None):
#                if not f.rel.edit_inline:
#                    if f.rel.raw_id_admin:
#                        new_vals = new_data.get(f.name, ())
#                    else:
#                        new_vals = new_data.getlist(f.name)
#                    was_changed = getattr(new_object, 'set_%s' % f.name)(new_vals)
#                    if change and was_changed:
#                        self.fields_changed.append(f.verbose_name)
#
#        # Save inline edited objects
#        self._fill_related_objects(expanded_data, SaveHelper)
#
#        return new_object
#
#        # Save the order, if applicable.
#        #if change and opts.get_ordered_objects():
#        #    order = new_data['order_'] and map(int, new_data['order_'].split(',')) or []
#        #    for rel_opts in opts.get_ordered_objects():
#        #        getattr(new_object, 'set_%s_order' % rel_opts.object_name.lower())(order)

    def get_related_objects(self):
        return self.opts.get_followed_related_objects(self.follow)

    def flatten_data(self):
        new_data = {}

        for f in self.opts.fields + self.opts.many_to_many:
            fol = self.follow.get(f.name, None)
            if fol:
                new_data.update(f.flatten_data(fol, self.original_object))
        for rel, child_manips in self.children.items():
            child_data = child_manips.flatten_data()
            new_data.update(child_data)

        prefix = self.name_prefix
        new_data = dict([(prefix + k, v) for k,v in new_data.items()])
        return new_data

class ModelAddManipulator(AutomaticManipulator):
    change = False
    add = True
    def __init__(self, follow=None, name_parts=()):
        super(ModelAddManipulator, self).__init__(follow=follow, name_parts=name_parts)

    def get_original_value(self, field):
        return field.get_default()

    def __repr__(self):
        return "<Automatic AddManipulator '%s' for %s>" % (self.name_prefix, self.model.__name__)

class ModelChangeManipulator(AutomaticManipulator):
    change = True
    add = False

    def __init__(self, obj_key=None, follow=None, name_parts=()):
        assert obj_key is not None, "ChangeManipulator.__init__() must be passed obj_key parameter."
        opts = self.model._meta
        if isinstance(obj_key, self.model):
            original_object = obj_key
            self.obj_key = original_object._get_pk_val()
        else:
            self.obj_key = obj_key
            try:
                original_object = self.manager.get_object(pk=obj_key)
            except ObjectDoesNotExist:
                # If the object doesn't exist, this might be a manipulator for a
                # one-to-one related object that hasn't created its subobject yet.
                # For example, this might be a Restaurant for a Place that doesn't
                # yet have restaurant information.
                if opts.one_to_one_field:
                    # Sanity check -- Make sure the "parent" object exists.
                    # For example, make sure the Place exists for the Restaurant.
                    # Let the ObjectDoesNotExist exception propogate up.
                    lookup_kwargs = opts.one_to_one_field.rel.limit_choices_to
                    lookup_kwargs['%s__exact' % opts.one_to_one_field.rel.field_name] = obj_key
                    null = opts.one_to_one_field.rel.to._meta.get_model_module().get_object(**lookup_kwargs)
                    params = dict([(f.attname, f.get_default()) for f in opts.fields])
                    params[opts.pk.attname] = obj_key
                    original_object = opts.get_model_module().Klass(**params)
                else:
                    raise
            else:
                # Save the obj_key even though we already have it, in case it's
                # currently a string and needs to be an integer.
                self.obj_key = original_object._get_pk_val()

        super(ModelChangeManipulator, self).__init__(original_object=original_object, follow=follow, name_parts=name_parts)
        #self.original_object = original_object

        #if self.opts.get_ordered_objects():
        #    self.fields.append(formfields.CommaSeparatedIntegerField(field_name="order_"))

        self.fields_added, self.fields_changed, self.fields_deleted = [], [], []

    def get_original_value(self, field):
        return getattr(self.original_object, field.attname)

    def __repr__(self):
        return "<Automatic ChangeManipulator '%s' for %s:%r >" % (self.name_prefix, self.model.__name__, self.obj_key)

class ManipulatorCollection(list, Naming):
    def __init__(self, model, follow, name_parts=()):
        Naming.__init__(self, name_parts)
        self.model = model
        self.follow = follow
        self._load()

    def _get_list(self):
        return self.model._default_manager.get_list()

    def _load(self):
        man_class = self.model.ChangeManipulator

        for i,obj in enumerate(self._get_list()):
            self.append(man_class(obj, self.follow, self.name_parts + (str(i),)))

    def _save_child(self, manip, parent_key):
        manip.save_from_update()

    def save_from_update(self, parent_key=None):
        for manip in self:
            if manip:
                self._save_child(manip, parent_key)

    def _fill_data(self, expanded_data):
        for index,manip in enumerate(self):
            obj_data = expanded_data.get(str(index), None)
            expanded_data.pop(str(index), None)
            if manip:
                if obj_data != None:
                    #the object has new data
                    manip._fill_data(obj_data)
                else:
                    #the object was not in the data
                    manip.needs_deletion = True
        if expanded_data:
            # There are new objects in the data
            items = [(int(k), v) for k, v in expanded_data.items()]
            items.sort(lambda x, y: cmp(x[0], y[0]))
            for index, obj_data in items:
                child_manip = self.add_child(index)
                #HACK: this data will not have been converted to python form yet.
                #child_manip.do_html2python(obj_data)
                child_manip._fill_data(obj_data)

    def _do_command_expanded(self, command_parts):
        # The next part could be an index of a manipulator,
        # or it could be a command on the collection.
        try:
            index_part = command_parts.pop(0)
        except IndexError:
            raise BadCommand, "Not enough parts in command"
        try:
            index = int(index_part)
            try:
                manip = self[index]
            except IndexError:
                raise BadCommand, "No %s manipulator found for index %s in command." % (part, index)

            if manip == None:
                raise BadCommand, "No %s manipulator found for index %s in command." % (part, index)

            manip._do_command_expanded(command_parts)
        except ValueError:
            command_name = index_part
        # Must be a command on the collection. Possible commands:
        # add.
        # TODO: page.forward, page.back, page.n, swap.n.m
            if command_name == "add":
                child_manip = self.add_child()
                # Don't show validation stuff for things just added.
                child_manip.ignore_errors = True
            elif command_name == "swap":
                order_field = self.model._meta.order_with_respect_to
                if not order_field:
                    raise BadCommand, "Swap command recieved on unordered ManipulatorCollection"
                try:
                    manip1 = self[int(command_parts.pop(0))]
                    manip2 = self[int(command_parts.pop(0))]
                    if manip1 == None or manip2 == None:
                        raise BadCommand, "Attempt to swap a deleted manipulator"
                except ValueError, IndexError:
                    raise BadCommand, "Could not find manipulators for swap command"
                else:
                    # Set the ordering field value on the objects in the manipulators.
                    # This will make sure they are put in a different when rendered on the form.
                    # The indices in this collection will stay the same.
                    temp = getattr(manip1.original_object, order_field.attname)
                    setattr(manip1.original_object, order_field.attname,
                             getattr(manip2.original_object, order_field.attname))
                    setattr(manip2.original_object, order_field.attname, temp)
            else:
                raise BadCommand, "%s, unknown command" % (command_name)

    def add_child(self, index = None):
        man_class = self.model.AddManipulator
        if index == None:
            index = len(self)
        # Make sure that we are going to put this in the right index, by prefilling with Nones.
        for i in range(len(self), index + 1):
            self.append(None)

        prefix = '%s%s.' % (self.name_prefix, index )
        child_manip = man_class(self.follow, self.name_parts + (str(index),))

        self[index] = child_manip
        return child_manip

    def flatten_data(self):
        new_data = {}
        for manip in self:
            if manip:
                manip_data = manip.flatten_data()
                new_data.update(manip_data)
        return new_data

    def get_validation_errors(self, new_data):
        "Returns dictionary mapping field_names to error-message lists"
        errors = {}
        for manip in self:
            if manip:
                errors.update(manip.get_validation_errors(new_data))
        return errors

    def do_html2python(self, new_data):
        for manip in self:
            if manip:
                manip.do_html2python(new_data)

def manipulator_validator_unique_together(field_name_list, opts, self, field_data, all_data):
    from django.db.models.fields.related import ManyToOne
    from django.utils.text import get_text_list
    field_list = [opts.get_field(field_name) for field_name in field_name_list]
    if isinstance(field_list[0].rel, ManyToOne):
        kwargs = {'%s__%s__iexact' % (field_name_list[0], field_list[0].rel.field_name): field_data}
    else:
        kwargs = {'%s__iexact' % field_name_list[0]: field_data}
    for f in field_list[1:]:
        # This is really not going to work for fields that have different
        # form fields, e.g. DateTime.
        # This validation needs to occur after html2python to be effective.
        field_val = all_data.get(f.attname, None)
        if field_val is None:
            # This will be caught by another validator, assuming the field
            # doesn't have blank=True.
            return
        if isinstance(f.rel, ManyToOne):
            kwargs['%s__pk' % f.name] = field_val
        else:
            kwargs['%s__iexact' % f.name] = field_val
    mod = opts.get_model_module()
    try:
        old_obj = mod.get_object(**kwargs)
    except ObjectDoesNotExist:
        return
    if hasattr(self, 'original_object') and self.original_object._get_pk_val() == old_obj._get_pk_val():
        pass
    else:
        raise validators.ValidationError, _("%(object)s with this %(type)s already exists for the given %(field)s.") % \
            {'object': capfirst(opts.verbose_name), 'type': field_list[0].verbose_name, 'field': get_text_list(field_name_list[1:], 'and')}

def manipulator_validator_unique_for_date(from_field, date_field, opts, lookup_type, self, field_data, all_data):
    from django.db.models.fields.related import ManyToOne
    date_str = all_data.get(date_field.get_manipulator_field_names('')[0], None)
    date_val = forms.DateField.html2python(date_str)
    if date_val is None:
        return # Date was invalid. This will be caught by another validator.
    lookup_kwargs = {'%s__year' % date_field.name: date_val.year}
    if isinstance(from_field.rel, ManyToOne):
        lookup_kwargs['%s__pk' % from_field.name] = field_data
    else:
        lookup_kwargs['%s__iexact' % from_field.name] = field_data
    if lookup_type in ('month', 'date'):
        lookup_kwargs['%s__month' % date_field.name] = date_val.month
    if lookup_type == 'date':
        lookup_kwargs['%s__day' % date_field.name] = date_val.day
    try:
        old_obj = opts.model._default_manager.get_object(**lookup_kwargs)
    except ObjectDoesNotExist:
        return
    else:
        if hasattr(self, 'original_object') and self.original_object._get_pk_val() == old_obj._get_pk_val():
            pass
        else:
            format_string = (lookup_type == 'date') and '%B %d, %Y' or '%B %Y'
            raise validators.ValidationError, "Please enter a different %s. The one you entered is already being used for %s." % \
                (from_field.verbose_name, date_val.strftime(format_string))
