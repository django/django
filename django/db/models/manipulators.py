from django.core.exceptions import ObjectDoesNotExist
from django import forms
from django.core import validators
from django.db.models.fields import FileField, AutoField
from django.dispatch import dispatcher
from django.db.models import signals
from django.utils.functional import curry
from django.utils.datastructures import DotExpandedDict, MultiValueDict
from django.utils.text import capfirst
import types

def add_manipulators(sender):
    cls = sender
    cls.add_to_class('AddManipulator', AutomaticAddManipulator)
    cls.add_to_class('ChangeManipulator', AutomaticChangeManipulator)

dispatcher.connect(add_manipulators, signal=signals.class_prepared)

class ManipulatorDescriptor(object):
    # This class provides the functionality that makes the default model
    # manipulators (AddManipulator and ChangeManipulator) available via the
    # model class.
    def __init__(self, name, base):
        self.man = None # Cache of the manipulator class.
        self.name = name
        self.base = base

    def __get__(self, instance, model=None):
        if instance != None:
            raise AttributeError, "Manipulator cannot be accessed via instance"
        else:
            if not self.man:
                # Create a class that inherits from the "Manipulator" class
                # given in the model class (if specified) and the automatic
                # manipulator.
                bases = [self.base]
                if hasattr(model, 'Manipulator'):
                    bases = [model.Manipulator] + bases
                self.man = types.ClassType(self.name, tuple(bases), {})
                self.man._prepare(model)
            return self.man

class AutomaticManipulator(forms.Manipulator):
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

    def __init__(self, follow=None):
        self.follow = self.opts.get_follow(follow)
        self.fields = []

        for f in self.opts.fields + self.opts.many_to_many:
            if self.follow.get(f.name, False):
                self.fields.extend(f.get_manipulator_fields(self.opts, self, self.change))

        # Add fields for related objects.
        for f in self.opts.get_all_related_objects():
            if self.follow.get(f.name, False):
                fol = self.follow[f.name]
                self.fields.extend(f.get_manipulator_fields(self.opts, self, self.change, fol))

        # Add field for ordering.
        if self.change and self.opts.get_ordered_objects():
            self.fields.append(formfields.CommaSeparatedIntegerField(field_name="order_"))

    def save(self, new_data):
        # TODO: big cleanup when core fields go -> use recursive manipulators.
        params = {}
        for f in self.opts.fields:
            # Fields with auto_now_add should keep their original value in the change stage.
            auto_now_add = self.change and getattr(f, 'auto_now_add', False)
            if self.follow.get(f.name, None) and not auto_now_add:
                param = f.get_manipulator_new_data(new_data)
            else:
                if self.change:
                    param = getattr(self.original_object, f.attname)
                else:
                    param = f.get_default()
            params[f.attname] = param

        if self.change:
            params[self.opts.pk.attname] = self.obj_key

        # First, save the basic object itself.
        new_object = self.model(**params)
        new_object.save()

        # Now that the object's been saved, save any uploaded files.
        for f in self.opts.fields:
            if isinstance(f, FileField):
                f.save_file(new_data, new_object, self.change and self.original_object or None, self.change, rel=False)

        # Calculate which primary fields have changed.
        if self.change:
            self.fields_added, self.fields_changed, self.fields_deleted = [], [], []
            for f in self.opts.fields:
                if not f.primary_key and str(getattr(self.original_object, f.attname)) != str(getattr(new_object, f.attname)):
                    self.fields_changed.append(f.verbose_name)

        # Save many-to-many objects. Example: Set sites for a poll.
        for f in self.opts.many_to_many:
            if self.follow.get(f.name, None):
                if not f.rel.edit_inline:
                    if f.rel.raw_id_admin:
                        new_vals = new_data.get(f.name, ())
                    else:
                        new_vals = new_data.getlist(f.name)
                    # First, clear the existing values.
                    rel_manager = getattr(new_object, f.name)
                    rel_manager.clear()
                    # Then, set the new values.
                    for n in new_vals:
                        rel_manager.add(f.rel.to._default_manager.get(pk=n))
                    # TODO: Add to 'fields_changed'

        expanded_data = DotExpandedDict(dict(new_data))
        # Save many-to-one objects. Example: Add the Choice objects for a Poll.
        for related in self.opts.get_all_related_objects():
            # Create obj_list, which is a DotExpandedDict such as this:
            # [('0', {'id': ['940'], 'choice': ['This is the first choice']}),
            #  ('1', {'id': ['941'], 'choice': ['This is the second choice']}),
            #  ('2', {'id': [''], 'choice': ['']})]
            child_follow = self.follow.get(related.name, None)

            if child_follow:
                obj_list = expanded_data[related.var_name].items()
                if not obj_list:
                    continue

                obj_list.sort(lambda x, y: cmp(int(x[0]), int(y[0])))

                # For each related item...
                for _, rel_new_data in obj_list:

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
                    if self.change:
                        if rel_new_data[related.opts.pk.name][0]:
                            try:
                                old_rel_obj = getattr(self.original_object, related.get_accessor_name()).get(**{'%s__exact' % related.opts.pk.name: rel_new_data[related.opts.pk.attname][0]})
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
                        elif (not self.change) and isinstance(f, AutoField):
                            param = None
                        elif self.change and (isinstance(f, FileField) or not child_follow.get(f.name, None)):
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
                                    f.save_file(rel_new_data, new_rel_obj, self.change and old_rel_obj or None, old_rel_obj is not None, rel=True)

                        # Calculate whether any fields have changed.
                        if self.change:
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
                                if self.change and was_changed:
                                    self.fields_changed.append('%s for %s "%s"' % (f.verbose_name, related.opts.verbose_name, new_rel_obj))

                    # If, in the change stage, all of the core fields were blank and
                    # the primary key (ID) was provided, delete the item.
                    if self.change and all_cores_blank and old_rel_obj:
                        new_rel_obj.delete()
                        self.fields_deleted.append('%s "%s"' % (related.opts.verbose_name, old_rel_obj))

        # Save the order, if applicable.
        if self.change and self.opts.get_ordered_objects():
            order = new_data['order_'] and map(int, new_data['order_'].split(',')) or []
            for rel_opts in self.opts.get_ordered_objects():
                getattr(new_object, 'set_%s_order' % rel_opts.object_name.lower())(order)
        return new_object

    def get_related_objects(self):
        return self.opts.get_followed_related_objects(self.follow)

    def flatten_data(self):
        new_data = {}
        obj = self.change and self.original_object or None
        for f in self.opts.get_data_holders(self.follow):
            fol = self.follow.get(f.name)
            new_data.update(f.flatten_data(fol, obj))
        return new_data

class AutomaticAddManipulator(AutomaticManipulator):
    change = False

class AutomaticChangeManipulator(AutomaticManipulator):
    change = True
    def __init__(self, obj_key, follow=None):
        self.obj_key = obj_key
        try:
            self.original_object = self.manager.get(pk=obj_key)
        except ObjectDoesNotExist:
            # If the object doesn't exist, this might be a manipulator for a
            # one-to-one related object that hasn't created its subobject yet.
            # For example, this might be a Restaurant for a Place that doesn't
            # yet have restaurant information.
            if self.opts.one_to_one_field:
                # Sanity check -- Make sure the "parent" object exists.
                # For example, make sure the Place exists for the Restaurant.
                # Let the ObjectDoesNotExist exception propagate up.
                limit_choices_to = self.opts.one_to_one_field.rel.limit_choices_to
                lookup_kwargs = {'%s__exact' % self.opts.one_to_one_field.rel.field_name: obj_key}
                self.opts.one_to_one_field.rel.to.get_model_module().complex_filter(limit_choices_to).get(**lookup_kwargs)
                params = dict([(f.attname, f.get_default()) for f in self.opts.fields])
                params[self.opts.pk.attname] = obj_key
                self.original_object = self.opts.get_model_module().Klass(**params)
            else:
                raise
        super(AutomaticChangeManipulator, self).__init__(follow=follow)

def manipulator_validator_unique_together(field_name_list, opts, self, field_data, all_data):
    from django.db.models.fields.related import ManyToOneRel
    from django.utils.text import get_text_list
    field_list = [opts.get_field(field_name) for field_name in field_name_list]
    if isinstance(field_list[0].rel, ManyToOneRel):
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
        if isinstance(f.rel, ManyToOneRel):
            kwargs['%s__pk' % f.name] = field_val
        else:
            kwargs['%s__iexact' % f.name] = field_val
    try:
        old_obj = self.manager.get(**kwargs)
    except ObjectDoesNotExist:
        return
    if hasattr(self, 'original_object') and self.original_object._get_pk_val() == old_obj._get_pk_val():
        pass
    else:
        raise validators.ValidationError, _("%(object)s with this %(type)s already exists for the given %(field)s.") % \
            {'object': capfirst(opts.verbose_name), 'type': field_list[0].verbose_name, 'field': get_text_list(field_name_list[1:], 'and')}

def manipulator_validator_unique_for_date(from_field, date_field, opts, lookup_type, self, field_data, all_data):
    from django.db.models.fields.related import ManyToOneRel
    date_str = all_data.get(date_field.get_manipulator_field_names('')[0], None)
    date_val = forms.DateField.html2python(date_str)
    if date_val is None:
        return # Date was invalid. This will be caught by another validator.
    lookup_kwargs = {'%s__year' % date_field.name: date_val.year}
    if isinstance(from_field.rel, ManyToOneRel):
        lookup_kwargs['%s__pk' % from_field.name] = field_data
    else:
        lookup_kwargs['%s__iexact' % from_field.name] = field_data
    if lookup_type in ('month', 'date'):
        lookup_kwargs['%s__month' % date_field.name] = date_val.month
    if lookup_type == 'date':
        lookup_kwargs['%s__day' % date_field.name] = date_val.day
    try:
        old_obj = self.manager.get(**lookup_kwargs)
    except ObjectDoesNotExist:
        return
    else:
        if hasattr(self, 'original_object') and self.original_object._get_pk_val() == old_obj._get_pk_val():
            pass
        else:
            format_string = (lookup_type == 'date') and '%B %d, %Y' or '%B %Y'
            raise validators.ValidationError, "Please enter a different %s. The one you entered is already being used for %s." % \
                (from_field.verbose_name, date_val.strftime(format_string))
