from django.db.models import signals
from django.db.models.fields import AutoField, Field, IntegerField
from django.db.models.related import RelatedObject
from django.utils.translation import gettext_lazy, string_concat
from django.utils.functional import curry
from django.core import validators
from django import forms
from django.dispatch import dispatcher
import types

# Values for Relation.edit_inline.
TABULAR, STACKED = 1, 2

RECURSIVE_RELATIONSHIP_CONSTANT = 'self'

pending_lookups = {}

def add_lookup(rel_cls, field):
    name = field.rel.to
    module = rel_cls.__module__
    key = (module, name)
    pending_lookups.setdefault(key, []).append((rel_cls, field))

def do_pending_lookups(sender):
    other_cls = sender
    key = (other_cls.__module__, other_cls.__name__)
    for rel_cls, field in pending_lookups.setdefault(key, []):
        field.rel.to = other_cls
        field.do_related_class(other_cls, rel_cls)

dispatcher.connect(do_pending_lookups, signal=signals.class_prepared)

def manipulator_valid_rel_key(f, self, field_data, all_data):
    "Validates that the value is a valid foreign key"
    klass = f.rel.to
    try:
        klass._default_manager.get_object(pk=field_data)
    except klass.DoesNotExist:
        raise validators.ValidationError, _("Please enter a valid %s.") % f.verbose_name

#HACK
class RelatedField(object):
    def contribute_to_class(self, cls, name):
        sup = super(RelatedField, self)
        if hasattr(sup, 'contribute_to_class'):
            sup.contribute_to_class(cls, name)
        other = self.rel.to
        if isinstance(other, basestring):
            if other == RECURSIVE_RELATIONSHIP_CONSTANT:
                self.rel.to = cls.__name__
            add_lookup(cls, self)
        else:
            self.do_related_class(other, cls)

    def set_attributes_from_rel(self):
        self.name = self.name or (self.rel.to._meta.object_name.lower() + '_' + self.rel.to._meta.pk.name)
        self.verbose_name = self.verbose_name or self.rel.to._meta.verbose_name
        self.rel.field_name = self.rel.field_name or self.rel.to._meta.pk.name

    def do_related_class(self, other, cls):
        self.set_attributes_from_rel()
        related = RelatedObject(other, cls, self)
        self.contribute_to_related_class(other, related)

class RelatedObjectDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class.
    # In the example "poll.choice_set", the choice_set attribute is a
    # RelatedObjectDescriptor instance.
    def __init__(self, related):
        self.related = related # RelatedObject instance
        self.manager = None

    def __get__(self, instance, instance_type=None):
        if instance is None:
            raise AttributeError, "Manager must be accessed via instance"
        else:
            if not self.manager:
                # Dynamically create a class that subclasses the related
                # model's default manager.
                self.manager = types.ClassType('RelatedManager', (self.related.model._default_manager.__class__,), {})()

                # Set core_filters on the new manager to limit it to the
                # foreign-key relationship.
                rel_field = self.related.field
                self.manager.core_filters = {'%s__%s__exact' % (rel_field.name, rel_field.rel.to._meta.pk.name): getattr(instance, rel_field.rel.get_related_field().attname)}

                # Prepare the manager.
                # TODO: We need to set self.manager.klass because
                # self.manager._prepare() expects that self.manager.klass is
                # set. This is slightly hackish.
                self.manager.klass = self.related.model
                self.manager._prepare()

            return self.manager

class ForeignKey(RelatedField, Field):
    empty_strings_allowed = False
    def __init__(self, to, to_field=None, **kwargs):
        try:
            to_name = to._meta.object_name.lower()
        except AttributeError: # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            assert isinstance(to, basestring), "ForeignKey(%r) is invalid. First parameter to ForeignKey must be either a model, a model name, or the string %r" % (to, RECURSIVE_RELATIONSHIP_CONSTANT)
            kwargs['verbose_name'] = kwargs.get('verbose_name', '')
        else:
            to_field = to_field or to._meta.pk.name
            kwargs['verbose_name'] = kwargs.get('verbose_name', to._meta.verbose_name)

        if kwargs.has_key('edit_inline_type'):
            import warnings
            warnings.warn("edit_inline_type is deprecated. Use edit_inline instead.")
            kwargs['edit_inline'] = kwargs.pop('edit_inline_type')

        kwargs['rel'] = ManyToOne(to, to_field,
            edit_inline=kwargs.pop('edit_inline', False),
            related_name=kwargs.pop('related_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            lookup_overrides=kwargs.pop('lookup_overrides', None),
            raw_id_admin=kwargs.pop('raw_id_admin', False))
        Field.__init__(self, **kwargs)

        self.db_index = True

        for name in ('num_in_admin', 'min_num_in_admin', 'max_num_in_admin', 'num_extra_on_change'):
            if name in kwargs:
                self.deprecated_args.append(name)

    def get_attname(self):
        return '%s_id' % self.name

    def get_validator_unique_lookup_type(self):
        return '%s__%s__exact' % (self.name, self.rel.get_related_field().name)

    def prepare_field_objs_and_params(self, manipulator, name_prefix):
        params = {'validator_list': self.validator_list[:], 'member_name': name_prefix + self.attname}
        if self.rel.raw_id_admin:
            field_objs = self.get_manipulator_field_objs()
            params['validator_list'].append(curry(manipulator_valid_rel_key, self, manipulator))
        else:
            if self.radio_admin:
                field_objs = [forms.RadioSelectField]
                params['ul_class'] = get_ul_class(self.radio_admin)
            else:
                if self.null:
                    field_objs = [forms.NullSelectField]
                else:
                    field_objs = [forms.SelectField]
            params['choices'] = self.get_choices_default()
        return field_objs, params

    def get_manipulator_field_objs(self):
        rel_field = self.rel.get_related_field()
        if self.rel.raw_id_admin and not isinstance(rel_field, AutoField):
            return rel_field.get_manipulator_field_objs()
        else:
            return [forms.IntegerField]

    def get_db_prep_save(self, value):
        if value == '' or value == None:
            return None
        else:
            return self.rel.get_related_field().get_db_prep_save(value)

    def flatten_data(self, follow, obj=None):
        if not obj:
            # In required many-to-one fields with only one available choice,
            # select that one available choice. Note: For SelectFields
            # (radio_admin=False), we have to check that the length of choices
            # is *2*, not 1, because SelectFields always have an initial
            # "blank" value. Otherwise (radio_admin=True), we check that the
            # length is 1.
            if not self.blank and (not self.rel.raw_id_admin or self.choices):
                choice_list = self.get_choices_default()
                if self.radio_admin and len(choice_list) == 1:
                    return {self.attname: choice_list[0][0]}
                if not self.radio_admin and len(choice_list) == 2:
                    return {self.attname: choice_list[1][0]}
        return Field.flatten_data(self, follow, obj)

    def contribute_to_class(self, cls, name):
        super(ForeignKey, self).contribute_to_class(cls, name)
        # Add methods for many-to-one related objects.
        # EXAMPLES: Choice.get_poll(), Story.get_dateline()
        setattr(cls, 'get_%s' % self.name, curry(cls._get_foreign_key_object, field_with_rel=self))

    def contribute_to_related_class(self, cls, related):
        setattr(cls, related.get_accessor_name(), RelatedObjectDescriptor(related))

        # TODO: Delete the rest of this function and RelatedObject.OLD_get_accessor_name()
        # to remove support for old-style related lookup.

        rel_obj_name = related.OLD_get_accessor_name

        # Add "get_thingie" methods for many-to-one related objects.
        # EXAMPLE: Poll.get_choice()
        setattr(cls, 'get_%s' % rel_obj_name, curry(cls._get_related, method_name='get_object', rel_class=related.model, rel_field=related.field))
        # Add "get_thingie_count" methods for many-to-one related objects.
        # EXAMPLE: Poll.get_choice_count()
        setattr(cls, 'get_%s_count' % rel_obj_name, curry(cls._get_related, method_name='get_count', rel_class=related.model, rel_field=related.field))
        # Add "get_thingie_list" methods for many-to-one related objects.
        # EXAMPLE: Poll.get_choice_list()
        setattr(cls, 'get_%s_list' % rel_obj_name, curry(cls._get_related, method_name='get_list', rel_class=related.model, rel_field=related.field))
        # Add "add_thingie" methods for many-to-one related objects,
        # but only for related objects that are in the same app.
        # EXAMPLE: Poll.add_choice()
        if related.opts.app_label == cls._meta.app_label:
            func = lambda self, *args, **kwargs: self._add_related(related.model, related.field, *args, **kwargs)
            setattr(cls, 'add_%s' % rel_obj_name, func)

class OneToOneField(RelatedField, IntegerField):
    def __init__(self, to, to_field=None, **kwargs):
        kwargs['verbose_name'] = kwargs.get('verbose_name', 'ID')
        to_field = to_field or to._meta.pk.name

        if kwargs.has_key('edit_inline_type'):
            import warnings
            warnings.warn("edit_inline_type is deprecated. Use edit_inline instead.")
            kwargs['edit_inline'] = kwargs.pop('edit_inline_type')

        kwargs['rel'] = OneToOne(to, to_field,
            edit_inline=kwargs.pop('edit_inline', False),
            related_name=kwargs.pop('related_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            lookup_overrides=kwargs.pop('lookup_overrides', None),
            raw_id_admin=kwargs.pop('raw_id_admin', False))
        kwargs['primary_key'] = True
        IntegerField.__init__(self, **kwargs)

        self.db_index = True

        for name in ('num_in_admin'):
            if name in kwargs:
                self.deprecated_args.append(name)

    def get_attname(self):
        return '%s_id' % self.name

    def get_validator_unique_lookup_type(self):
        return '%s__%s__exact' % (self.name, self.rel.get_related_field().name)

    def contribute_to_class(self, cls, name):
        super(OneToOneField, self).contribute_to_class(cls, name)
        # Add methods for many-to-one related objects.
        # EXAMPLES: Choice.get_poll(), Story.get_dateline()
        setattr(cls, 'get_%s' % self.name, curry(cls._get_foreign_key_object, field_with_rel=self))

    def contribute_to_related_class(self, cls, related):
        rel_obj_name = related.OLD_get_accessor_name()
        # Add "get_thingie" methods for one-to-one related objects.
        # EXAMPLE: Place.get_restaurants_restaurant()
        setattr(cls, 'get_%s' % rel_obj_name,
                curry(cls._get_related, method_name='get_object',
                      rel_class=related.model, rel_field=related.field))
        if not cls._meta.one_to_one_field:
           cls._meta.one_to_one_field = self

class ManyToManyField(RelatedField, Field):
    def __init__(self, to, **kwargs):
        kwargs['verbose_name'] = kwargs.get('verbose_name', None)
        kwargs['rel'] = ManyToMany(to, kwargs.pop('singular', None),
            related_name=kwargs.pop('related_name', None),
            filter_interface=kwargs.pop('filter_interface', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            raw_id_admin=kwargs.pop('raw_id_admin', False))
        if kwargs["rel"].raw_id_admin:
            kwargs.setdefault("validator_list", []).append(self.isValidIDList)
        Field.__init__(self, **kwargs)
        for name in ('num_in_admin'):
            if name in kwargs:
                self.deprecated_args.append(name)

        if self.rel.raw_id_admin:
            msg = gettext_lazy('Separate multiple IDs with commas.')
        else:
            msg = gettext_lazy('Hold down "Control", or "Command" on a Mac, to select more than one.')
        self.help_text = string_concat(self.help_text, msg)

    def get_manipulator_field_objs(self):
        if self.rel.raw_id_admin:
            return [forms.RawIdAdminField]
        else:
            choices = self.get_choices_default()
            return [curry(forms.SelectMultipleField, size=min(max(len(choices), 5), 15), choices=choices)]

    def get_choices_default(self):
        return Field.get_choices(self, include_blank=False)

    def get_m2m_db_table(self, original_opts):
        "Returns the name of the many-to-many 'join' table."
        return '%s_%s' % (original_opts.db_table, self.name)

    def isValidIDList(self, field_data, all_data):
        "Validates that the value is a valid list of foreign keys"
        mod = self.rel.to._meta.get_model_module()
        try:
            pks = map(int, field_data.split(','))
        except ValueError:
            # the CommaSeparatedIntegerField validator will catch this error
            return
        objects = mod.get_in_bulk(pks)
        if len(objects) != len(pks):
            badkeys = [k for k in pks if k not in objects]
            raise validators.ValidationError, ngettext("Please enter valid %(self)s IDs. The value %(value)r is invalid.",
                    "Please enter valid %(self)s IDs. The values %(value)r are invalid.", len(badkeys)) % {
                'self': self.verbose_name,
                'value': len(badkeys) == 1 and badkeys[0] or tuple(badkeys),
            }

    def flatten_data(self, follow, obj = None):
        new_data = {}
        if obj:
            get_list_func = getattr(obj, 'get_%s_list' % self.rel.singular)
            instance_ids = [instance._get_pk_val() for instance in get_list_func()]
            if self.rel.raw_id_admin:
                 new_data[self.name] = ",".join([str(id) for id in instance_ids])
            else:
                 new_data[self.name] = instance_ids
        else:
            # In required many-to-many fields with only one available choice,
            # select that one available choice.
            if not self.blank and not self.rel.edit_inline and not self.rel.raw_id_admin:
               choices_list = self.get_choices_default()
               if len(choices_list) == 1:
                   new_data[self.name] = [choices_list[0][0]]
        return new_data

    def contribute_to_class(self, cls, name):
        super(ManyToManyField, self).contribute_to_class(cls, name)
        # Add "get_thingie" methods for many-to-many related objects.
        # EXAMPLES: Poll.get_site_list(), Story.get_byline_list()
        setattr(cls, 'get_%s_list' % self.rel.singular, curry(cls._get_many_to_many_objects, field_with_rel=self))

        # Add "set_thingie" methods for many-to-many related objects.
        # EXAMPLES: Poll.set_sites(), Story.set_bylines()
        setattr(cls, 'set_%s' % self.name, curry(cls._set_many_to_many_objects, field_with_rel=self))

    def contribute_to_related_class(self, cls, related):
        rel_obj_name = related.OLD_get_accessor_name()
        setattr(cls, 'get_%s' % rel_obj_name, curry(cls._get_related_many_to_many, method_name='get_object', rel_class=related.model, rel_field=related.field))
        setattr(cls, 'get_%s_count' % rel_obj_name, curry(cls._get_related_many_to_many, method_name='get_count', rel_class=related.model, rel_field=related.field))
        setattr(cls, 'get_%s_list' % rel_obj_name, curry(cls._get_related_many_to_many, method_name='get_list', rel_class=related.model, rel_field=related.field))
        if related.opts.app_label == cls._meta.app_label:
            func = curry(cls._set_related_many_to_many, cls, related.field)
            func.alters_data = True
            setattr(cls, 'set_%s' % related.opts.module_name, func)

        self.rel.singular = self.rel.singular or self.rel.to._meta.object_name.lower()

    def set_attributes_from_rel(self):
        pass

class ManyToOne:
    def __init__(self, to, field_name, edit_inline=False,
        related_name=None, limit_choices_to=None, lookup_overrides=None, raw_id_admin=False):
        try:
            to._meta
        except AttributeError:
            assert isinstance(to, basestring), "'to' must be either a model, a model name or the string %r" % RECURSIVE_RELATIONSHIP_CONSTANT
        self.to, self.field_name = to, field_name
        self.edit_inline = edit_inline
        self.related_name = related_name
        self.limit_choices_to = limit_choices_to or {}
        self.lookup_overrides = lookup_overrides or {}
        self.raw_id_admin = raw_id_admin

    def get_related_field(self):
        "Returns the Field in the 'to' object to which this relationship is tied."
        return self.to._meta.get_field(self.field_name)

class OneToOne(ManyToOne):
    def __init__(self, to, field_name, edit_inline=False,
        related_name=None, limit_choices_to=None, lookup_overrides=None,
        raw_id_admin=False):
        self.to, self.field_name = to, field_name
        self.edit_inline = edit_inline
        self.related_name = related_name
        self.limit_choices_to = limit_choices_to or {}
        self.lookup_overrides = lookup_overrides or {}
        self.raw_id_admin = raw_id_admin

class ManyToMany:
    def __init__(self, to, singular=None, related_name=None,
        filter_interface=None, limit_choices_to=None, raw_id_admin=False):
        self.to = to
        self.singular = singular or None
        self.related_name = related_name
        self.filter_interface = filter_interface
        self.limit_choices_to = limit_choices_to or {}
        self.edit_inline = False
        self.raw_id_admin = raw_id_admin
        assert not (self.raw_id_admin and self.filter_interface), "ManyToMany relationships may not use both raw_id_admin and filter_interface"
