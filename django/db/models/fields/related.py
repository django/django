from django.db.models.fields import Field, IntegerField
from django.db.models.related import RelatedObject
from django.utils.translation import gettext_lazy, string_concat
from django.utils.functional import curry
from django.core import formfields


# Values for Relation.edit_inline.
TABULAR, STACKED = 1, 2

RECURSIVE_RELATIONSHIP_CONSTANT = 'self'

#HACK 
class RelatedField(object):
    pending_lookups = {}
    
    def add_lookup(cls, rel_cls, field):
        name = field.rel.to
        module = rel_cls.__module__
        key = (module, name)
        cls.pending_lookups.setdefault(key,[]).append( (rel_cls, field) )
    add_lookup = classmethod(add_lookup)
        
    def do_pending_lookups(cls, other_cls):
        key = (other_cls.__module__, other_cls.__name__)
        for (rel_cls,field) in cls.pending_lookups.setdefault(key,[]):
            field.rel.to = other_cls
            field.do_related_class(other_cls, rel_cls)
    do_pending_lookups = classmethod(do_pending_lookups)
    
    def contribute_to_class(self, cls, name):
        Field.contribute_to_class(self,cls,name)
        other = self.rel.to
        if isinstance(other, basestring):
            if other == RECURSIVE_RELATIONSHIP_CONSTANT:
                self.rel.to = cls.__name__
            self.add_lookup(cls, self)
        else:
            self.do_related_class(other, cls)

    def set_attributes_from_rel(self):
        self.name = self.name or (self.rel.to._meta.object_name.lower() + '_' + self.rel.to._meta.pk.name)
        self.verbose_name = self.verbose_name or self.rel.to._meta.verbose_name
        self.rel.field_name = self.rel.field_name or self.rel.to._meta.pk.name
        
    def do_related_class(self, other, cls):
        self.set_attributes_from_rel()
        related = RelatedObject(other._meta, cls, self)
        self.contribute_to_related_class(other, related)
        

#HACK
class SharedMethods(RelatedField):
    def get_attname(self):
        return '%s_id' % self.name
    
    def get_validator_unique_lookup_type(self):
        return '%s__%s__exact' % (self.name, self.rel.get_related_field().name)


class ForeignKey(SharedMethods,Field):
    empty_strings_allowed = False
    def __init__(self, to, to_field=None, **kwargs):
        try:
            to_name = to._meta.object_name.lower()
        except AttributeError: # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            assert isinstance(to, basestring) , """ForeignKey(%r) is invalid. First parameter to ForeignKey must be either 
                         a model, a model name, or the string %r""" % (to, RECURSIVE_RELATIONSHIP_CONSTANT)
            kwargs['verbose_name'] = kwargs.get('verbose_name', '')
        else:
            to_field = to_field or to._meta.pk.name
            kwargs['verbose_name'] = kwargs.get('verbose_name', to._meta.verbose_name)

        if kwargs.has_key('edit_inline_type'):
            import warnings
            warnings.warn("edit_inline_type is deprecated. Use edit_inline instead.")
            kwargs['edit_inline'] = kwargs.pop('edit_inline_type')

        kwargs['rel'] = ManyToOne(to, to_field,
            num_in_admin=kwargs.pop('num_in_admin', 3),
            min_num_in_admin=kwargs.pop('min_num_in_admin', None),
            max_num_in_admin=kwargs.pop('max_num_in_admin', None),
            num_extra_on_change=kwargs.pop('num_extra_on_change', 1),
            edit_inline=kwargs.pop('edit_inline', False),
            related_name=kwargs.pop('related_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            lookup_overrides=kwargs.pop('lookup_overrides', None),
            raw_id_admin=kwargs.pop('raw_id_admin', False))
        Field.__init__(self, **kwargs)
        
        if not self.db_index:
                self.db_index = True
    
    def prepare_field_objs_and_params(self, manipulator, name_prefix):
        params = {'validator_list': self.validator_list[:]}
        
        params['member_name'] = name_prefix + self.attname
        if self.rel.raw_id_admin:
            field_objs = self.get_manipulator_field_objs()
            params['validator_list'].append(curry(manipulator_valid_rel_key, self, manipulator))
        else:
            if self.radio_admin:
                field_objs = [formfields.RadioSelectField]
                params['ul_class'] = get_ul_class(self.radio_admin)
            else:
                if self.null:
                    field_objs = [formfields.NullSelectField]
                else:
                    field_objs = [formfields.SelectField]
            params['choices'] = self.get_choices_default()
        return (field_objs,params)

    def get_manipulator_field_objs(self):
        rel_field = self.rel.get_related_field()
        if self.rel.raw_id_admin and not isinstance(rel_field, AutoField):
            return rel_field.get_manipulator_field_objs()
        else:
            return [formfields.IntegerField]

    def get_db_prep_save(self,value):
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

    def contribute_to_related_class(self, cls, related):
        rel_obj_name = related.get_method_name_part()
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


class OneToOneField(SharedMethods, IntegerField):
    def __init__(self, to, to_field=None, **kwargs):
        kwargs['verbose_name'] = kwargs.get('verbose_name', 'ID')
        to_field = to_field or to._meta.pk.name

        if kwargs.has_key('edit_inline_type'):
            import warnings
            warnings.warn("edit_inline_type is deprecated. Use edit_inline instead.")
            kwargs['edit_inline'] = kwargs.pop('edit_inline_type')

        kwargs['rel'] = OneToOne(to, to_field,
            num_in_admin=kwargs.pop('num_in_admin', 0),
            edit_inline=kwargs.pop('edit_inline', False),
            related_name=kwargs.pop('related_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            lookup_overrides=kwargs.pop('lookup_overrides', None),
            raw_id_admin=kwargs.pop('raw_id_admin', False))
        kwargs['primary_key'] = True
        IntegerField.__init__(self, **kwargs)
        if not self.db_index:
           self.db_index = True

    def contribute_to_related_class(self, cls, related):
        rel_obj_name = related.get_method_name_part()
        # Add "get_thingie" methods for one-to-one related objects.
        # EXAMPLE: Place.get_restaurants_restaurant()
        setattr(cls, 'get_%s' % rel_obj_name,
                curry(cls._get_related, method_name='get_object',
                      rel_class=related.model, rel_field=related.field))


class ManyToManyField(RelatedField,Field):
    def __init__(self, to, **kwargs):
        kwargs['verbose_name'] = kwargs.get('verbose_name', to._meta.verbose_name_plural)
        kwargs['rel'] = ManyToMany(to, kwargs.pop('singular', None),
            num_in_admin=kwargs.pop('num_in_admin', 0),
            related_name=kwargs.pop('related_name', None),
            filter_interface=kwargs.pop('filter_interface', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            raw_id_admin=kwargs.pop('raw_id_admin', False))
        if kwargs["rel"].raw_id_admin:
            kwargs.setdefault("validator_list", []).append(self.isValidIDList)
        Field.__init__(self, **kwargs)
        if self.rel.raw_id_admin:
            msg = gettext_lazy(' Separate multiple IDs with commas.')
        else:
            msg = gettext_lazy(' Hold down "Control", or "Command" on a Mac, to select more than one.')
        self.help_text = string_concat( self.help_text , msg )
        

    def get_manipulator_field_objs(self):
        if self.rel.raw_id_admin:
            return [formfields.RawIdAdminField]
        else:
            choices = self.get_choices_default()
            return [curry(formfields.SelectMultipleField, size=min(max(len(choices), 5), 15), choices=choices)]

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
            instance_ids = [getattr(instance, self.rel.to._meta.pk.attname) for instance in get_list_func()]
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

    def contribute_to_related_class(self, cls, related):
        rel_obj_name = related.get_method_name_part()
        setattr(cls, 'get_%s' % rel_obj_name, curry(cls._get_related_many_to_many, method_name='get_object', rel_class=related.model , rel_field=related.field))
        setattr(cls, 'get_%s_count' % rel_obj_name, curry(cls._get_related_many_to_many, method_name='get_count', rel_class=related.model, rel_field=related.field))
        setattr(cls, 'get_%s_list' % rel_obj_name, curry(cls._get_related_many_to_many, method_name='get_list', rel_class=related.model, rel_field=related.field))
        if related.opts.app_label == cls._meta.app_label:
            func = curry(cls._set_related_many_to_many, cls, related.field)
            func.alters_data = True
            setattr(cls, 'set_%s' % related.opts.module_name, func)

    def set_attributes_from_rel(self):
        pass

class ManyToOne:
    def __init__(self, to, field_name, num_in_admin=3, min_num_in_admin=None,
        max_num_in_admin=None, num_extra_on_change=1, edit_inline=False,
        related_name=None, limit_choices_to=None, lookup_overrides=None, raw_id_admin=False):
        try:
            to._meta
        except AttributeError: # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            assert isinstance(to, basestring) , "'to' must be either a model, a model name or the string %r" % RECURSIVE_RELATIONSHIP_CONSTANT
        self.to, self.field_name = to, field_name
        self.num_in_admin, self.edit_inline = num_in_admin, edit_inline
        self.min_num_in_admin, self.max_num_in_admin = min_num_in_admin, max_num_in_admin
        self.num_extra_on_change, self.related_name = num_extra_on_change, related_name
        self.limit_choices_to = limit_choices_to or {}
        self.lookup_overrides = lookup_overrides or {}
        self.raw_id_admin = raw_id_admin

    def get_related_field(self):
        "Returns the Field in the 'to' object to which this relationship is tied."
        return self.to._meta.get_field(self.field_name)

class OneToOne(ManyToOne):
    def __init__(self, to, field_name, num_in_admin=0, edit_inline=False,
        related_name=None, limit_choices_to=None, lookup_overrides=None,
        raw_id_admin=False):
        self.to, self.field_name = to, field_name
        self.num_in_admin, self.edit_inline = num_in_admin, edit_inline
        self.related_name = related_name
        self.limit_choices_to = limit_choices_to or {}
        self.lookup_overrides = lookup_overrides or {}
        self.raw_id_admin = raw_id_admin


class ManyToMany:
    def __init__(self, to, singular=None, num_in_admin=0, related_name=None,
        filter_interface=None, limit_choices_to=None, raw_id_admin=False):
        self.to = to
        self.singular = singular or to._meta.object_name.lower()
        self.num_in_admin = num_in_admin
        self.related_name = related_name
        self.filter_interface = filter_interface
        self.limit_choices_to = limit_choices_to or {}
        self.edit_inline = False
        self.raw_id_admin = raw_id_admin
        assert not (self.raw_id_admin and self.filter_interface), "ManyToMany relationships may not use both raw_id_admin and filter_interface"
