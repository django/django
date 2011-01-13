from django.conf import settings
from django.db import connection, router, transaction
from django.db.backends import util
from django.db.models import signals, get_model
from django.db.models.fields import (AutoField, Field, IntegerField,
    PositiveIntegerField, PositiveSmallIntegerField, FieldDoesNotExist)
from django.db.models.related import RelatedObject
from django.db.models.query import QuerySet
from django.db.models.query_utils import QueryWrapper
from django.db.models.deletion import CASCADE
from django.utils.encoding import smart_unicode
from django.utils.translation import (ugettext_lazy as _, string_concat,
    ungettext, ugettext)
from django.utils.functional import curry
from django.core import exceptions
from django import forms


RECURSIVE_RELATIONSHIP_CONSTANT = 'self'

pending_lookups = {}

def add_lazy_relation(cls, field, relation, operation):
    """
    Adds a lookup on ``cls`` when a related field is defined using a string,
    i.e.::

        class MyModel(Model):
            fk = ForeignKey("AnotherModel")

    This string can be:

        * RECURSIVE_RELATIONSHIP_CONSTANT (i.e. "self") to indicate a recursive
          relation.

        * The name of a model (i.e "AnotherModel") to indicate another model in
          the same app.

        * An app-label and model name (i.e. "someapp.AnotherModel") to indicate
          another model in a different app.

    If the other model hasn't yet been loaded -- almost a given if you're using
    lazy relationships -- then the relation won't be set up until the
    class_prepared signal fires at the end of model initialization.

    operation is the work that must be performed once the relation can be resolved.
    """
    # Check for recursive relations
    if relation == RECURSIVE_RELATIONSHIP_CONSTANT:
        app_label = cls._meta.app_label
        model_name = cls.__name__

    else:
        # Look for an "app.Model" relation
        try:
            app_label, model_name = relation.split(".")
        except ValueError:
            # If we can't split, assume a model in current app
            app_label = cls._meta.app_label
            model_name = relation
        except AttributeError:
            # If it doesn't have a split it's actually a model class
            app_label = relation._meta.app_label
            model_name = relation._meta.object_name

    # Try to look up the related model, and if it's already loaded resolve the
    # string right away. If get_model returns None, it means that the related
    # model isn't loaded yet, so we need to pend the relation until the class
    # is prepared.
    model = get_model(app_label, model_name, False)
    if model:
        operation(field, model, cls)
    else:
        key = (app_label, model_name)
        value = (cls, field, operation)
        pending_lookups.setdefault(key, []).append(value)

def do_pending_lookups(sender, **kwargs):
    """
    Handle any pending relations to the sending model. Sent from class_prepared.
    """
    key = (sender._meta.app_label, sender.__name__)
    for cls, field, operation in pending_lookups.pop(key, []):
        operation(field, sender, cls)

signals.class_prepared.connect(do_pending_lookups)

#HACK
class RelatedField(object):
    def contribute_to_class(self, cls, name):
        sup = super(RelatedField, self)

        # Store the opts for related_query_name()
        self.opts = cls._meta

        if hasattr(sup, 'contribute_to_class'):
            sup.contribute_to_class(cls, name)

        if not cls._meta.abstract and self.rel.related_name:
            self.rel.related_name = self.rel.related_name % {
                    'class': cls.__name__.lower(),
                    'app_label': cls._meta.app_label.lower(),
                }

        other = self.rel.to
        if isinstance(other, basestring) or other._meta.pk is None:
            def resolve_related_class(field, model, cls):
                field.rel.to = model
                field.do_related_class(model, cls)
            add_lazy_relation(cls, self, other, resolve_related_class)
        else:
            self.do_related_class(other, cls)

    def set_attributes_from_rel(self):
        self.name = self.name or (self.rel.to._meta.object_name.lower() + '_' + self.rel.to._meta.pk.name)
        if self.verbose_name is None:
            self.verbose_name = self.rel.to._meta.verbose_name
        self.rel.field_name = self.rel.field_name or self.rel.to._meta.pk.name

    def do_related_class(self, other, cls):
        self.set_attributes_from_rel()
        self.related = RelatedObject(other, cls, self)
        if not cls._meta.abstract:
            self.contribute_to_related_class(other, self.related)

    def get_prep_lookup(self, lookup_type, value):
        if hasattr(value, 'prepare'):
            return value.prepare()
        if hasattr(value, '_prepare'):
            return value._prepare()
        # FIXME: lt and gt are explicitly allowed to make
        # get_(next/prev)_by_date work; other lookups are not allowed since that
        # gets messy pretty quick. This is a good candidate for some refactoring
        # in the future.
        if lookup_type in ['exact', 'gt', 'lt', 'gte', 'lte']:
            return self._pk_trace(value, 'get_prep_lookup', lookup_type)
        if lookup_type in ('range', 'in'):
            return [self._pk_trace(v, 'get_prep_lookup', lookup_type) for v in value]
        elif lookup_type == 'isnull':
            return []
        raise TypeError("Related Field has invalid lookup: %s" % lookup_type)

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_lookup(lookup_type, value)
        if hasattr(value, 'get_compiler'):
            value = value.get_compiler(connection=connection)
        if hasattr(value, 'as_sql') or hasattr(value, '_as_sql'):
            # If the value has a relabel_aliases method, it will need to
            # be invoked before the final SQL is evaluated
            if hasattr(value, 'relabel_aliases'):
                return value
            if hasattr(value, 'as_sql'):
                sql, params = value.as_sql()
            else:
                sql, params = value._as_sql(connection=connection)
            return QueryWrapper(('(%s)' % sql), params)

        # FIXME: lt and gt are explicitly allowed to make
        # get_(next/prev)_by_date work; other lookups are not allowed since that
        # gets messy pretty quick. This is a good candidate for some refactoring
        # in the future.
        if lookup_type in ['exact', 'gt', 'lt', 'gte', 'lte']:
            return [self._pk_trace(value, 'get_db_prep_lookup', lookup_type,
                            connection=connection, prepared=prepared)]
        if lookup_type in ('range', 'in'):
            return [self._pk_trace(v, 'get_db_prep_lookup', lookup_type,
                            connection=connection, prepared=prepared)
                    for v in value]
        elif lookup_type == 'isnull':
            return []
        raise TypeError("Related Field has invalid lookup: %s" % lookup_type)

    def _pk_trace(self, value, prep_func, lookup_type, **kwargs):
        # Value may be a primary key, or an object held in a relation.
        # If it is an object, then we need to get the primary key value for
        # that object. In certain conditions (especially one-to-one relations),
        # the primary key may itself be an object - so we need to keep drilling
        # down until we hit a value that can be used for a comparison.
        v = value
        try:
            while True:
                v = getattr(v, v._meta.pk.name)
        except AttributeError:
            pass
        except exceptions.ObjectDoesNotExist:
            v = None

        field = self
        while field.rel:
            if hasattr(field.rel, 'field_name'):
                field = field.rel.to._meta.get_field(field.rel.field_name)
            else:
                field = field.rel.to._meta.pk

        if lookup_type in ('range', 'in'):
            v = [v]
        v = getattr(field, prep_func)(lookup_type, v, **kwargs)
        if isinstance(v, list):
            v = v[0]
        return v

    def related_query_name(self):
        # This method defines the name that can be used to identify this
        # related object in a table-spanning query. It uses the lower-cased
        # object_name by default, but this can be overridden with the
        # "related_name" option.
        return self.rel.related_name or self.opts.object_name.lower()

class SingleRelatedObjectDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # a single "remote" value, on the class pointed to by a related field.
    # In the example "place.restaurant", the restaurant attribute is a
    # SingleRelatedObjectDescriptor instance.
    def __init__(self, related):
        self.related = related
        self.cache_name = related.get_cache_name()

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self
        try:
            return getattr(instance, self.cache_name)
        except AttributeError:
            params = {'%s__pk' % self.related.field.name: instance._get_pk_val()}
            db = router.db_for_read(self.related.model, instance=instance)
            rel_obj = self.related.model._base_manager.using(db).get(**params)
            setattr(instance, self.cache_name, rel_obj)
            return rel_obj

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("%s must be accessed via instance" % self.related.opts.object_name)

        # The similarity of the code below to the code in
        # ReverseSingleRelatedObjectDescriptor is annoying, but there's a bunch
        # of small differences that would make a common base class convoluted.

        # If null=True, we can assign null here, but otherwise the value needs
        # to be an instance of the related class.
        if value is None and self.related.field.null == False:
            raise ValueError('Cannot assign None: "%s.%s" does not allow null values.' %
                                (instance._meta.object_name, self.related.get_accessor_name()))
        elif value is not None and not isinstance(value, self.related.model):
            raise ValueError('Cannot assign "%r": "%s.%s" must be a "%s" instance.' %
                                (value, instance._meta.object_name,
                                 self.related.get_accessor_name(), self.related.opts.object_name))
        elif value is not None:
            if instance._state.db is None:
                instance._state.db = router.db_for_write(instance.__class__, instance=value)
            elif value._state.db is None:
                value._state.db = router.db_for_write(value.__class__, instance=instance)
            elif value._state.db is not None and instance._state.db is not None:
                if not router.allow_relation(value, instance):
                    raise ValueError('Cannot assign "%r": instance is on database "%s", value is on database "%s"' %
                                        (value, instance._state.db, value._state.db))

        # Set the value of the related field to the value of the related object's related field
        setattr(value, self.related.field.attname, getattr(instance, self.related.field.rel.get_related_field().attname))

        # Since we already know what the related object is, seed the related
        # object caches now, too. This avoids another db hit if you get the
        # object you just set.
        setattr(instance, self.cache_name, value)
        setattr(value, self.related.field.get_cache_name(), instance)

class ReverseSingleRelatedObjectDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # a single "remote" value, on the class that defines the related field.
    # In the example "choice.poll", the poll attribute is a
    # ReverseSingleRelatedObjectDescriptor instance.
    def __init__(self, field_with_rel):
        self.field = field_with_rel

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        cache_name = self.field.get_cache_name()
        try:
            return getattr(instance, cache_name)
        except AttributeError:
            val = getattr(instance, self.field.attname)
            if val is None:
                # If NULL is an allowed value, return it.
                if self.field.null:
                    return None
                raise self.field.rel.to.DoesNotExist
            other_field = self.field.rel.get_related_field()
            if other_field.rel:
                params = {'%s__pk' % self.field.rel.field_name: val}
            else:
                params = {'%s__exact' % self.field.rel.field_name: val}

            # If the related manager indicates that it should be used for
            # related fields, respect that.
            rel_mgr = self.field.rel.to._default_manager
            db = router.db_for_read(self.field.rel.to, instance=instance)
            if getattr(rel_mgr, 'use_for_related_fields', False):
                rel_obj = rel_mgr.using(db).get(**params)
            else:
                rel_obj = QuerySet(self.field.rel.to).using(db).get(**params)
            setattr(instance, cache_name, rel_obj)
            return rel_obj

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("%s must be accessed via instance" % self._field.name)

        # If null=True, we can assign null here, but otherwise the value needs
        # to be an instance of the related class.
        if value is None and self.field.null == False:
            raise ValueError('Cannot assign None: "%s.%s" does not allow null values.' %
                                (instance._meta.object_name, self.field.name))
        elif value is not None and not isinstance(value, self.field.rel.to):
            raise ValueError('Cannot assign "%r": "%s.%s" must be a "%s" instance.' %
                                (value, instance._meta.object_name,
                                 self.field.name, self.field.rel.to._meta.object_name))
        elif value is not None:
            if instance._state.db is None:
                instance._state.db = router.db_for_write(instance.__class__, instance=value)
            elif value._state.db is None:
                value._state.db = router.db_for_write(value.__class__, instance=instance)
            elif value._state.db is not None and instance._state.db is not None:
                if not router.allow_relation(value, instance):
                    raise ValueError('Cannot assign "%r": instance is on database "%s", value is on database "%s"' %
                                        (value, instance._state.db, value._state.db))

        # If we're setting the value of a OneToOneField to None, we need to clear
        # out the cache on any old related object. Otherwise, deleting the
        # previously-related object will also cause this object to be deleted,
        # which is wrong.
        if value is None:
            # Look up the previously-related object, which may still be available
            # since we've not yet cleared out the related field.
            # Use the cache directly, instead of the accessor; if we haven't
            # populated the cache, then we don't care - we're only accessing
            # the object to invalidate the accessor cache, so there's no
            # need to populate the cache just to expire it again.
            related = getattr(instance, self.field.get_cache_name(), None)

            # If we've got an old related object, we need to clear out its
            # cache. This cache also might not exist if the related object
            # hasn't been accessed yet.
            if related:
                cache_name = self.field.related.get_cache_name()
                try:
                    delattr(related, cache_name)
                except AttributeError:
                    pass

        # Set the value of the related field
        try:
            val = getattr(value, self.field.rel.get_related_field().attname)
        except AttributeError:
            val = None
        setattr(instance, self.field.attname, val)

        # Since we already know what the related object is, seed the related
        # object cache now, too. This avoids another db hit if you get the
        # object you just set.
        setattr(instance, self.field.get_cache_name(), value)

class ForeignRelatedObjectsDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # multiple "remote" values and have a ForeignKey pointed at them by
    # some other model. In the example "poll.choice_set", the choice_set
    # attribute is a ForeignRelatedObjectsDescriptor instance.
    def __init__(self, related):
        self.related = related   # RelatedObject instance

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        return self.create_manager(instance,
                self.related.model._default_manager.__class__)

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Manager must be accessed via instance")

        manager = self.__get__(instance)
        # If the foreign key can support nulls, then completely clear the related set.
        # Otherwise, just move the named objects into the set.
        if self.related.field.null:
            manager.clear()
        manager.add(*value)

    def delete_manager(self, instance):
        """
        Returns a queryset based on the related model's base manager (rather
        than the default manager, as returned by __get__). Used by
        Model.delete().
        """
        return self.create_manager(instance,
                self.related.model._base_manager.__class__)

    def create_manager(self, instance, superclass):
        """
        Creates the managers used by other methods (__get__() and delete()).
        """
        rel_field = self.related.field
        rel_model = self.related.model

        class RelatedManager(superclass):
            def get_query_set(self):
                db = self._db or router.db_for_read(rel_model, instance=instance)
                return superclass.get_query_set(self).using(db).filter(**(self.core_filters))

            def add(self, *objs):
                for obj in objs:
                    if not isinstance(obj, self.model):
                        raise TypeError("'%s' instance expected" % self.model._meta.object_name)
                    setattr(obj, rel_field.name, instance)
                    obj.save()
            add.alters_data = True

            def create(self, **kwargs):
                kwargs.update({rel_field.name: instance})
                db = router.db_for_write(rel_model, instance=instance)
                return super(RelatedManager, self.db_manager(db)).create(**kwargs)
            create.alters_data = True

            def get_or_create(self, **kwargs):
                # Update kwargs with the related object that this
                # ForeignRelatedObjectsDescriptor knows about.
                kwargs.update({rel_field.name: instance})
                db = router.db_for_write(rel_model, instance=instance)
                return super(RelatedManager, self.db_manager(db)).get_or_create(**kwargs)
            get_or_create.alters_data = True

            # remove() and clear() are only provided if the ForeignKey can have a value of null.
            if rel_field.null:
                def remove(self, *objs):
                    val = getattr(instance, rel_field.rel.get_related_field().attname)
                    for obj in objs:
                        # Is obj actually part of this descriptor set?
                        if getattr(obj, rel_field.attname) == val:
                            setattr(obj, rel_field.name, None)
                            obj.save()
                        else:
                            raise rel_field.rel.to.DoesNotExist("%r is not related to %r." % (obj, instance))
                remove.alters_data = True

                def clear(self):
                    for obj in self.all():
                        setattr(obj, rel_field.name, None)
                        obj.save()
                clear.alters_data = True

        manager = RelatedManager()
        attname = rel_field.rel.get_related_field().name
        manager.core_filters = {'%s__%s' % (rel_field.name, attname):
                getattr(instance, attname)}
        manager.model = self.related.model

        return manager

def create_many_related_manager(superclass, rel=False):
    """Creates a manager that subclasses 'superclass' (which is a Manager)
    and adds behavior for many-to-many related objects."""
    through = rel.through
    class ManyRelatedManager(superclass):
        def __init__(self, model=None, core_filters=None, instance=None, symmetrical=None,
                join_table=None, source_field_name=None, target_field_name=None,
                reverse=False):
            super(ManyRelatedManager, self).__init__()
            self.core_filters = core_filters
            self.model = model
            self.symmetrical = symmetrical
            self.instance = instance
            self.source_field_name = source_field_name
            self.target_field_name = target_field_name
            self.through = through
            self._pk_val = self.instance.pk
            self.reverse = reverse
            if self._pk_val is None:
                raise ValueError("%r instance needs to have a primary key value before a many-to-many relationship can be used." % instance.__class__.__name__)

        def get_query_set(self):
            db = self._db or router.db_for_read(self.instance.__class__, instance=self.instance)
            return superclass.get_query_set(self).using(db)._next_is_sticky().filter(**(self.core_filters))

        # If the ManyToMany relation has an intermediary model,
        # the add and remove methods do not exist.
        if rel.through._meta.auto_created:
            def add(self, *objs):
                self._add_items(self.source_field_name, self.target_field_name, *objs)

                # If this is a symmetrical m2m relation to self, add the mirror entry in the m2m table
                if self.symmetrical:
                    self._add_items(self.target_field_name, self.source_field_name, *objs)
            add.alters_data = True

            def remove(self, *objs):
                self._remove_items(self.source_field_name, self.target_field_name, *objs)

                # If this is a symmetrical m2m relation to self, remove the mirror entry in the m2m table
                if self.symmetrical:
                    self._remove_items(self.target_field_name, self.source_field_name, *objs)
            remove.alters_data = True

        def clear(self):
            self._clear_items(self.source_field_name)

            # If this is a symmetrical m2m relation to self, clear the mirror entry in the m2m table
            if self.symmetrical:
                self._clear_items(self.target_field_name)
        clear.alters_data = True

        def create(self, **kwargs):
            # This check needs to be done here, since we can't later remove this
            # from the method lookup table, as we do with add and remove.
            if not rel.through._meta.auto_created:
                opts = through._meta
                raise AttributeError("Cannot use create() on a ManyToManyField which specifies an intermediary model. Use %s.%s's Manager instead." % (opts.app_label, opts.object_name))
            db = router.db_for_write(self.instance.__class__, instance=self.instance)
            new_obj = super(ManyRelatedManager, self.db_manager(db)).create(**kwargs)
            self.add(new_obj)
            return new_obj
        create.alters_data = True

        def get_or_create(self, **kwargs):
            db = router.db_for_write(self.instance.__class__, instance=self.instance)
            obj, created = \
                super(ManyRelatedManager, self.db_manager(db)).get_or_create(**kwargs)
            # We only need to add() if created because if we got an object back
            # from get() then the relationship already exists.
            if created:
                self.add(obj)
            return obj, created
        get_or_create.alters_data = True

        def _add_items(self, source_field_name, target_field_name, *objs):
            # join_table: name of the m2m link table
            # source_field_name: the PK fieldname in join_table for the source object
            # target_field_name: the PK fieldname in join_table for the target object
            # *objs - objects to add. Either object instances, or primary keys of object instances.

            # If there aren't any objects, there is nothing to do.
            from django.db.models import Model
            if objs:
                new_ids = set()
                for obj in objs:
                    if isinstance(obj, self.model):
                        if not router.allow_relation(obj, self.instance):
                           raise ValueError('Cannot add "%r": instance is on database "%s", value is on database "%s"' %
                                               (obj, self.instance._state.db, obj._state.db))
                        new_ids.add(obj.pk)
                    elif isinstance(obj, Model):
                        raise TypeError("'%s' instance expected" % self.model._meta.object_name)
                    else:
                        new_ids.add(obj)
                db = router.db_for_write(self.through, instance=self.instance)
                vals = self.through._default_manager.using(db).values_list(target_field_name, flat=True)
                vals = vals.filter(**{
                    source_field_name: self._pk_val,
                    '%s__in' % target_field_name: new_ids,
                })
                new_ids = new_ids - set(vals)

                if self.reverse or source_field_name == self.source_field_name:
                    # Don't send the signal when we are inserting the
                    # duplicate data row for symmetrical reverse entries.
                    signals.m2m_changed.send(sender=rel.through, action='pre_add',
                        instance=self.instance, reverse=self.reverse,
                        model=self.model, pk_set=new_ids, using=db)
                # Add the ones that aren't there already
                for obj_id in new_ids:
                    self.through._default_manager.using(db).create(**{
                        '%s_id' % source_field_name: self._pk_val,
                        '%s_id' % target_field_name: obj_id,
                    })
                if self.reverse or source_field_name == self.source_field_name:
                    # Don't send the signal when we are inserting the
                    # duplicate data row for symmetrical reverse entries.
                    signals.m2m_changed.send(sender=rel.through, action='post_add',
                        instance=self.instance, reverse=self.reverse,
                        model=self.model, pk_set=new_ids, using=db)

        def _remove_items(self, source_field_name, target_field_name, *objs):
            # source_col_name: the PK colname in join_table for the source object
            # target_col_name: the PK colname in join_table for the target object
            # *objs - objects to remove

            # If there aren't any objects, there is nothing to do.
            if objs:
                # Check that all the objects are of the right type
                old_ids = set()
                for obj in objs:
                    if isinstance(obj, self.model):
                        old_ids.add(obj.pk)
                    else:
                        old_ids.add(obj)
                # Work out what DB we're operating on
                db = router.db_for_write(self.through, instance=self.instance)
                # Send a signal to the other end if need be.
                if self.reverse or source_field_name == self.source_field_name:
                    # Don't send the signal when we are deleting the
                    # duplicate data row for symmetrical reverse entries.
                    signals.m2m_changed.send(sender=rel.through, action="pre_remove",
                        instance=self.instance, reverse=self.reverse,
                        model=self.model, pk_set=old_ids, using=db)
                # Remove the specified objects from the join table
                self.through._default_manager.using(db).filter(**{
                    source_field_name: self._pk_val,
                    '%s__in' % target_field_name: old_ids
                }).delete()
                if self.reverse or source_field_name == self.source_field_name:
                    # Don't send the signal when we are deleting the
                    # duplicate data row for symmetrical reverse entries.
                    signals.m2m_changed.send(sender=rel.through, action="post_remove",
                        instance=self.instance, reverse=self.reverse,
                        model=self.model, pk_set=old_ids, using=db)

        def _clear_items(self, source_field_name):
            db = router.db_for_write(self.through, instance=self.instance)
            # source_col_name: the PK colname in join_table for the source object
            if self.reverse or source_field_name == self.source_field_name:
                # Don't send the signal when we are clearing the
                # duplicate data rows for symmetrical reverse entries.
                signals.m2m_changed.send(sender=rel.through, action="pre_clear",
                    instance=self.instance, reverse=self.reverse,
                    model=self.model, pk_set=None, using=db)
            self.through._default_manager.using(db).filter(**{
                source_field_name: self._pk_val
            }).delete()
            if self.reverse or source_field_name == self.source_field_name:
                # Don't send the signal when we are clearing the
                # duplicate data rows for symmetrical reverse entries.
                signals.m2m_changed.send(sender=rel.through, action="post_clear",
                    instance=self.instance, reverse=self.reverse,
                    model=self.model, pk_set=None, using=db)

    return ManyRelatedManager

class ManyRelatedObjectsDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # multiple "remote" values and have a ManyToManyField pointed at them by
    # some other model (rather than having a ManyToManyField themselves).
    # In the example "publication.article_set", the article_set attribute is a
    # ManyRelatedObjectsDescriptor instance.
    def __init__(self, related):
        self.related = related   # RelatedObject instance

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        # Dynamically create a class that subclasses the related
        # model's default manager.
        rel_model = self.related.model
        superclass = rel_model._default_manager.__class__
        RelatedManager = create_many_related_manager(superclass, self.related.field.rel)

        manager = RelatedManager(
            model=rel_model,
            core_filters={'%s__pk' % self.related.field.name: instance._get_pk_val()},
            instance=instance,
            symmetrical=False,
            source_field_name=self.related.field.m2m_reverse_field_name(),
            target_field_name=self.related.field.m2m_field_name(),
            reverse=True
        )

        return manager

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Manager must be accessed via instance")

        if not self.related.field.rel.through._meta.auto_created:
            opts = self.related.field.rel.through._meta
            raise AttributeError("Cannot set values on a ManyToManyField which specifies an intermediary model. Use %s.%s's Manager instead." % (opts.app_label, opts.object_name))

        manager = self.__get__(instance)
        manager.clear()
        manager.add(*value)


class ReverseManyRelatedObjectsDescriptor(object):
    # This class provides the functionality that makes the related-object
    # managers available as attributes on a model class, for fields that have
    # multiple "remote" values and have a ManyToManyField defined in their
    # model (rather than having another model pointed *at* them).
    # In the example "article.publications", the publications attribute is a
    # ReverseManyRelatedObjectsDescriptor instance.
    def __init__(self, m2m_field):
        self.field = m2m_field

    def _through(self):
        # through is provided so that you have easy access to the through
        # model (Book.authors.through) for inlines, etc. This is done as
        # a property to ensure that the fully resolved value is returned.
        return self.field.rel.through
    through = property(_through)

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        # Dynamically create a class that subclasses the related
        # model's default manager.
        rel_model=self.field.rel.to
        superclass = rel_model._default_manager.__class__
        RelatedManager = create_many_related_manager(superclass, self.field.rel)

        manager = RelatedManager(
            model=rel_model,
            core_filters={'%s__pk' % self.field.related_query_name(): instance._get_pk_val()},
            instance=instance,
            symmetrical=self.field.rel.symmetrical,
            source_field_name=self.field.m2m_field_name(),
            target_field_name=self.field.m2m_reverse_field_name(),
            reverse=False
        )

        return manager

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Manager must be accessed via instance")

        if not self.field.rel.through._meta.auto_created:
            opts = self.field.rel.through._meta
            raise AttributeError("Cannot set values on a ManyToManyField which specifies an intermediary model.  Use %s.%s's Manager instead." % (opts.app_label, opts.object_name))

        manager = self.__get__(instance)
        manager.clear()
        manager.add(*value)

class ManyToOneRel(object):
    def __init__(self, to, field_name, related_name=None, limit_choices_to=None,
        parent_link=False, on_delete=None):
        try:
            to._meta
        except AttributeError: # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            assert isinstance(to, basestring), "'to' must be either a model, a model name or the string %r" % RECURSIVE_RELATIONSHIP_CONSTANT
        self.to, self.field_name = to, field_name
        self.related_name = related_name
        if limit_choices_to is None:
            limit_choices_to = {}
        self.limit_choices_to = limit_choices_to
        self.multiple = True
        self.parent_link = parent_link
        self.on_delete = on_delete

    def is_hidden(self):
        "Should the related object be hidden?"
        return self.related_name and self.related_name[-1] == '+'

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

class OneToOneRel(ManyToOneRel):
    def __init__(self, to, field_name, related_name=None, limit_choices_to=None,
        parent_link=False, on_delete=None):
        super(OneToOneRel, self).__init__(to, field_name,
                related_name=related_name, limit_choices_to=limit_choices_to,
                parent_link=parent_link, on_delete=on_delete
        )
        self.multiple = False

class ManyToManyRel(object):
    def __init__(self, to, related_name=None, limit_choices_to=None,
            symmetrical=True, through=None):
        self.to = to
        self.related_name = related_name
        if limit_choices_to is None:
            limit_choices_to = {}
        self.limit_choices_to = limit_choices_to
        self.symmetrical = symmetrical
        self.multiple = True
        self.through = through

    def is_hidden(self):
        "Should the related object be hidden?"
        return self.related_name and self.related_name[-1] == '+'

    def get_related_field(self):
        """
        Returns the field in the to' object to which this relationship is tied
        (this is always the primary key on the target model). Provided for
        symmetry with ManyToOneRel.
        """
        return self.to._meta.pk

class ForeignKey(RelatedField, Field):
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _('Model %(model)s with pk %(pk)r does not exist.')
    }
    description = _("Foreign Key (type determined by related field)")
    def __init__(self, to, to_field=None, rel_class=ManyToOneRel, **kwargs):
        try:
            to_name = to._meta.object_name.lower()
        except AttributeError: # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            assert isinstance(to, basestring), "%s(%r) is invalid. First parameter to ForeignKey must be either a model, a model name, or the string %r" % (self.__class__.__name__, to, RECURSIVE_RELATIONSHIP_CONSTANT)
        else:
            assert not to._meta.abstract, "%s cannot define a relation with abstract class %s" % (self.__class__.__name__, to._meta.object_name)
            # For backwards compatibility purposes, we need to *try* and set
            # the to_field during FK construction. It won't be guaranteed to
            # be correct until contribute_to_class is called. Refs #12190.
            to_field = to_field or (to._meta.pk and to._meta.pk.name)
        kwargs['verbose_name'] = kwargs.get('verbose_name', None)

        if 'db_index' not in kwargs:
            kwargs['db_index'] = True

        kwargs['rel'] = rel_class(to, to_field,
            related_name=kwargs.pop('related_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            parent_link=kwargs.pop('parent_link', False),
            on_delete=kwargs.pop('on_delete', CASCADE),
        )
        Field.__init__(self, **kwargs)

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
        qs = qs.complex_filter(self.rel.limit_choices_to)
        if not qs.exists():
            raise exceptions.ValidationError(self.error_messages['invalid'] % {
                'model': self.rel.to._meta.verbose_name, 'pk': value})

    def get_attname(self):
        return '%s_id' % self.name

    def get_validator_unique_lookup_type(self):
        return '%s__%s__exact' % (self.name, self.rel.get_related_field().name)

    def get_default(self):
        "Here we check if the default value is an object and return the to_field if so."
        field_default = super(ForeignKey, self).get_default()
        if isinstance(field_default, self.rel.to):
            return getattr(field_default, self.rel.get_related_field().attname)
        return field_default

    def get_db_prep_save(self, value, connection):
        if value == '' or value == None:
            return None
        else:
            return self.rel.get_related_field().get_db_prep_save(value,
                connection=connection)

    def value_to_string(self, obj):
        if not obj:
            # In required many-to-one fields with only one available choice,
            # select that one available choice. Note: For SelectFields
            # we have to check that the length of choices is *2*, not 1,
            # because SelectFields always have an initial "blank" value.
            if not self.blank and self.choices:
                choice_list = self.get_choices_default()
                if len(choice_list) == 2:
                    return smart_unicode(choice_list[1][0])
        return Field.value_to_string(self, obj)

    def contribute_to_class(self, cls, name):
        super(ForeignKey, self).contribute_to_class(cls, name)
        setattr(cls, self.name, ReverseSingleRelatedObjectDescriptor(self))
        if isinstance(self.rel.to, basestring):
            target = self.rel.to
        else:
            target = self.rel.to._meta.db_table
        cls._meta.duplicate_targets[self.column] = (target, "o2m")

    def contribute_to_related_class(self, cls, related):
        # Internal FK's - i.e., those with a related name ending with '+' -
        # don't get a related descriptor.
        if not self.rel.is_hidden():
            setattr(cls, related.get_accessor_name(), ForeignRelatedObjectsDescriptor(related))
        if self.rel.field_name is None:
            self.rel.field_name = cls._meta.pk.name

    def formfield(self, **kwargs):
        db = kwargs.pop('using', None)
        defaults = {
            'form_class': forms.ModelChoiceField,
            'queryset': self.rel.to._default_manager.using(db).complex_filter(self.rel.limit_choices_to),
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
        rel_field = self.rel.get_related_field()
        if (isinstance(rel_field, AutoField) or
                (not connection.features.related_fields_match_type and
                isinstance(rel_field, (PositiveIntegerField,
                                       PositiveSmallIntegerField)))):
            return IntegerField().db_type(connection=connection)
        return rel_field.db_type(connection=connection)

class OneToOneField(ForeignKey):
    """
    A OneToOneField is essentially the same as a ForeignKey, with the exception
    that always carries a "unique" constraint with it and the reverse relation
    always returns the object pointed to (since there will only ever be one),
    rather than returning a list.
    """
    description = _("One-to-one relationship")
    def __init__(self, to, to_field=None, **kwargs):
        kwargs['unique'] = True
        super(OneToOneField, self).__init__(to, to_field, OneToOneRel, **kwargs)

    def contribute_to_related_class(self, cls, related):
        setattr(cls, related.get_accessor_name(),
                SingleRelatedObjectDescriptor(related))

    def formfield(self, **kwargs):
        if self.rel.parent_link:
            return None
        return super(OneToOneField, self).formfield(**kwargs)

    def save_form_data(self, instance, data):
        if isinstance(data, self.rel.to):
            setattr(instance, self.name, data)
        else:
            setattr(instance, self.attname, data)

def create_many_to_many_intermediary_model(field, klass):
    from django.db import models
    managed = True
    if isinstance(field.rel.to, basestring) and field.rel.to != RECURSIVE_RELATIONSHIP_CONSTANT:
        to_model = field.rel.to
        to = to_model.split('.')[-1]
        def set_managed(field, model, cls):
            field.rel.through._meta.managed = model._meta.managed or cls._meta.managed
        add_lazy_relation(klass, field, to_model, set_managed)
    elif isinstance(field.rel.to, basestring):
        to = klass._meta.object_name
        to_model = klass
        managed = klass._meta.managed
    else:
        to = field.rel.to._meta.object_name
        to_model = field.rel.to
        managed = klass._meta.managed or to_model._meta.managed
    name = '%s_%s' % (klass._meta.object_name, field.name)
    if field.rel.to == RECURSIVE_RELATIONSHIP_CONSTANT or to == klass._meta.object_name:
        from_ = 'from_%s' % to.lower()
        to = 'to_%s' % to.lower()
    else:
        from_ = klass._meta.object_name.lower()
        to = to.lower()
    meta = type('Meta', (object,), {
        'db_table': field._get_m2m_db_table(klass._meta),
        'managed': managed,
        'auto_created': klass,
        'app_label': klass._meta.app_label,
        'unique_together': (from_, to),
        'verbose_name': '%(from)s-%(to)s relationship' % {'from': from_, 'to': to},
        'verbose_name_plural': '%(from)s-%(to)s relationships' % {'from': from_, 'to': to},
    })
    # Construct and return the new class.
    return type(name, (models.Model,), {
        'Meta': meta,
        '__module__': klass.__module__,
        from_: models.ForeignKey(klass, related_name='%s+' % name),
        to: models.ForeignKey(to_model, related_name='%s+' % name)
    })

class ManyToManyField(RelatedField, Field):
    description = _("Many-to-many relationship")
    def __init__(self, to, **kwargs):
        try:
            assert not to._meta.abstract, "%s cannot define a relation with abstract class %s" % (self.__class__.__name__, to._meta.object_name)
        except AttributeError: # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            assert isinstance(to, basestring), "%s(%r) is invalid. First parameter to ManyToManyField must be either a model, a model name, or the string %r" % (self.__class__.__name__, to, RECURSIVE_RELATIONSHIP_CONSTANT)

        kwargs['verbose_name'] = kwargs.get('verbose_name', None)
        kwargs['rel'] = ManyToManyRel(to,
            related_name=kwargs.pop('related_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            symmetrical=kwargs.pop('symmetrical', to==RECURSIVE_RELATIONSHIP_CONSTANT),
            through=kwargs.pop('through', None))

        self.db_table = kwargs.pop('db_table', None)
        if kwargs['rel'].through is not None:
            assert self.db_table is None, "Cannot specify a db_table if an intermediary model is used."

        Field.__init__(self, **kwargs)

        msg = _('Hold down "Control", or "Command" on a Mac, to select more than one.')
        self.help_text = string_concat(self.help_text, ' ', msg)

    def get_choices_default(self):
        return Field.get_choices(self, include_blank=False)

    def _get_m2m_db_table(self, opts):
        "Function that can be curried to provide the m2m table name for this relation"
        if self.rel.through is not None:
            return self.rel.through._meta.db_table
        elif self.db_table:
            return self.db_table
        else:
            return util.truncate_name('%s_%s' % (opts.db_table, self.name),
                                      connection.ops.max_name_length())

    def _get_m2m_attr(self, related, attr):
        "Function that can be curried to provide the source accessor or DB column name for the m2m table"
        cache_attr = '_m2m_%s_cache' % attr
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)
        for f in self.rel.through._meta.fields:
            if hasattr(f,'rel') and f.rel and f.rel.to == related.model:
                setattr(self, cache_attr, getattr(f, attr))
                return getattr(self, cache_attr)

    def _get_m2m_reverse_attr(self, related, attr):
        "Function that can be curried to provide the related accessor or DB column name for the m2m table"
        cache_attr = '_m2m_reverse_%s_cache' % attr
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)
        found = False
        for f in self.rel.through._meta.fields:
            if hasattr(f,'rel') and f.rel and f.rel.to == related.parent_model:
                if related.model == related.parent_model:
                    # If this is an m2m-intermediate to self,
                    # the first foreign key you find will be
                    # the source column. Keep searching for
                    # the second foreign key.
                    if found:
                        setattr(self, cache_attr, getattr(f, attr))
                        break
                    else:
                        found = True
                else:
                    setattr(self, cache_attr, getattr(f, attr))
                    break
        return getattr(self, cache_attr)

    def value_to_string(self, obj):
        data = ''
        if obj:
            qs = getattr(obj, self.name).all()
            data = [instance._get_pk_val() for instance in qs]
        else:
            # In required many-to-many fields with only one available choice,
            # select that one available choice.
            if not self.blank:
                choices_list = self.get_choices_default()
                if len(choices_list) == 1:
                    data = [choices_list[0][0]]
        return smart_unicode(data)

    def contribute_to_class(self, cls, name):
        # To support multiple relations to self, it's useful to have a non-None
        # related name on symmetrical relations for internal reasons. The
        # concept doesn't make a lot of sense externally ("you want me to
        # specify *what* on my non-reversible relation?!"), so we set it up
        # automatically. The funky name reduces the chance of an accidental
        # clash.
        if self.rel.symmetrical and (self.rel.to == "self" or self.rel.to == cls._meta.object_name):
            self.rel.related_name = "%s_rel_+" % name

        super(ManyToManyField, self).contribute_to_class(cls, name)

        # The intermediate m2m model is not auto created if:
        #  1) There is a manually specified intermediate, or
        #  2) The class owning the m2m field is abstract.
        if not self.rel.through and not cls._meta.abstract:
            self.rel.through = create_many_to_many_intermediary_model(self, cls)

        # Add the descriptor for the m2m relation
        setattr(cls, self.name, ReverseManyRelatedObjectsDescriptor(self))

        # Set up the accessor for the m2m table name for the relation
        self.m2m_db_table = curry(self._get_m2m_db_table, cls._meta)

        # Populate some necessary rel arguments so that cross-app relations
        # work correctly.
        if isinstance(self.rel.through, basestring):
            def resolve_through_model(field, model, cls):
                field.rel.through = model
            add_lazy_relation(cls, self, self.rel.through, resolve_through_model)

        if isinstance(self.rel.to, basestring):
            target = self.rel.to
        else:
            target = self.rel.to._meta.db_table
        cls._meta.duplicate_targets[self.column] = (target, "m2m")

    def contribute_to_related_class(self, cls, related):
        # Internal M2Ms (i.e., those with a related name ending with '+')
        # don't get a related descriptor.
        if not self.rel.is_hidden():
            setattr(cls, related.get_accessor_name(), ManyRelatedObjectsDescriptor(related))

        # Set up the accessors for the column names on the m2m table
        self.m2m_column_name = curry(self._get_m2m_attr, related, 'column')
        self.m2m_reverse_name = curry(self._get_m2m_reverse_attr, related, 'column')

        self.m2m_field_name = curry(self._get_m2m_attr, related, 'name')
        self.m2m_reverse_field_name = curry(self._get_m2m_reverse_attr, related, 'name')

    def set_attributes_from_rel(self):
        pass

    def value_from_object(self, obj):
        "Returns the value of this field in the given model instance."
        return getattr(obj, self.attname).all()

    def save_form_data(self, instance, data):
        setattr(instance, self.attname, data)

    def formfield(self, **kwargs):
        db = kwargs.pop('using', None)
        defaults = {
            'form_class': forms.ModelMultipleChoiceField,
            'queryset': self.rel.to._default_manager.using(db).complex_filter(self.rel.limit_choices_to)
        }
        defaults.update(kwargs)
        # If initial is passed in, it's a list of related objects, but the
        # MultipleChoiceField takes a list of IDs.
        if defaults.get('initial') is not None:
            initial = defaults['initial']
            if callable(initial):
                initial = initial()
            defaults['initial'] = [i._get_pk_val() for i in initial]
        return super(ManyToManyField, self).formfield(**defaults)

    def db_type(self, connection):
        # A ManyToManyField is not represented by a single column,
        # so return None.
        return None
