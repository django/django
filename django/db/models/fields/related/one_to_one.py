from operator import attrgetter

from django.db import router
from django.db.models.fields.related.many_to_one import ManyToOneRel, ForeignKey
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _


class SingleRelatedObjectDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # a single "remote" value, on the class pointed to by a related field.
    # In the example "place.restaurant", the restaurant attribute is a
    # SingleRelatedObjectDescriptor instance.
    def __init__(self, related):
        self.related = related
        self.cache_name = related.get_cache_name()

    @cached_property
    def RelatedObjectDoesNotExist(self):
        # The exception isn't created at initialization time for the sake of
        # consistency with `ReverseSingleRelatedObjectDescriptor`.
        return type(
            str('RelatedObjectDoesNotExist'),
            (self.related.model.DoesNotExist, AttributeError),
            {}
        )

    def is_cached(self, instance):
        return hasattr(instance, self.cache_name)

    def get_queryset(self, **hints):
        manager = self.related.model._default_manager
        # If the related manager indicates that it should be used for
        # related fields, respect that.
        if not getattr(manager, 'use_for_related_fields', False):
            manager = self.related.model._base_manager
        return manager.db_manager(hints=hints).all()

    def get_prefetch_queryset(self, instances, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        queryset._add_hints(instance=instances[0])

        rel_obj_attr = attrgetter(self.related.field.attname)
        instance_attr = lambda obj: obj._get_pk_val()
        instances_dict = {instance_attr(inst): inst for inst in instances}
        query = {'%s__in' % self.related.field.name: instances}
        queryset = queryset.filter(**query)

        # Since we're going to assign directly in the cache,
        # we must manage the reverse relation cache manually.
        rel_obj_cache_name = self.related.field.get_cache_name()
        for rel_obj in queryset:
            instance = instances_dict[rel_obj_attr(rel_obj)]
            setattr(rel_obj, rel_obj_cache_name, instance)
        return queryset, rel_obj_attr, instance_attr, True, self.cache_name

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self
        try:
            rel_obj = getattr(instance, self.cache_name)
        except AttributeError:
            related_pk = instance._get_pk_val()
            if related_pk is None:
                rel_obj = None
            else:
                params = {}
                for lh_field, rh_field in self.related.field.related_fields:
                    params['%s__%s' % (self.related.field.name, rh_field.name)] = getattr(instance, rh_field.attname)
                try:
                    rel_obj = self.get_queryset(instance=instance).get(**params)
                except self.related.model.DoesNotExist:
                    rel_obj = None
                else:
                    setattr(rel_obj, self.related.field.get_cache_name(), instance)
            setattr(instance, self.cache_name, rel_obj)
        if rel_obj is None:
            raise self.RelatedObjectDoesNotExist(
                "%s has no %s." % (
                    instance.__class__.__name__,
                    self.related.get_accessor_name()
                )
            )
        else:
            return rel_obj

    def __set__(self, instance, value):
        # The similarity of the code below to the code in
        # ReverseSingleRelatedObjectDescriptor is annoying, but there's a bunch
        # of small differences that would make a common base class convoluted.

        # If null=True, we can assign null here, but otherwise the value needs
        # to be an instance of the related class.
        if value is None and self.related.field.null is False:
            raise ValueError(
                'Cannot assign None: "%s.%s" does not allow null values.' % (
                    instance._meta.object_name,
                    self.related.get_accessor_name(),
                )
            )
        elif value is not None and not isinstance(value, self.related.model):
            raise ValueError(
                'Cannot assign "%r": "%s.%s" must be a "%s" instance.' % (
                    value,
                    instance._meta.object_name,
                    self.related.get_accessor_name(),
                    self.related.opts.object_name,
                )
            )
        elif value is not None:
            if instance._state.db is None:
                instance._state.db = router.db_for_write(instance.__class__, instance=value)
            elif value._state.db is None:
                value._state.db = router.db_for_write(value.__class__, instance=instance)
            elif value._state.db is not None and instance._state.db is not None:
                if not router.allow_relation(value, instance):
                    raise ValueError('Cannot assign "%r": the current database router prevents this relation.' % value)

        related_pk = tuple(getattr(instance, field.attname) for field in self.related.field.foreign_related_fields)
        if None in related_pk:
            raise ValueError(
                'Cannot assign "%r": "%s" instance isn\'t saved in the database.' %
                (value, instance._meta.object_name)
            )

        # Set the value of the related field to the value of the related object's related field
        for index, field in enumerate(self.related.field.local_related_fields):
            setattr(value, field.attname, related_pk[index])

        # Since we already know what the related object is, seed the related
        # object caches now, too. This avoids another db hit if you get the
        # object you just set.
        setattr(instance, self.cache_name, value)
        setattr(value, self.related.field.get_cache_name(), instance)


class OneToOneRel(ManyToOneRel):
    def __init__(self, field, to, field_name, related_name=None, limit_choices_to=None,
                 parent_link=False, on_delete=None, related_query_name=None):
        super(OneToOneRel, self).__init__(field, to, field_name,
                related_name=related_name, limit_choices_to=limit_choices_to,
                parent_link=parent_link, on_delete=on_delete, related_query_name=related_query_name)
        self.multiple = False


class OneToOneField(ForeignKey):
    """
    A OneToOneField is essentially the same as a ForeignKey, with the exception
    that always carries a "unique" constraint with it and the reverse relation
    always returns the object pointed to (since there will only ever be one),
    rather than returning a list.
    """
    related_accessor_class = SingleRelatedObjectDescriptor
    description = _("One-to-one relationship")

    def __init__(self, to, to_field=None, **kwargs):
        kwargs['unique'] = True
        super(OneToOneField, self).__init__(to, to_field, OneToOneRel, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(OneToOneField, self).deconstruct()
        if "unique" in kwargs:
            del kwargs['unique']
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        if self.rel.parent_link:
            return None
        return super(OneToOneField, self).formfield(**kwargs)

    def save_form_data(self, instance, data):
        if isinstance(data, self.rel.to):
            setattr(instance, self.name, data)
        else:
            setattr(instance, self.attname, data)

    def _check_unique(self, **kwargs):
        # override ForeignKey since check isn't applicable here
        return []
