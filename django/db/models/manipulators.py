from django.core.exceptions import ObjectDoesNotExist
from django.core import formfields
from django.core.formfields import Manipulator
from django.db.models.fields import FileField, AutoField
from django.db.models.fields.related import ManyToOne
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

dispatcher.connect(
    add_manipulators,
    signal=signals.class_prepared
)

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
                bases = [ self.base ]
                if hasattr(type, 'MANIPULATOR'):
                    bases = [type.MANIPULATOR] + bases
                self.man = types.ClassType(self.name, tuple(bases), {})
                self.man._prepare(type)
            return self.man

class ManipulatorHelper(object):
    def __init__(self, manip, related_collection):
        self.manip = manip
        self.related_collection = related_collection

class FillHelper(ManipulatorHelper):
    def matched_item(self,child_manip, obj_data):
        child_manip._fill_data(obj_data)
        
    def missing_item(self, index, child_manip):
        self.related_collection[index] = None

    def new_item(self):
        child_manip = self.manip.model.AddManipulator()
        self.related_collection.append(child_manip)
        child_manip._fill_data(obj_data)
    
class SaveHelper(ManipulatorHelper):
    def matched_item(self, index, child_manip, obj_data):
        child_manip._save_expanded(obj_data)
    
    def missing_item(self, index, child_manip):
        child_manip.manip.original_object.delete(ignore_objects=[parent.original_object])

    def new_item(self, index, obj_data):
        child_manip = self.manip.model.AddManipulator()
        child_manip._save_expanded(obj_data)

class AutomaticManipulator(Manipulator):
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

    def contribute_to_class(cls, other_cls, name ):
        setattr(other_cls, name, ManipulatorDescriptor(name, cls))
    contribute_to_class = classmethod(contribute_to_class)

    def __init__(self, original_object=None, follow=None, name_prefix=''):
        if name_prefix == '':
            self.follow = self.model._meta.get_follow(follow)
        else:
            self.follow = follow
        self.fields_, self.children = [], {}
        self.original_object = original_object
        self.name_prefix = name_prefix
        for f in self.opts.get_data_holders(self.follow):
            fol = self.follow[f.name]
            fields,manipulators = f.get_fields_and_manipulators(self.opts, self, follow=fol)
            #fields = f.get_manipulator_fields(self.opts, self, self.change, follow=fol)
            self.fields_.extend(fields)
            if manipulators:
                self.children[f] = manipulators
        
    def get_fields(self):
        l = list(self.fields_)
        for child_manips in self.children.values():
            for manip in child_manips:
                if manip: 
                    l.extend(manip.fields)
        return l
            
    fields = property(get_fields)
    
    def get_original_value(self, field):
        raise NotImplementedError 
    
    def get_new_object(self, expanded_data):
        params = {}
        
        for f in self.opts.fields:
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
    
    def _fill_related_objects(self, expanded_data, helper_factory):
        for related, manips in self.children.items():
                helper = helper_factory(self, related)
                child_data = expanded_data[related.var_name]
                # existing objects
                for index,manip in enumerate(manips): 
                    obj_data = child_data.get(str(index), None)
                    child_data.pop(str(index) )
                    if obj_data != None:
                        #the object has new data
                        helper.matched_item(index,manip, obj_data )
                    else:
                        #the object was not in the data
                        helper.missing_item(index,manip)
                if child_data:
                    # There are new objects in the data
                    for index, obj_data in child_data:
                        helper.new_item(obj_data)
                        
    def _fill_data(self, expanded_data):
        self.original_object = self.get_new_object()
        # TODO: many_to_many
        self._fill_related_objects(expanded_data,FillHelper)
        
    def do_command(self, new_data, command):
        expanded_data = dot_expand(new_data, MultiValueDict)
        # Deal with the effects of previous commands
        self.fill_data(expanded_data)
        # Do this command
        command_parts = command.split('.')
        self._do_command_expanded(self, expanded_data, command_parts)
    
    def _do_command_expanded(self, expanded_data, command_parts):
        part = command_parts.pop(0, None)
        if part == None:
            raise BadCommand, "Not enough parts in command"
    
        # must be the name of a child manipulator collection
        child_manips = None
        related = None
        for rel,manips in self.children: 
            if rel.var_name == part:
                related = rel
                child_manips = manips
                break
        if child_manips == None: 
            raise BadCommand, "%s : unknown manipulator collection name." % (part,)
        
        child_data = expanded_data.get(part, None)
        if child_data == None: 
            raise BadCommand, "%s : could not find data for manipulator collection." % (part,)                
            
            # The next part could be an index of a manipulator,
            # or it could be a command on the collection.
            index_part = command_parts.pop(0)
            try:
                index = int(index_part)
                manip = child_manips.get(index, None)
                if manip == None:
                    raise BadCommand, "No %s manipulator found for index %s in command." % (part, index)
                
                if command_parts == ["delete"]:
                    child_manips[index] = None
                else:
                    manip._do_command_expanded(expanded_data,command_parts)
            except ValueError:
            # Must be a command on the collection. Possible commands: 
            # add. 
                if index_part == "add":
                    child_manips.append(related.model.AddManipulator())
                        
    
    def save(self, new_data):
        expanded_data = dot_expand(new_data,MultiValueDict)
        return self._save_expanded(expanded_data)
        
    def _save_expanded(self, expanded_data):        
        add, change, opts, klass = self.add, self.change, self.opts, self.model
        
        new_object = self.get_new_object(expanded_data)

        # First, save the basic object itself.
        new_object.save()

        # Now that the object's been saved, save any uploaded files.
        for f in opts.fields:
            if isinstance(f, FileField):
                f.save_file(new_data, new_object, change and self.original_object or None, change)

        # Calculate which primary fields have changed.
        
            
        #    for f in opts.fields:
        #        if not f.primary_key and str(getattr(self.original_object, f.attname)) != str(getattr(new_object, f.attname)):
        #            self.fields_changed.append(f.verbose_name)

        # Save many-to-many objects. Example: Poll.set_sites()
        for f in opts.many_to_many:
            if self.follow.get(f.name, None):
                if not f.rel.edit_inline:
                    if f.rel.raw_id_admin:
                        new_vals = new_data.get(f.name, ())
                    else:
                        new_vals = new_data.getlist(f.name)
                    was_changed = getattr(new_object, 'set_%s' % f.name)(new_vals)
                    if change and was_changed:
                        self.fields_changed.append(f.verbose_name)
        
        # Save inline edited objects
        self._fill_related_objects(expanded_data,SaveHelper)
        
        return new_object
#        for related, manips in self.children.items():
#            child_data = expanded_data[related.var_name]
#            #print "with child:",  name
#            # Apply changes to existing objects
#            for index,manip in enumerate(manips): 
#                obj_data = child_data.get(str(index), None)
#                child_data.pop(str(index) )
#                if obj_data != None:
#                    #save the object with the new data
#                    #print "saving child data:", obj_data
#                    manip._save_expanded(obj_data)
#                else:
#                    #delete the object as it was not in the data
#                    manip.original_object.delete(ignore_objects=[self])
#                    #print "deleting child object:", manip.original_original
#            if child_data:
#                # There are new objects in the data, so 
#                # add them.
#                for index, obj_data in child_data:
#                    manip = related.model.AddManipulator()
#                    manip._save_expanded(obj_data)
#                #print "new data to be added:", child_data
        

        # Save the order, if applicable.
        #if change and opts.get_ordered_objects():
        #    order = new_data['order_'] and map(int, new_data['order_'].split(',')) or []
        #    for rel_opts in opts.get_ordered_objects():
        #        getattr(new_object, 'set_%s_order' % rel_opts.object_name.lower())(order)
        

    def get_related_objects(self):
        return self.opts.get_followed_related_objects(self.follow)

    def flatten_data(self):
        new_data = {}
        for f in self.opts.get_data_holders(self.follow):
            fol = self.follow.get(f.name)
            new_data.update(f.flatten_data(fol, self.original_object))
        return new_data

class ModelAddManipulator(AutomaticManipulator):
    change = False
    add = True
    def __init__(self, follow=None, name_prefix=''):
        super(ModelAddManipulator, self).__init__(follow=follow, name_prefix=name_prefix)

    def get_original_value(self, field):
        return field.get_default()

class ModelChangeManipulator(AutomaticManipulator):
    change = True
    add = False

    def __init__(self, obj_key=None, follow=None, name_prefix=''):
        assert obj_key is not None, "ChangeManipulator.__init__() must be passed obj_key parameter."
        if isinstance(obj_key, self.model):
            original_object = obj_key
            self.obj_key = getattr(original_object, self.model._meta.pk.attname)
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
        
        super(ModelChangeManipulator, self).__init__(original_object=original_object, follow=follow, name_prefix=name_prefix)
        #self.original_object = original_object

        if self.opts.get_ordered_objects():
            self.fields.append(formfields.CommaSeparatedIntegerField(field_name="order_"))

        self.fields_added, self.fields_changed, self.fields_deleted = [], [], []

    def get_original_value(self, field):
        return getattr(self.original_object, field.attname) 

def manipulator_validator_unique_together(field_name_list, opts, self, field_data, all_data):
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
    if hasattr(self, 'original_object') and getattr(self.original_object, opts.pk.attname) == getattr(old_obj, opts.pk.attname):
        pass
    else:
        raise validators.ValidationError, _("%(object)s with this %(type)s already exists for the given %(field)s.") % \
            {'object': capfirst(opts.verbose_name), 'type': field_list[0].verbose_name, 'field': get_text_list(field_name_list[1:], 'and')}

def manipulator_validator_unique_for_date(from_field, date_field, opts, lookup_type, self, field_data, all_data):
    date_str = all_data.get(date_field.get_manipulator_field_names('')[0], None)
    date_val = formfields.DateField.html2python(date_str)
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
        if hasattr(self, 'original_object') and getattr(self.original_object, opts.pk.attname) == getattr(old_obj, opts.pk.attname):
            pass
        else:
            format_string = (lookup_type == 'date') and '%B %d, %Y' or '%B %Y'
            raise validators.ValidationError, "Please enter a different %s. The one you entered is already being used for %s." % \
                (from_field.verbose_name, date_val.strftime(format_string))
