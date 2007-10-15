import datetime
import operator
import re
import warnings

from django.conf import settings
from django.db import connection, transaction
from django.db.models.fields import DateField, FieldDoesNotExist
from django.db.models.query_utils import Q, QNot, EmptyResultSet
from django.db.models import signals, loading, sql
from django.dispatch import dispatcher
from django.utils.datastructures import SortedDict
from django.utils.encoding import smart_unicode
from django.contrib.contenttypes import generic

try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback

# Used to control how many objects are worked with at once in some cases (e.g.
# when deleting objects).
CHUNK_SIZE = 100

class _QuerySet(object):
    "Represents a lazy database lookup for a set of objects"
    def __init__(self, model=None):
        self.model = model
        self.query = sql.Query(self.model, connection)
        self._result_cache = None

    ########################
    # PYTHON MAGIC METHODS #
    ########################

    def __repr__(self):
        return repr(self._get_data())

    def __len__(self):
        return len(self._get_data())

    def __iter__(self):
        return iter(self._get_data())

    def __getitem__(self, k):
        "Retrieve an item or slice from the set of results."
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."

        if self._result_cache is not None:
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            qs.query.set_limits(k.start, k.stop)
            return k.step and list(qs)[::k.step] or qs
        try:
            qs = self._clone()
            qs.query.set_limits(k, k + 1)
            return list(qs)[0]
        except self.model.DoesNotExist, e:
            raise IndexError, e.args

    def __and__(self, other):
        combined = self._clone()
        combined.query.combine(other.query, sql.AND)
        return combined

    def __or__(self, other):
        combined = self._clone()
        combined.query.combine(other.query, sql.OR)
        return combined

    ####################################
    # METHODS THAT DO DATABASE QUERIES #
    ####################################

    def iterator(self):
        """
        An iterator over the results from applying this QuerySet to the
        database.
        """
        fill_cache = self.query.select_related
        max_depth = self.query.max_depth
        index_end = len(self.model._meta.fields)
        extra_select = self.query.extra_select.keys()
        extra_select.sort()
        for row in self.query.results_iter():
            if fill_cache:
                obj, index_end = get_cached_row(klass=self.model, row=row,
                        index_start=0, max_depth=max_depth)
            else:
                obj = self.model(*row[:index_end])
            for i, k in enumerate(extra_select):
                setattr(obj, k, row[index_end + i])
            yield obj

    def count(self):
        """
        Performs a SELECT COUNT() and returns the number of records as an
        integer.

        If the queryset is already cached (i.e. self._result_cache is set) this
        simply returns the length of the cached results set to avoid multiple
        SELECT COUNT(*) calls.
        """
        if self._result_cache is not None:
            return len(self._result_cache)

        return self.query.get_count()

    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.
        """
        clone = self.filter(*args, **kwargs)
        obj_list = list(clone)
        if len(obj_list) < 1:
            raise self.model.DoesNotExist("%s matching query does not exist."
                    % self.model._meta.object_name)
        assert len(obj_list) == 1, "get() returned more than one %s -- it returned %s! Lookup parameters were %s" % (self.model._meta.object_name, len(obj_list), kwargs)
        return obj_list[0]

    def create(self, **kwargs):
        """
        Create a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self.model(**kwargs)
        obj.save()
        return obj

    def get_or_create(self, **kwargs):
        """
        Looks up an object with the given kwargs, creating one if necessary.
        Returns a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        assert kwargs, \
                'get_or_create() must be passed at least one keyword argument'
        defaults = kwargs.pop('defaults', {})
        try:
            return self.get(**kwargs), False
        except self.model.DoesNotExist:
            params = dict([(k, v) for k, v in kwargs.items() if '__' not in k])
            params.update(defaults)
            obj = self.model(**params)
            obj.save()
            return obj, True

    def latest(self, field_name=None):
        """
        Returns the latest object, according to the model's 'get_latest_by'
        option or optional given field_name.
        """
        latest_by = field_name or self.model._meta.get_latest_by
        assert bool(latest_by), "latest() requires either a field_name parameter or 'get_latest_by' in the model"
        assert self.query.can_filter(), \
                "Cannot change a query once a slice has been taken."
        obj = self._clone()
        obj.query.set_limits(high=1)
        obj.query.add_ordering('-%s' % latest_by)
        return obj.get()

    def in_bulk(self, id_list):
        """
        Returns a dictionary mapping each of the given IDs to the object with
        that ID.
        """
        assert self.query.can_filter(), \
                "Cannot use 'limit' or 'offset' with in_bulk"
        assert isinstance(id_list, (tuple,  list)), \
                "in_bulk() must be provided with a list of IDs."
        if not id_list:
            return {}
        qs = self._clone()
        qs.query.add_filter(('pk__in', id_list))
        return dict([(obj._get_pk_val(), obj) for obj in qs.iterator()])

    # XXX Mostly DONE
    def delete(self):
        """
        Deletes the records in the current QuerySet.
        """
        assert self.query.can_filter(), \
                "Cannot use 'limit' or 'offset' with delete."

        del_query = self._clone()

        # Disable non-supported fields.
        del_query.query.select_related = False
        del_query.query.clear_ordering()

        # Delete objects in chunks to prevent the list of related objects from
        # becoming too long.
        more_objects = True
        while more_objects:
            # Collect all the objects to be deleted in this chunk, and all the
            # objects that are related to the objects that are to be deleted.
            seen_objs = SortedDict()
            more_objects = False
            for object in del_query[:CHUNK_SIZE]:
                more_objects = True
                object._collect_sub_objects(seen_objs)

            # If one or more objects were found, delete them.
            # Otherwise, stop looping.
            # FIXME: Does "if seen_objs:.." work here? If so, we can get rid of
            # more_objects.
            if more_objects:
                delete_objects(seen_objs)

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None
    delete.alters_data = True

    ##################################################
    # PUBLIC METHODS THAT RETURN A QUERYSET SUBCLASS #
    ##################################################

    def values(self, *fields):
        return self._clone(klass=ValuesQuerySet, setup=True, _fields=fields)

    def dates(self, field_name, kind, order='ASC'):
        """
        Returns a list of datetime objects representing all available dates
        for the given field_name, scoped to 'kind'.
        """
        assert kind in ("month", "year", "day"), \
                "'kind' must be one of 'year', 'month' or 'day'."
        assert order in ('ASC', 'DESC'), \
                "'order' must be either 'ASC' or 'DESC'."
        # Let the FieldDoesNotExist exception propagate.
        field = self.model._meta.get_field(field_name, many_to_many=False)
        assert isinstance(field, DateField), "%r isn't a DateField." \
                % field_name
        return self._clone(klass=DateQuerySet, setup=True, _field=field,
                _kind=kind, _order=order)

    ##################################################################
    # PUBLIC METHODS THAT ALTER ATTRIBUTES AND RETURN A NEW QUERYSET #
    ##################################################################

    def filter(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with the args ANDed to the existing
        set.
        """
        return self._filter_or_exclude(None, *args, **kwargs)

    def exclude(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with NOT (args) ANDed to the existing
        set.
        """
        return self._filter_or_exclude(QNot, *args, **kwargs)

    def _filter_or_exclude(self, mapper, *args, **kwargs):
        # mapper is a callable used to transform Q objects,
        # or None for identity transform.
        if mapper is None:
            mapper = lambda x: x
        if args or kwargs:
            assert self.query.can_filter(), \
                "Cannot filter a query once a slice has been taken."

        clone = self._clone()
        if kwargs:
            clone.query.add_q(mapper(Q(**kwargs)))
        for arg in args:
            clone.query.add_q(mapper(arg))
        return clone

    def complex_filter(self, filter_obj):
        """
        Returns a new QuerySet instance with filter_obj added to the filters.
        filter_obj can be a Q object (or anything with an add_to_query()
        method) or a dictionary of keyword lookup arguments.

        This exists to support framework features such as 'limit_choices_to',
        and usually it will be more natural to use other methods.
        """
        if isinstance(filter_obj, Q) or hasattr(filter_obj, 'add_to_query'):
            return self._filter_or_exclude(None, filter_obj)
        else:
            return self._filter_or_exclude(None, **filter_obj)

    def select_related(self, true_or_false=True, depth=0):
        """Returns a new QuerySet instance that will select related objects."""
        obj = self._clone()
        obj.query.select_related = true_or_false
        obj.query.max_depth = depth
        return obj

    def order_by(self, *field_names):
        """Returns a new QuerySet instance with the ordering changed."""
        assert self.query.can_filter(), \
                "Cannot reorder a query once a slice has been taken."
        obj = self._clone()
        obj.query.add_ordering(*field_names)
        return obj

    def distinct(self, true_or_false=True):
        """
        Returns a new QuerySet instance that will select only distinct results.
        """
        obj = self._clone()
        obj.query.distinct = true_or_false
        return obj

    def extra(self, select=None, where=None, params=None, tables=None,
            order_by=None):
        """
        Add extra SQL fragments to the query.
        """
        assert self.query.can_filter(), \
                "Cannot change a query once a slice has been taken"
        clone = self._clone()
        if select:
            clone.query.extra_select.update(select)
        if where:
            clone.query.extra_where.extend(where)
        if params:
            clone.query.extra_params.extend(params)
        if tables:
            clone.query.extra_tables.extend(tables)
        if order_by:
            clone.query.extra_order_by.extend(order_by)
        return clone

    ###################
    # PRIVATE METHODS #
    ###################

    def _clone(self, klass=None, setup=False, **kwargs):
        if klass is None:
            klass = self.__class__
        c = klass()
        c.model = self.model
        c.query = self.query.clone()
        c.__dict__.update(kwargs)
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

    def _get_data(self):
        if self._result_cache is None:
            self._result_cache = list(self.iterator())
        return self._result_cache

# Use the backend's QuerySet class if it defines one. Otherwise, use _QuerySet.
if connection.features.uses_custom_queryset:
    QuerySet = connection.ops.query_set_class(_QuerySet)
else:
    QuerySet = _QuerySet

class ValuesQuerySet(QuerySet):
    def __init__(self, *args, **kwargs):
        super(ValuesQuerySet, self).__init__(*args, **kwargs)
        # select_related isn't supported in values().
        self.query.select_related = False

        # QuerySet.clone() will also set up the _fields attribute with the
        # names of the model fields to select.

    def iterator(self):
        extra_select = self.query.extra_select.keys()
        extra_select.sort()
        if extra_select:
            self.field_names.extend([f for f in extra_select])

        for row in self.query.results_iter():
            yield dict(zip(self.field_names, row))

    def _setup_query(self):
        """
        Sets up any special features of the query attribute.

        Called by the _clone() method after initialising the rest of the
        instance.
        """
        # Construct two objects:
        #   - fields is a list of Field objects to fetch.
        #   - field_names is a list of field names, which will be the keys in
        #   the resulting dictionaries.
        # 'fields' is used to configure the query, whilst field_names is stored
        # in this object for use by iterator().
        if self._fields:
            opts = self.model._meta
            all = dict([(field.column, field) for field in opts.fields])
            all.update([(field.name, field) for field in opts.fields])
            if not self.query.extra_select:
                try:
                    fields = [all[f] for f in self._fields]
                except KeyError, e:
                    raise FieldDoesNotExist('%s has no field named %r'
                                % (opts.object_name, e.args[0]))
                field_names = self._fields
            else:
                fields = []
                field_names = []
                for f in self._fields:
                    if f in all:
                        fields.append(all[f])
                        field_names.append(f)
                    elif not self.query.extra_select.has_key(f):
                        raise FieldDoesNotExist('%s has no field named %r'
                                % (self.model._meta.object_name, f))
        else: # Default to all fields.
            fields = self.model._meta.fields
            field_names = [f.attname for f in fields]

        self.query.add_local_columns([f.column for f in fields])
        self.field_names = field_names

    def _clone(self, klass=None, setup=False, **kwargs):
        """
        Cloning a ValuesQuerySet preserves the current fields.
        """
        c = super(ValuesQuerySet, self)._clone(klass, **kwargs)
        c._fields = self._fields[:]
        c.field_names = self.field_names[:]
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

class DateQuerySet(QuerySet):
    def iterator(self):
        return self.query.results_iter()

    def _setup_query(self):
        """
        Sets up any special features of the query attribute.

        Called by the _clone() method after initialising the rest of the
        instance.
        """
        self.query = self.query.clone(klass=sql.DateQuery, setup=True)
        self.query.select = []
        self.query.add_date_select(self._field.column, self._kind, self._order)
        if self._field.null:
            self.query.add_filter(('%s__isnull' % self._field.name, True))

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(DateQuerySet, self)._clone(klass, False, **kwargs)
        c._field = self._field
        c._kind = self._kind
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

class EmptyQuerySet(QuerySet):
    def __init__(self, model=None):
        super(EmptyQuerySet, self).__init__(model)
        self._result_cache = []

    def count(self):
        return 0

    def delete(self):
        pass

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(EmptyQuerySet, self)._clone(klass, **kwargs)
        c._result_cache = []
        return c

    def iterator(self):
        # This slightly odd construction is because we need an empty generator
        # (it raises StopIteration immediately).
        yield iter([]).next()

# QOperator, QAnd and QOr are temporarily retained for backwards compatibility.
# All the old functionality is now part of the 'Q' class.
class QOperator(Q):
    def __init__(self, *args, **kwargs):
        warnings.warn('Use Q instead of QOr, QAnd or QOperation.',
                DeprecationWarning, stacklevel=2)

QOr = QAnd = QOperator

def get_cached_row(klass, row, index_start, max_depth=0, cur_depth=0):
    """Helper function that recursively returns an object with cache filled"""

    # If we've got a max_depth set and we've exceeded that depth, bail now.
    if max_depth and cur_depth > max_depth:
        return None

    index_end = index_start + len(klass._meta.fields)
    obj = klass(*row[index_start:index_end])
    for f in klass._meta.fields:
        if f.rel and not f.null:
            cached_row = get_cached_row(f.rel.to, row, index_end, max_depth, cur_depth+1)
            if cached_row:
                rel_obj, index_end = cached_row
                setattr(obj, f.get_cache_name(), rel_obj)
    return obj, index_end

def delete_objects(seen_objs):
    """
    Iterate through a list of seen classes, and remove any instances that are
    referred to.
    """
    ordered_classes = seen_objs.keys()
    ordered_classes.reverse()

    for cls in ordered_classes:
        seen_objs[cls] = seen_objs[cls].items()
        seen_objs[cls].sort()

        # Pre notify all instances to be deleted
        for pk_val, instance in seen_objs[cls]:
            dispatcher.send(signal=signals.pre_delete, sender=cls,
                    instance=instance)

        pk_list = [pk for pk,instance in seen_objs[cls]]
        del_query = sql.DeleteQuery(cls, connection)
        del_query.delete_batch_related(pk_list)

        update_query = sql.UpdateQuery(cls, connection)
        for field in cls._meta.fields:
            if field.rel and field.null and field.rel.to in seen_objs:
                update_query.clear_related(field, pk_list)

    # Now delete the actual data
    for cls in ordered_classes:
        seen_objs[cls].reverse()
        pk_list = [pk for pk,instance in seen_objs[cls]]
        del_query = sql.DeleteQuery(cls, connection)
        del_query.delete_batch(pk_list)

        # Last cleanup; set NULLs where there once was a reference to the
        # object, NULL the primary key of the found objects, and perform
        # post-notification.
        for pk_val, instance in seen_objs[cls]:
            for field in cls._meta.fields:
                if field.rel and field.null and field.rel.to in seen_objs:
                    setattr(instance, field.attname, None)

            setattr(instance, cls._meta.pk.attname, None)
            dispatcher.send(signal=signals.post_delete, sender=cls,
                    instance=instance)

    transaction.commit_unless_managed()

