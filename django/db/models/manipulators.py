from django.core.exceptions import ObjectDoesNotExist
from django.core import formfields
from django.core.formfields import Manipulator
from django.db.models.fields import FileField, AutoField
from django.db.models.fields.related import ManyToOne
from django.dispatch import dispatcher
from django.db.models import signals
from django.utils.functional import curry

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
    class empty:
        pass

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

    def __init__(self, original_object=None, follow=None):
        self.follow = self.model._meta.get_follow(follow)
        self.fields = []
        self.original_object = original_object
        for f in self.opts.get_data_holders(self.follow):
            fol = self.follow[f.name]
            fields = f.get_manipulator_fields(self.opts, self, self.change, follow=fol)
            self.fields.extend(fields)

    def save(self, new_data):
        add, change, opts, klass = self.add, self.change, self.opts, self.model
        # TODO: big cleanup when core fields go -> use recursive manipulators.
        from django.utils.datastructures import DotExpandedDict
        params = {}
        for f in opts.fields:
            # Fields with auto_now_add should keep their original value in the change stage.
            auto_now_add = change and getattr(f, 'auto_now_add', False)
            if self.follow.get(f.name, None) and not auto_now_add:
                param = f.get_manipulator_new_data(new_data)
            else:
                if change:
                    param = getattr(self.original_object, f.attname)
                else:
                    param = f.get_default()
            params[f.attname] = param

        if change:
            params[opts.pk.attname] = self.obj_key

        # First, save the basic object itself.
        new_object = klass(**params)
        new_object.save()

        # Now that the object's been saved, save any uploaded files.
        for f in opts.fields:
            if isinstance(f, FileField):
                f.save_file(new_data, new_object, change and self.original_object or None, change, rel=False)

        # Calculate which primary fields have changed.
        if change:
            self.fields_added, self.fields_changed, self.fields_deleted = [], [], []
            for f in opts.fields:
                if not f.primary_key and str(getattr(self.original_object, f.attname)) != str(getattr(new_object, f.attname)):
                    self.fields_changed.append(f.verbose_name)

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

        expanded_data = DotExpandedDict(dict(new_data))
        # Save many-to-one objects. Example: Add the Choice objects for a Poll.
        for related in opts.get_all_related_objects():
            # Create obj_list, which is a DotExpandedDict such as this:
            # [('0', {'id': ['940'], 'choice': ['This is the first choice']}),
            #  ('1', {'id': ['941'], 'choice': ['This is the second choice']}),
            #  ('2', {'id': [''], 'choice': ['']})]
            child_follow = self.follow.get(related.name, None)

            if child_follow:
                obj_list = expanded_data[related.var_name].items()
                obj_list.sort(lambda x, y: cmp(int(x[0]), int(y[0])))

                # For each related item...
                for null, rel_new_data in obj_list:

                    params = {}

                    # Keep track of which core=True fields were provided.
                    # If all core fields were given, the related object will be saved.
                    # If none of the core fields were given, the object will be deleted.
                    # If some, but not all, of the fields were given, the validator would
                    # have caught that.
                    all_cores_given, all_cores_blank = True, True

                    # Get a reference to the old object. We'll use it to compare the
                    # old to the new, to see which fields have changed.
                    old_rel_obj = None
                    if change:
                        if rel_new_data[related.opts.pk.name][0]:
                            try:
                                old_rel_obj = getattr(self.original_object, 'get_%s' % related.get_method_name_part() )(**{'%s__exact' % related.opts.pk.name: rel_new_data[related.opts.pk.attname][0]})
                            except ObjectDoesNotExist:
                                pass

                    for f in related.opts.fields:
                        if f.core and not isinstance(f, FileField) and f.get_manipulator_new_data(rel_new_data, rel=True) in (None, ''):
                            all_cores_given = False
                        elif f.core and not isinstance(f, FileField) and f.get_manipulator_new_data(rel_new_data, rel=True) not in (None, ''):
                            all_cores_blank = False
                        # If this field isn't editable, give it the same value it had
                        # previously, according to the given ID. If the ID wasn't
                        # given, use a default value. FileFields are also a special
                        # case, because they'll be dealt with later.

                        if f == related.field:
                            param = getattr(new_object, related.field.rel.field_name)
                        elif add and isinstance(f, AutoField):
                            param = None
                        elif change and (isinstance(f, FileField) or not child_follow.get(f.name, None)):
                            if old_rel_obj:
                                param = getattr(old_rel_obj, f.column)
                            else:
                                param = f.get_default()
                        else:
                            param = f.get_manipulator_new_data(rel_new_data, rel=True)
                        if param != None:
                           params[f.attname] = param

                    # Create the related item.
                    new_rel_obj = related.model(**params)

                    # If all the core fields were provided (non-empty), save the item.
                    if all_cores_given:
                        new_rel_obj.save()

                        # Save any uploaded files.
                        for f in related.opts.fields:
                            if child_follow.get(f.name, None):
                                if isinstance(f, FileField) and rel_new_data.get(f.name, False):
                                    f.save_file(rel_new_data, new_rel_obj, change and old_rel_obj or None, old_rel_obj is not None, rel=True)

                        # Calculate whether any fields have changed.
                        if change:
                            if not old_rel_obj: # This object didn't exist before.
                                self.fields_added.append('%s "%s"' % (related.opts.verbose_name, new_rel_obj))
                            else:
                                for f in related.opts.fields:
                                    if not f.primary_key and f != related.field and str(getattr(old_rel_obj, f.attname)) != str(getattr(new_rel_obj, f.attname)):
                                        self.fields_changed.append('%s for %s "%s"' % (f.verbose_name, related.opts.verbose_name, new_rel_obj))

                        # Save many-to-many objects.
                        for f in related.opts.many_to_many:
                            if child_follow.get(f.name, None) and not f.rel.edit_inline:
                                was_changed = getattr(new_rel_obj, 'set_%s' % f.name)(rel_new_data[f.attname])
                                if change and was_changed:
                                    self.fields_changed.append('%s for %s "%s"' % (f.verbose_name, related.opts.verbose_name, new_rel_obj))

                    # If, in the change stage, all of the core fields were blank and
                    # the primary key (ID) was provided, delete the item.
                    if change and all_cores_blank and old_rel_obj:
                        new_rel_obj.delete(ignore_objects=[new_object])
                        self.fields_deleted.append('%s "%s"' % (related.opts.verbose_name, old_rel_obj))

        # Save the order, if applicable.
        if change and opts.get_ordered_objects():
            order = new_data['order_'] and map(int, new_data['order_'].split(',')) or []
            for rel_opts in opts.get_ordered_objects():
                getattr(new_object, 'set_%s_order' % rel_opts.object_name.lower())(order)
        return new_object

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
    def __init__(self, follow=None):
        super(ModelAddManipulator, self).__init__(follow=follow)

class ModelChangeManipulator(AutomaticManipulator):
    change = True
    add = False

    def __init__(self, obj_key=None, follow=None):
        assert obj_key is not None, "ChangeManipulator.__init__() must be passed obj_key parameter."
        self.obj_key = obj_key
        try:
            original_object = self.__class__.manager.get_object(pk=obj_key)
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
        super(ModelChangeManipulator, self).__init__(original_object=original_object, follow=follow)
        self.original_object = original_object

        if self.opts.get_ordered_objects():
            self.fields.append(formfields.CommaSeparatedIntegerField(field_name="order_"))

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
