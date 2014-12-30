from django import forms
from django.core import checks, exceptions
from django.db import router
from django.db.models.fields import AutoField, FieldDoesNotExist, IntegerField, PositiveIntegerField, PositiveSmallIntegerField
from django.db.models.deletion import CASCADE, SET_NULL, SET_DEFAULT
from django.db.models.fields.related.base import ForeignObject, ForeignObjectRel, RECURSIVE_RELATIONSHIP_CONSTANT
from django.db.models.query_utils import PathInfo
from django.utils import six
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _


class ManyToOneRel(ForeignObjectRel):
    def __init__(self, field, to, field_name, related_name=None, limit_choices_to=None,
                 parent_link=False, on_delete=None, related_query_name=None):
        super(ManyToOneRel, self).__init__(
            field, to, related_name=related_name, limit_choices_to=limit_choices_to,
            parent_link=parent_link, on_delete=on_delete, related_query_name=related_query_name)
        self.field_name = field_name

    def get_related_field(self):
        """
        Returns the Field in the 'to' object to which this relationship is
        tied.
        """
        data = self.to._meta.get_field_by_name(self.field_name)
        if not data[2]:
            raise FieldDoesNotExist("No related field named '%s'" %
                    self.field_name)
        return data[0]

    def set_field_name(self):
        self.field_name = self.field_name or self.to._meta.pk.name


class ForeignKey(ForeignObject):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _('%(model)s instance with %(field)s %(value)r does not exist.')
    }
    description = _("Foreign Key (type determined by related field)")

    def __init__(self, to, to_field=None, rel_class=ManyToOneRel,
                 db_constraint=True, **kwargs):
        try:
            to._meta.model_name
        except AttributeError:  # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            assert isinstance(to, six.string_types), (
                "%s(%r) is invalid. First parameter to ForeignKey must be "
                "either a model, a model name, or the string %r" % (
                    self.__class__.__name__, to,
                    RECURSIVE_RELATIONSHIP_CONSTANT,
                )
            )
        else:
            # For backwards compatibility purposes, we need to *try* and set
            # the to_field during FK construction. It won't be guaranteed to
            # be correct until contribute_to_class is called. Refs #12190.
            to_field = to_field or (to._meta.pk and to._meta.pk.name)

        if 'db_index' not in kwargs:
            kwargs['db_index'] = True

        self.db_constraint = db_constraint

        kwargs['rel'] = rel_class(
            self, to, to_field,
            related_name=kwargs.pop('related_name', None),
            related_query_name=kwargs.pop('related_query_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            parent_link=kwargs.pop('parent_link', False),
            on_delete=kwargs.pop('on_delete', CASCADE),
        )
        super(ForeignKey, self).__init__(to, ['self'], [to_field], **kwargs)

    def check(self, **kwargs):
        errors = super(ForeignKey, self).check(**kwargs)
        errors.extend(self._check_on_delete())
        errors.extend(self._check_unique())
        return errors

    def _check_on_delete(self):
        on_delete = getattr(self.rel, 'on_delete', None)
        if on_delete == SET_NULL and not self.null:
            return [
                checks.Error(
                    'Field specifies on_delete=SET_NULL, but cannot be null.',
                    hint='Set null=True argument on the field, or change the on_delete rule.',
                    obj=self,
                    id='fields.E320',
                )
            ]
        elif on_delete == SET_DEFAULT and not self.has_default():
            return [
                checks.Error(
                    'Field specifies on_delete=SET_DEFAULT, but has no default value.',
                    hint='Set a default value, or change the on_delete rule.',
                    obj=self,
                    id='fields.E321',
                )
            ]
        else:
            return []

    def _check_unique(self, **kwargs):
        return [
            checks.Warning(
                'Setting unique=True on a ForeignKey has the same effect as using a OneToOneField.',
                hint='ForeignKey(unique=True) is usually better served by a OneToOneField.',
                obj=self,
                id='fields.W342',
            )
        ] if self.unique else []

    def deconstruct(self):
        name, path, args, kwargs = super(ForeignKey, self).deconstruct()
        del kwargs['to_fields']
        del kwargs['from_fields']
        # Handle the simpler arguments
        if self.db_index:
            del kwargs['db_index']
        else:
            kwargs['db_index'] = False
        if self.db_constraint is not True:
            kwargs['db_constraint'] = self.db_constraint
        # Rel needs more work.
        to_meta = getattr(self.rel.to, "_meta", None)
        if self.rel.field_name and (not to_meta or (to_meta.pk and self.rel.field_name != to_meta.pk.name)):
            kwargs['to_field'] = self.rel.field_name
        return name, path, args, kwargs

    @property
    def related_field(self):
        return self.foreign_related_fields[0]

    def get_reverse_path_info(self):
        """
        Get path from the related model to this field's model.
        """
        opts = self.model._meta
        from_opts = self.rel.to._meta
        pathinfos = [PathInfo(from_opts, opts, (opts.pk,), self.rel, not self.unique, False)]
        return pathinfos

    def validate(self, value, model_instance):
        if self.rel.parent_link:
            return
        super(ForeignKey, self).validate(value, model_instance)
        if value is None:
            return

        using = router.db_for_read(model_instance.__class__, instance=model_instance)
        qs = self.rel.to._default_manager.using(using).filter(
            **{self.rel.field_name: value}
        )
        qs = qs.complex_filter(self.get_limit_choices_to())
        if not qs.exists():
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={
                    'model': self.rel.to._meta.verbose_name, 'pk': value,
                    'field': self.rel.field_name, 'value': value,
                },  # 'pk' is included for backwards compatibility
            )

    def get_attname(self):
        return '%s_id' % self.name

    def get_attname_column(self):
        attname = self.get_attname()
        column = self.db_column or attname
        return attname, column

    def get_default(self):
        "Here we check if the default value is an object and return the to_field if so."
        field_default = super(ForeignKey, self).get_default()
        if isinstance(field_default, self.rel.to):
            return getattr(field_default, self.related_field.attname)
        return field_default

    def get_db_prep_save(self, value, connection):
        if value is None or (value == '' and
                             (not self.related_field.empty_strings_allowed or
                              connection.features.interprets_empty_strings_as_nulls)):
            return None
        else:
            return self.related_field.get_db_prep_save(value, connection=connection)

    def value_to_string(self, obj):
        if not obj:
            # In required many-to-one fields with only one available choice,
            # select that one available choice. Note: For SelectFields
            # we have to check that the length of choices is *2*, not 1,
            # because SelectFields always have an initial "blank" value.
            if not self.blank and self.choices:
                choice_list = self.get_choices_default()
                if len(choice_list) == 2:
                    return smart_text(choice_list[1][0])
        return super(ForeignKey, self).value_to_string(obj)

    def contribute_to_related_class(self, cls, related):
        super(ForeignKey, self).contribute_to_related_class(cls, related)
        if self.rel.field_name is None:
            self.rel.field_name = cls._meta.pk.name

    def formfield(self, **kwargs):
        db = kwargs.pop('using', None)
        if isinstance(self.rel.to, six.string_types):
            raise ValueError("Cannot create form field for %r yet, because "
                             "its related model %r has not been loaded yet" %
                             (self.name, self.rel.to))
        defaults = {
            'form_class': forms.ModelChoiceField,
            'queryset': self.rel.to._default_manager.using(db),
            'to_field_name': self.rel.field_name,
        }
        defaults.update(kwargs)
        return super(ForeignKey, self).formfield(**defaults)

    def db_type(self, connection):
        # The database column type of a ForeignKey is the column type
        # of the field to which it points. An exception is if the ForeignKey
        # points to an AutoField/PositiveIntegerField/PositiveSmallIntegerField,
        # in which case the column type is simply that of an IntegerField.
        # If the database needs similar types for key fields however, the only
        # thing we can do is making AutoField an IntegerField.
        rel_field = self.related_field
        if (isinstance(rel_field, AutoField) or
                (not connection.features.related_fields_match_type and
                isinstance(rel_field, (PositiveIntegerField,
                                       PositiveSmallIntegerField)))):
            return IntegerField().db_type(connection=connection)
        return rel_field.db_type(connection=connection)

    def db_parameters(self, connection):
        return {"type": self.db_type(connection), "check": []}
