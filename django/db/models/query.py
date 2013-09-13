"""
The main QuerySet implementation. This provides the public API for the ORM.
"""

import copy
import itertools
import sys
import warnings

from django.core import exceptions
from django.db import connections, router, transaction, IntegrityError
from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields import AutoField
from django.db.models.query_utils import (Q, select_related_descend,
    deferred_class_factory, InvalidQuery)
from django.db.models.deletion import Collector
from django.db.models import sql
from django.utils.functional import partition
from django.utils import six

# Used to control how many objects are worked with at once in some cases (e.g.
# when deleting objects).
CHUNK_SIZE = 100
ITER_CHUNK_SIZE = CHUNK_SIZE

# The maximum number of items to display in a QuerySet.__repr__
REPR_OUTPUT_SIZE = 20

# Pull into this namespace for backwards compatibility.
EmptyResultSet = sql.EmptyResultSet

class QuerySet(object):
    """
    Represents a lazy database lookup for a set of objects.
    """
    def __init__(self, model=None, query=None, using=None):
        self.model = model
        # EmptyQuerySet instantiates QuerySet with model as None
        self._db = using
        self.query = query or sql.Query(self.model)
        self._result_cache = None
        self._iter = None
        self._sticky_filter = False
        self._for_write = False
        self._prefetch_related_lookups = []
        self._prefetch_done = False
        self._known_related_objects = {}        # {rel_field, {pk: rel_obj}}

    ########################
    # PYTHON MAGIC METHODS #
    ########################

    def __deepcopy__(self, memo):
        """
        Deep copy of a QuerySet doesn't populate the cache
        """
        obj = self.__class__()
        for k,v in self.__dict__.items():
            if k in ('_iter','_result_cache'):
                obj.__dict__[k] = None
            else:
                obj.__dict__[k] = copy.deepcopy(v, memo)
        return obj

    def __getstate__(self):
        """
        Allows the QuerySet to be pickled.
        """
        # Force the cache to be fully populated.
        len(self)
        obj_dict = self.__dict__.copy()
        obj_dict['_iter'] = None
        obj_dict['_known_related_objects'] = dict(
            (field.name, val) for field, val in self._known_related_objects.items()
        )
        return obj_dict

    def __setstate__(self, obj_dict):
        model = obj_dict['model']
        if model is None:
            # if model is None, then self should be emptyqs and the related
            # objects do not matter.
            obj_dict['_known_related_objects'] = {}
        else:
            opts = model._meta
            obj_dict['_known_related_objects'] = dict(
                (opts.get_field(field.name if hasattr(field, 'name') else field), val)
                for field, val in obj_dict['_known_related_objects'].items()
            )
        self.__dict__.update(obj_dict)

    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)

    def __len__(self):
        # Since __len__ is called quite frequently (for example, as part of
        # list(qs), we make some effort here to be as efficient as possible
        # whilst not messing up any existing iterators against the QuerySet.
        if self._result_cache is None:
            if self._iter:
                self._result_cache = list(self._iter)
            else:
                self._result_cache = list(self.iterator())
        elif self._iter:
            self._result_cache.extend(self._iter)
        if self._prefetch_related_lookups and not self._prefetch_done:
            self._prefetch_related_objects()
        return len(self._result_cache)

    def __iter__(self):
        if self._prefetch_related_lookups and not self._prefetch_done:
            # We need all the results in order to be able to do the prefetch
            # in one go. To minimize code duplication, we use the __len__
            # code path which also forces this, and also does the prefetch
            len(self)

        if self._result_cache is None:
            self._iter = self.iterator()
            self._result_cache = []
        if self._iter:
            return self._result_iter()
        # Python's list iterator is better than our version when we're just
        # iterating over the cache.
        return iter(self._result_cache)

    def _result_iter(self):
        pos = 0
        while 1:
            upper = len(self._result_cache)
            while pos < upper:
                yield self._result_cache[pos]
                pos = pos + 1
            if not self._iter:
                raise StopIteration
            if len(self._result_cache) <= pos:
                self._fill_cache()

    def __bool__(self):
        if self._prefetch_related_lookups and not self._prefetch_done:
            # We need all the results in order to be able to do the prefetch
            # in one go. To minimize code duplication, we use the __len__
            # code path which also forces this, and also does the prefetch
            len(self)

        if self._result_cache is not None:
            return bool(self._result_cache)
        try:
            next(iter(self))
        except StopIteration:
            return False
        return True

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    def __contains__(self, val):
        # The 'in' operator works without this method, due to __iter__. This
        # implementation exists only to shortcut the creation of Model
        # instances, by bailing out early if we find a matching element.
        pos = 0
        if self._result_cache is not None:
            if val in self._result_cache:
                return True
            elif self._iter is None:
                # iterator is exhausted, so we have our answer
                return False
            # remember not to check these again:
            pos = len(self._result_cache)
        else:
            # We need to start filling the result cache out. The following
            # ensures that self._iter is not None and self._result_cache is not
            # None
            it = iter(self)

        # Carry on, one result at a time.
        while True:
            if len(self._result_cache) <= pos:
                self._fill_cache(num=1)
            if self._iter is None:
                # we ran out of items
                return False
            if self._result_cache[pos] == val:
                return True
            pos += 1

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice,) + six.integer_types):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."

        if self._result_cache is not None:
            if self._iter is not None:
                # The result cache has only been partially populated, so we may
                # need to fill it out a bit more.
                if isinstance(k, slice):
                    if k.stop is not None:
                        # Some people insist on passing in strings here.
                        bound = int(k.stop)
                    else:
                        bound = None
                else:
                    bound = k + 1
                if len(self._result_cache) < bound:
                    self._fill_cache(bound - len(self._result_cache))
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs.query.set_limits(start, stop)
            return k.step and list(qs)[::k.step] or qs
        try:
            qs = self._clone()
            qs.query.set_limits(k, k + 1)
            return list(qs)[0]
        except self.model.DoesNotExist as e:
            raise IndexError(e.args)

    def __and__(self, other):
        self._merge_sanity_check(other)
        if isinstance(other, EmptyQuerySet):
            return other._clone()
        combined = self._clone()
        combined._merge_known_related_objects(other)
        combined.query.combine(other.query, sql.AND)
        return combined

    def __or__(self, other):
        self._merge_sanity_check(other)
        combined = self._clone()
        if isinstance(other, EmptyQuerySet):
            return combined
        combined._merge_known_related_objects(other)
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
        fill_cache = False
        if connections[self.db].features.supports_select_related:
            fill_cache = self.query.select_related
        if isinstance(fill_cache, dict):
            requested = fill_cache
        else:
            requested = None
        max_depth = self.query.max_depth

        extra_select = list(self.query.extra_select)
        aggregate_select = list(self.query.aggregate_select)

        only_load = self.query.get_loaded_field_names()
        if not fill_cache:
            fields = self.model._meta.fields

        load_fields = []
        # If only/defer clauses have been specified,
        # build the list of fields that are to be loaded.
        if only_load:
            for field, model in self.model._meta.get_fields_with_model():
                if model is None:
                    model = self.model
                try:
                    if field.name in only_load[model]:
                        # Add a field that has been explicitly included
                        load_fields.append(field.name)
                except KeyError:
                    # Model wasn't explicitly listed in the only_load table
                    # Therefore, we need to load all fields from this model
                    load_fields.append(field.name)

        index_start = len(extra_select)
        aggregate_start = index_start + len(load_fields or self.model._meta.fields)

        skip = None
        if load_fields and not fill_cache:
            # Some fields have been deferred, so we have to initialise
            # via keyword arguments.
            skip = set()
            init_list = []
            for field in fields:
                if field.name not in load_fields:
                    skip.add(field.attname)
                else:
                    init_list.append(field.attname)
            model_cls = deferred_class_factory(self.model, skip)

        # Cache db and model outside the loop
        db = self.db
        model = self.model
        compiler = self.query.get_compiler(using=db)
        if fill_cache:
            klass_info = get_klass_info(model, max_depth=max_depth,
                                        requested=requested, only_load=only_load)
        for row in compiler.results_iter():
            if fill_cache:
                obj, _ = get_cached_row(row, index_start, db, klass_info,
                                        offset=len(aggregate_select))
            else:
                # Omit aggregates in object creation.
                row_data = row[index_start:aggregate_start]
                if skip:
                    obj = model_cls(**dict(zip(init_list, row_data)))
                else:
                    obj = model(*row_data)

                # Store the source database of the object
                obj._state.db = db
                # This object came from the database; it's not being added.
                obj._state.adding = False

            if extra_select:
                for i, k in enumerate(extra_select):
                    setattr(obj, k, row[i])

            # Add the aggregates to the model
            if aggregate_select:
                for i, aggregate in enumerate(aggregate_select):
                    setattr(obj, aggregate, row[i + aggregate_start])

            # Add the known related objects to the model, if there are any
            if self._known_related_objects:
                for field, rel_objs in self._known_related_objects.items():
                    pk = getattr(obj, field.get_attname())
                    try:
                        rel_obj = rel_objs[pk]
                    except KeyError:
                        pass               # may happen in qs1 | qs2 scenarios
                    else:
                        setattr(obj, field.name, rel_obj)

            yield obj

    def aggregate(self, *args, **kwargs):
        """
        Returns a dictionary containing the calculations (aggregation)
        over the current queryset

        If args is present the expression is passed as a kwarg using
        the Aggregate object's default alias.
        """
        if self.query.distinct_fields:
            raise NotImplementedError("aggregate() + distinct(fields) not implemented.")
        for arg in args:
            kwargs[arg.default_alias] = arg

        query = self.query.clone()

        for (alias, aggregate_expr) in kwargs.items():
            query.add_aggregate(aggregate_expr, self.model, alias,
                is_summary=True)

        return query.get_aggregation(using=self.db)

    def count(self):
        """
        Performs a SELECT COUNT() and returns the number of records as an
        integer.

        If the QuerySet is already fully cached this simply returns the length
        of the cached results set to avoid multiple SELECT COUNT(*) calls.
        """
        if self._result_cache is not None and not self._iter:
            return len(self._result_cache)

        return self.query.get_count(using=self.db)

    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.
        """
        clone = self.filter(*args, **kwargs)
        if self.query.can_filter():
            clone = clone.order_by()
        num = len(clone)
        if num == 1:
            return clone._result_cache[0]
        if not num:
            raise self.model.DoesNotExist(
                "%s matching query does not exist." %
                self.model._meta.object_name)
        raise self.model.MultipleObjectsReturned(
            "get() returned more than one %s -- it returned %s!" %
            (self.model._meta.object_name, num))

    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self.model(**kwargs)
        self._for_write = True
        obj.save(force_insert=True, using=self.db)
        return obj

    def bulk_create(self, objs, batch_size=None):
        """
        Inserts each of the instances into the database. This does *not* call
        save() on each of the instances, does not send any pre/post save
        signals, and does not set the primary key attribute if it is an
        autoincrement field.
        """
        # So this case is fun. When you bulk insert you don't get the primary
        # keys back (if it's an autoincrement), so you can't insert into the
        # child tables which references this. There are two workarounds, 1)
        # this could be implemented if you didn't have an autoincrement pk,
        # and 2) you could do it by doing O(n) normal inserts into the parent
        # tables to get the primary keys back, and then doing a single bulk
        # insert into the childmost table. Some databases might allow doing
        # this by using RETURNING clause for the insert query. We're punting
        # on these for now because they are relatively rare cases.
        assert batch_size is None or batch_size > 0
        if self.model._meta.parents:
            raise ValueError("Can't bulk create an inherited model")
        if not objs:
            return objs
        self._for_write = True
        connection = connections[self.db]
        fields = self.model._meta.local_fields
        if not transaction.is_managed(using=self.db):
            transaction.enter_transaction_management(using=self.db)
            forced_managed = True
        else:
            forced_managed = False
        try:
            if (connection.features.can_combine_inserts_with_and_without_auto_increment_pk
                and self.model._meta.has_auto_field):
                self._batched_insert(objs, fields, batch_size)
            else:
                objs_with_pk, objs_without_pk = partition(lambda o: o.pk is None, objs)
                if objs_with_pk:
                    self._batched_insert(objs_with_pk, fields, batch_size)
                if objs_without_pk:
                    fields= [f for f in fields if not isinstance(f, AutoField)]
                    self._batched_insert(objs_without_pk, fields, batch_size)
            if forced_managed:
                transaction.commit(using=self.db)
            else:
                transaction.commit_unless_managed(using=self.db)
        finally:
            if forced_managed:
                transaction.leave_transaction_management(using=self.db)

        return objs

    def get_or_create(self, **kwargs):
        """
        Looks up an object with the given kwargs, creating one if necessary.
        Returns a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        assert kwargs, \
                'get_or_create() must be passed at least one keyword argument'
        defaults = kwargs.pop('defaults', {})
        lookup = kwargs.copy()
        for f in self.model._meta.fields:
            if f.attname in lookup:
                lookup[f.name] = lookup.pop(f.attname)
        try:
            self._for_write = True
            return self.get(**lookup), False
        except self.model.DoesNotExist:
            try:
                params = dict([(k, v) for k, v in kwargs.items() if '__' not in k])
                params.update(defaults)
                obj = self.model(**params)
                sid = transaction.savepoint(using=self.db)
                obj.save(force_insert=True, using=self.db)
                transaction.savepoint_commit(sid, using=self.db)
                return obj, True
            except IntegrityError as e:
                transaction.savepoint_rollback(sid, using=self.db)
                exc_info = sys.exc_info()
                try:
                    return self.get(**lookup), False
                except self.model.DoesNotExist:
                    # Re-raise the IntegrityError with its original traceback.
                    six.reraise(*exc_info)

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
        obj.query.clear_ordering()
        obj.query.add_ordering('-%s' % latest_by)
        return obj.get()

    def in_bulk(self, id_list):
        """
        Returns a dictionary mapping each of the given IDs to the object with
        that ID.
        """
        assert self.query.can_filter(), \
                "Cannot use 'limit' or 'offset' with in_bulk"
        if not id_list:
            return {}
        qs = self.filter(pk__in=id_list).order_by()
        return dict([(obj._get_pk_val(), obj) for obj in qs])

    def delete(self):
        """
        Deletes the records in the current QuerySet.
        """
        assert self.query.can_filter(), \
                "Cannot use 'limit' or 'offset' with delete."

        del_query = self._clone()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._for_write = True

        # Disable non-supported fields.
        del_query.query.select_for_update = False
        del_query.query.select_related = False
        del_query.query.clear_ordering(force_empty=True)

        collector = Collector(using=del_query.db)
        collector.collect(del_query)
        collector.delete()

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None
    delete.alters_data = True

    def _raw_delete(self, using):
        """
        Deletes objects found from the given queryset in single direct SQL
        query. No signals are sent, and there is no protection for cascades.
        """
        sql.DeleteQuery(self.model).delete_qs(self, using)
    _raw_delete.alters_data = True

    def update(self, **kwargs):
        """
        Updates all elements in the current QuerySet, setting all the given
        fields to the appropriate values.
        """
        assert self.query.can_filter(), \
                "Cannot update a query once a slice has been taken."
        self._for_write = True
        query = self.query.clone(sql.UpdateQuery)
        query.add_update_values(kwargs)
        if not transaction.is_managed(using=self.db):
            transaction.enter_transaction_management(using=self.db)
            forced_managed = True
        else:
            forced_managed = False
        try:
            rows = query.get_compiler(self.db).execute_sql(None)
            if forced_managed:
                transaction.commit(using=self.db)
            else:
                transaction.commit_unless_managed(using=self.db)
        finally:
            if forced_managed:
                transaction.leave_transaction_management(using=self.db)
        self._result_cache = None
        return rows
    update.alters_data = True

    def _update(self, values):
        """
        A version of update that accepts field objects instead of field names.
        Used primarily for model saving and not intended for use by general
        code (it requires too much poking around at model internals to be
        useful at that level).
        """
        assert self.query.can_filter(), \
                "Cannot update a query once a slice has been taken."
        query = self.query.clone(sql.UpdateQuery)
        query.add_update_fields(values)
        self._result_cache = None
        return query.get_compiler(self.db).execute_sql(None)
    _update.alters_data = True

    def exists(self):
        if self._result_cache is None:
            return self.query.has_results(using=self.db)
        return bool(self._result_cache)

    def _prefetch_related_objects(self):
        # This method can only be called once the result cache has been filled.
        prefetch_related_objects(self._result_cache, self._prefetch_related_lookups)
        self._prefetch_done = True

    ##################################################
    # PUBLIC METHODS THAT RETURN A QUERYSET SUBCLASS #
    ##################################################

    def values(self, *fields):
        return self._clone(klass=ValuesQuerySet, setup=True, _fields=fields)

    def values_list(self, *fields, **kwargs):
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to values_list: %s'
                    % (list(kwargs),))
        if flat and len(fields) > 1:
            raise TypeError("'flat' is not valid when values_list is called with more than one field.")
        return self._clone(klass=ValuesListQuerySet, setup=True, flat=flat,
                _fields=fields)

    def dates(self, field_name, kind, order='ASC'):
        """
        Returns a list of datetime objects representing all available dates for
        the given field_name, scoped to 'kind'.
        """
        assert kind in ("month", "year", "day"), \
                "'kind' must be one of 'year', 'month' or 'day'."
        assert order in ('ASC', 'DESC'), \
                "'order' must be either 'ASC' or 'DESC'."
        return self._clone(klass=DateQuerySet, setup=True,
                _field_name=field_name, _kind=kind, _order=order)

    def none(self):
        """
        Returns an empty QuerySet.
        """
        return self._clone(klass=EmptyQuerySet)

    ##################################################################
    # PUBLIC METHODS THAT ALTER ATTRIBUTES AND RETURN A NEW QUERYSET #
    ##################################################################

    def all(self):
        """
        Returns a new QuerySet that is a copy of the current one. This allows a
        QuerySet to proxy for a model manager in some cases.
        """
        return self._clone()

    def filter(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with the args ANDed to the existing
        set.
        """
        return self._filter_or_exclude(False, *args, **kwargs)

    def exclude(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with NOT (args) ANDed to the existing
        set.
        """
        return self._filter_or_exclude(True, *args, **kwargs)

    def _filter_or_exclude(self, negate, *args, **kwargs):
        if args or kwargs:
            assert self.query.can_filter(), \
                    "Cannot filter a query once a slice has been taken."

        clone = self._clone()
        if negate:
            clone.query.add_q(~Q(*args, **kwargs))
        else:
            clone.query.add_q(Q(*args, **kwargs))
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
            clone = self._clone()
            clone.query.add_q(filter_obj)
            return clone
        else:
            return self._filter_or_exclude(None, **filter_obj)

    def select_for_update(self, **kwargs):
        """
        Returns a new QuerySet instance that will select objects with a
        FOR UPDATE lock.
        """
        # Default to false for nowait
        nowait = kwargs.pop('nowait', False)
        obj = self._clone()
        obj.query.select_for_update = True
        obj.query.select_for_update_nowait = nowait
        return obj

    def select_related(self, *fields, **kwargs):
        """
        Returns a new QuerySet instance that will select related objects.

        If fields are specified, they must be ForeignKey fields and only those
        related objects are included in the selection.
        """
        if 'depth' in kwargs:
            warnings.warn('The "depth" keyword argument has been deprecated.\n'
                    'Use related field names instead.', PendingDeprecationWarning)
        depth = kwargs.pop('depth', 0)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to select_related: %s'
                    % (list(kwargs),))
        obj = self._clone()
        if fields:
            if depth:
                raise TypeError('Cannot pass both "depth" and fields to select_related()')
            obj.query.add_select_related(fields)
        else:
            obj.query.select_related = True
        if depth:
            obj.query.max_depth = depth
        return obj

    def prefetch_related(self, *lookups):
        """
        Returns a new QuerySet instance that will prefetch the specified
        Many-To-One and Many-To-Many related objects when the QuerySet is
        evaluated.

        When prefetch_related() is called more than once, the list of lookups to
        prefetch is appended to. If prefetch_related(None) is called, the
        the list is cleared.
        """
        clone = self._clone()
        if lookups == (None,):
            clone._prefetch_related_lookups = []
        else:
            clone._prefetch_related_lookups.extend(lookups)
        return clone

    def dup_select_related(self, other):
        """
        Copies the related selection status from the QuerySet 'other' to the
        current QuerySet.
        """
        self.query.select_related = other.query.select_related

    def annotate(self, *args, **kwargs):
        """
        Return a query set in which the returned objects have been annotated
        with data aggregated from related fields.
        """
        for arg in args:
            if arg.default_alias in kwargs:
                raise ValueError("The named annotation '%s' conflicts with the "
                                 "default name for another annotation."
                                 % arg.default_alias)
            kwargs[arg.default_alias] = arg

        names = getattr(self, '_fields', None)
        if names is None:
            names = set(self.model._meta.get_all_field_names())
        for aggregate in kwargs:
            if aggregate in names:
                raise ValueError("The annotation '%s' conflicts with a field on "
                    "the model." % aggregate)

        obj = self._clone()

        obj._setup_aggregate_query(list(kwargs))

        # Add the aggregates to the query
        for (alias, aggregate_expr) in kwargs.items():
            obj.query.add_aggregate(aggregate_expr, self.model, alias,
                is_summary=False)

        return obj

    def order_by(self, *field_names):
        """
        Returns a new QuerySet instance with the ordering changed.
        """
        assert self.query.can_filter(), \
                "Cannot reorder a query once a slice has been taken."
        obj = self._clone()
        obj.query.clear_ordering()
        obj.query.add_ordering(*field_names)
        return obj

    def distinct(self, *field_names):
        """
        Returns a new QuerySet instance that will select only distinct results.
        """
        assert self.query.can_filter(), \
                "Cannot create distinct fields once a slice has been taken."
        obj = self._clone()
        obj.query.add_distinct_fields(*field_names)
        return obj

    def extra(self, select=None, where=None, params=None, tables=None,
              order_by=None, select_params=None):
        """
        Adds extra SQL fragments to the query.
        """
        assert self.query.can_filter(), \
                "Cannot change a query once a slice has been taken"
        clone = self._clone()
        clone.query.add_extra(select, select_params, where, params, tables, order_by)
        return clone

    def reverse(self):
        """
        Reverses the ordering of the QuerySet.
        """
        clone = self._clone()
        clone.query.standard_ordering = not clone.query.standard_ordering
        return clone

    def defer(self, *fields):
        """
        Defers the loading of data for certain fields until they are accessed.
        The set of fields to defer is added to any existing set of deferred
        fields. The only exception to this is if None is passed in as the only
        parameter, in which case all deferrals are removed (None acts as a
        reset option).
        """
        clone = self._clone()
        if fields == (None,):
            clone.query.clear_deferred_loading()
        else:
            clone.query.add_deferred_loading(fields)
        return clone

    def only(self, *fields):
        """
        Essentially, the opposite of defer. Only the fields passed into this
        method and that are not already specified as deferred are loaded
        immediately when the queryset is evaluated.
        """
        if fields == (None,):
            # Can only pass None to defer(), not only(), as the rest option.
            # That won't stop people trying to do this, so let's be explicit.
            raise TypeError("Cannot pass None as an argument to only().")
        clone = self._clone()
        clone.query.add_immediate_loading(fields)
        return clone

    def using(self, alias):
        """
        Selects which database this QuerySet should excecute its query against.
        """
        clone = self._clone()
        clone._db = alias
        return clone

    ###################################
    # PUBLIC INTROSPECTION ATTRIBUTES #
    ###################################

    def ordered(self):
        """
        Returns True if the QuerySet is ordered -- i.e. has an order_by()
        clause or a default ordering on the model.
        """
        if self.query.extra_order_by or self.query.order_by:
            return True
        elif self.query.default_ordering and self.query.model._meta.ordering:
            return True
        else:
            return False
    ordered = property(ordered)

    @property
    def db(self):
        "Return the database that will be used if this query is executed now"
        if self._for_write:
            return self._db or router.db_for_write(self.model)
        return self._db or router.db_for_read(self.model)

    ###################
    # PRIVATE METHODS #
    ###################
    def _batched_insert(self, objs, fields, batch_size):
        """
        A little helper method for bulk_insert to insert the bulk one batch
        at a time. Inserts recursively a batch from the front of the bulk and
        then _batched_insert() the remaining objects again.
        """
        if not objs:
            return
        ops = connections[self.db].ops
        batch_size = (batch_size or max(ops.bulk_batch_size(fields, objs), 1))
        for batch in [objs[i:i+batch_size]
                      for i in range(0, len(objs), batch_size)]:
            self.model._base_manager._insert(batch, fields=fields,
                                             using=self.db)

    def _clone(self, klass=None, setup=False, **kwargs):
        if klass is None:
            klass = self.__class__
        query = self.query.clone()
        if self._sticky_filter:
            query.filter_is_sticky = True
        c = klass(model=self.model, query=query, using=self._db)
        c._for_write = self._for_write
        c._prefetch_related_lookups = self._prefetch_related_lookups[:]
        c._known_related_objects = self._known_related_objects
        c.__dict__.update(kwargs)
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

    def _fill_cache(self, num=None):
        """
        Fills the result cache with 'num' more entries (or until the results
        iterator is exhausted).
        """
        if self._iter:
            try:
                for i in range(num or ITER_CHUNK_SIZE):
                    self._result_cache.append(next(self._iter))
            except StopIteration:
                self._iter = None

    def _next_is_sticky(self):
        """
        Indicates that the next filter call and the one following that should
        be treated as a single filter. This is only important when it comes to
        determining when to reuse tables for many-to-many filters. Required so
        that we can filter naturally on the results of related managers.

        This doesn't return a clone of the current QuerySet (it returns
        "self"). The method is only used internally and should be immediately
        followed by a filter() that does create a clone.
        """
        self._sticky_filter = True
        return self

    def _merge_sanity_check(self, other):
        """
        Checks that we are merging two comparable QuerySet classes. By default
        this does nothing, but see the ValuesQuerySet for an example of where
        it's useful.
        """
        pass

    def _merge_known_related_objects(self, other):
        """
        Keep track of all known related objects from either QuerySet instance.
        """
        for field, objects in other._known_related_objects.items():
            self._known_related_objects.setdefault(field, {}).update(objects)

    def _setup_aggregate_query(self, aggregates):
        """
        Prepare the query for computing a result that contains aggregate annotations.
        """
        opts = self.model._meta
        if self.query.group_by is None:
            field_names = [f.attname for f in opts.fields]
            self.query.add_fields(field_names, False)
            self.query.set_group_by()

    def _prepare(self):
        return self

    def _as_sql(self, connection):
        """
        Returns the internal query's SQL and parameters (as a tuple).
        """
        obj = self.values("pk")
        if obj._db is None or connection == connections[obj._db]:
            return obj.query.get_compiler(connection=connection).as_nested_sql()
        raise ValueError("Can't do subqueries with queries on different DBs.")

    # When used as part of a nested query, a queryset will never be an "always
    # empty" result.
    value_annotation = True


class ValuesQuerySet(QuerySet):
    def __init__(self, *args, **kwargs):
        super(ValuesQuerySet, self).__init__(*args, **kwargs)
        # select_related isn't supported in values(). (FIXME -#3358)
        self.query.select_related = False

        # QuerySet.clone() will also set up the _fields attribute with the
        # names of the model fields to select.

    def iterator(self):
        # Purge any extra columns that haven't been explicitly asked for
        extra_names = list(self.query.extra_select)
        field_names = self.field_names
        aggregate_names = list(self.query.aggregate_select)

        names = extra_names + field_names + aggregate_names

        for row in self.query.get_compiler(self.db).results_iter():
            yield dict(zip(names, row))

    def delete(self):
        # values().delete() doesn't work currently - make sure it raises an
        # user friendly error.
        raise TypeError("Queries with .values() or .values_list() applied "
                        "can't be deleted")

    def _setup_query(self):
        """
        Constructs the field_names list that the values query will be
        retrieving.

        Called by the _clone() method after initializing the rest of the
        instance.
        """
        self.query.clear_deferred_loading()
        self.query.clear_select_fields()

        if self._fields:
            self.extra_names = []
            self.aggregate_names = []
            if not self.query.extra and not self.query.aggregates:
                # Short cut - if there are no extra or aggregates, then
                # the values() clause must be just field names.
                self.field_names = list(self._fields)
            else:
                self.query.default_cols = False
                self.field_names = []
                for f in self._fields:
                    # we inspect the full extra_select list since we might
                    # be adding back an extra select item that we hadn't
                    # had selected previously.
                    if f in self.query.extra:
                        self.extra_names.append(f)
                    elif f in self.query.aggregate_select:
                        self.aggregate_names.append(f)
                    else:
                        self.field_names.append(f)
        else:
            # Default to all fields.
            self.extra_names = None
            self.field_names = [f.attname for f in self.model._meta.fields]
            self.aggregate_names = None

        self.query.select = []
        if self.extra_names is not None:
            self.query.set_extra_mask(self.extra_names)
        self.query.add_fields(self.field_names, True)
        if self.aggregate_names is not None:
            self.query.set_aggregate_mask(self.aggregate_names)

    def _clone(self, klass=None, setup=False, **kwargs):
        """
        Cloning a ValuesQuerySet preserves the current fields.
        """
        c = super(ValuesQuerySet, self)._clone(klass, **kwargs)
        if not hasattr(c, '_fields'):
            # Only clone self._fields if _fields wasn't passed into the cloning
            # call directly.
            c._fields = self._fields[:]
        c.field_names = self.field_names
        c.extra_names = self.extra_names
        c.aggregate_names = self.aggregate_names
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

    def _merge_sanity_check(self, other):
        super(ValuesQuerySet, self)._merge_sanity_check(other)
        if (set(self.extra_names) != set(other.extra_names) or
                set(self.field_names) != set(other.field_names) or
                self.aggregate_names != other.aggregate_names):
            raise TypeError("Merging '%s' classes must involve the same values in each case."
                    % self.__class__.__name__)

    def _setup_aggregate_query(self, aggregates):
        """
        Prepare the query for computing a result that contains aggregate annotations.
        """
        self.query.set_group_by()

        if self.aggregate_names is not None:
            self.aggregate_names.extend(aggregates)
            self.query.set_aggregate_mask(self.aggregate_names)

        super(ValuesQuerySet, self)._setup_aggregate_query(aggregates)

    def _as_sql(self, connection):
        """
        For ValueQuerySet (and subclasses like ValuesListQuerySet), they can
        only be used as nested queries if they're already set up to select only
        a single field (in which case, that is the field column that is
        returned). This differs from QuerySet.as_sql(), where the column to
        select is set up by Django.
        """
        if ((self._fields and len(self._fields) > 1) or
                (not self._fields and len(self.model._meta.fields) > 1)):
            raise TypeError('Cannot use a multi-field %s as a filter value.'
                    % self.__class__.__name__)

        obj = self._clone()
        if obj._db is None or connection == connections[obj._db]:
            return obj.query.get_compiler(connection=connection).as_nested_sql()
        raise ValueError("Can't do subqueries with queries on different DBs.")

    def _prepare(self):
        """
        Validates that we aren't trying to do a query like
        value__in=qs.values('value1', 'value2'), which isn't valid.
        """
        if ((self._fields and len(self._fields) > 1) or
                (not self._fields and len(self.model._meta.fields) > 1)):
            raise TypeError('Cannot use a multi-field %s as a filter value.'
                    % self.__class__.__name__)
        return self


class ValuesListQuerySet(ValuesQuerySet):
    def iterator(self):
        if self.flat and len(self._fields) == 1:
            for row in self.query.get_compiler(self.db).results_iter():
                yield row[0]
        elif not self.query.extra_select and not self.query.aggregate_select:
            for row in self.query.get_compiler(self.db).results_iter():
                yield tuple(row)
        else:
            # When extra(select=...) or an annotation is involved, the extra
            # cols are always at the start of the row, and we need to reorder
            # the fields to match the order in self._fields.
            extra_names = list(self.query.extra_select)
            field_names = self.field_names
            aggregate_names = list(self.query.aggregate_select)

            names = extra_names + field_names + aggregate_names

            # If a field list has been specified, use it. Otherwise, use the
            # full list of fields, including extras and aggregates.
            if self._fields:
                fields = list(self._fields) + [f for f in aggregate_names if f not in self._fields]
            else:
                fields = names

            for row in self.query.get_compiler(self.db).results_iter():
                data = dict(zip(names, row))
                yield tuple([data[f] for f in fields])

    def _clone(self, *args, **kwargs):
        clone = super(ValuesListQuerySet, self)._clone(*args, **kwargs)
        if not hasattr(clone, "flat"):
            # Only assign flat if the clone didn't already get it from kwargs
            clone.flat = self.flat
        return clone


class DateQuerySet(QuerySet):
    def iterator(self):
        return self.query.get_compiler(self.db).results_iter()

    def _setup_query(self):
        """
        Sets up any special features of the query attribute.

        Called by the _clone() method after initializing the rest of the
        instance.
        """
        self.query.clear_deferred_loading()
        self.query = self.query.clone(klass=sql.DateQuery, setup=True)
        self.query.select = []
        self.query.add_date_select(self._field_name, self._kind, self._order)

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(DateQuerySet, self)._clone(klass, False, **kwargs)
        c._field_name = self._field_name
        c._kind = self._kind
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c


class EmptyQuerySet(QuerySet):
    def __init__(self, model=None, query=None, using=None):
        super(EmptyQuerySet, self).__init__(model, query, using)
        self._result_cache = []

    def __and__(self, other):
        return self._clone()

    def __or__(self, other):
        return other._clone()

    def count(self):
        return 0

    def delete(self):
        pass

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(EmptyQuerySet, self)._clone(klass, setup=setup, **kwargs)
        c._result_cache = []
        return c

    def iterator(self):
        # This slightly odd construction is because we need an empty generator
        # (it raises StopIteration immediately).
        yield next(iter([]))

    def all(self):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def filter(self, *args, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def exclude(self, *args, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def complex_filter(self, filter_obj):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def select_related(self, *fields, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def annotate(self, *args, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def order_by(self, *field_names):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def distinct(self, *field_names):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def extra(self, select=None, where=None, params=None, tables=None,
              order_by=None, select_params=None):
        """
        Always returns EmptyQuerySet.
        """
        assert self.query.can_filter(), \
                "Cannot change a query once a slice has been taken"
        return self

    def reverse(self):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def defer(self, *fields):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def only(self, *fields):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def update(self, **kwargs):
        """
        Don't update anything.
        """
        return 0

    def aggregate(self, *args, **kwargs):
        """
        Return a dict mapping the aggregate names to None
        """
        for arg in args:
            kwargs[arg.default_alias] = arg
        return dict([(key, None) for key in kwargs])

    def values(self, *fields):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def values_list(self, *fields, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        return self

    # EmptyQuerySet is always an empty result in where-clauses (and similar
    # situations).
    value_annotation = False

def get_klass_info(klass, max_depth=0, cur_depth=0, requested=None,
                   only_load=None, local_only=False):
    """
    Helper function that recursively returns an information for a klass, to be
    used in get_cached_row.  It exists just to compute this information only
    once for entire queryset. Otherwise it would be computed for each row, which
    leads to poor perfomance on large querysets.

    Arguments:
     * klass - the class to retrieve (and instantiate)
     * max_depth - the maximum depth to which a select_related()
       relationship should be explored.
     * cur_depth - the current depth in the select_related() tree.
       Used in recursive calls to determin if we should dig deeper.
     * requested - A dictionary describing the select_related() tree
       that is to be retrieved. keys are field names; values are
       dictionaries describing the keys on that related object that
       are themselves to be select_related().
     * only_load - if the query has had only() or defer() applied,
       this is the list of field names that will be returned. If None,
       the full field list for `klass` can be assumed.
     * local_only - Only populate local fields. This is used when
       following reverse select-related relations
    """
    if max_depth and requested is None and cur_depth > max_depth:
        # We've recursed deeply enough; stop now.
        return None

    if only_load:
        load_fields = only_load.get(klass) or set()
        # When we create the object, we will also be creating populating
        # all the parent classes, so traverse the parent classes looking
        # for fields that must be included on load.
        for parent in klass._meta.get_parent_list():
            fields = only_load.get(parent)
            if fields:
                load_fields.update(fields)
    else:
        load_fields = None

    if load_fields:
        # Handle deferred fields.
        skip = set()
        init_list = []
        # Build the list of fields that *haven't* been requested
        for field, model in klass._meta.get_fields_with_model():
            if field.name not in load_fields:
                skip.add(field.attname)
            elif local_only and model is not None:
                continue
            else:
                init_list.append(field.attname)
        # Retrieve all the requested fields
        field_count = len(init_list)
        if skip:
            klass = deferred_class_factory(klass, skip)
            field_names = init_list
        else:
            field_names = ()
    else:
        # Load all fields on klass

        # We trying to not populate field_names variable for perfomance reason.
        # If field_names variable is set, it is used to instantiate desired fields,
        # by passing **dict(zip(field_names, fields)) as kwargs to Model.__init__ method.
        # But kwargs version of Model.__init__ is slower, so we should avoid using
        # it when it is not really neccesary.
        if local_only and len(klass._meta.local_fields) != len(klass._meta.fields):
            field_count = len(klass._meta.local_fields)
            field_names = [f.attname for f in klass._meta.local_fields]
        else:
            field_count = len(klass._meta.fields)
            field_names = ()

    restricted = requested is not None

    related_fields = []
    for f in klass._meta.fields:
        if select_related_descend(f, restricted, requested, load_fields):
            if restricted:
                next = requested[f.name]
            else:
                next = None
            klass_info = get_klass_info(f.rel.to, max_depth=max_depth, cur_depth=cur_depth+1,
                                        requested=next, only_load=only_load)
            related_fields.append((f, klass_info))

    reverse_related_fields = []
    if restricted:
        for o in klass._meta.get_all_related_objects():
            if o.field.unique and select_related_descend(o.field, restricted, requested,
                                                         only_load.get(o.model), reverse=True):
                next = requested[o.field.related_query_name()]
                klass_info = get_klass_info(o.model, max_depth=max_depth, cur_depth=cur_depth+1,
                                            requested=next, only_load=only_load, local_only=True)
                reverse_related_fields.append((o.field, klass_info))
    if field_names:
        pk_idx = field_names.index(klass._meta.pk.attname)
    else:
        pk_idx = klass._meta.pk_index()

    return klass, field_names, field_count, related_fields, reverse_related_fields, pk_idx


def get_cached_row(row, index_start, using,  klass_info, offset=0):
    """
    Helper function that recursively returns an object with the specified
    related attributes already populated.

    This method may be called recursively to populate deep select_related()
    clauses.

    Arguments:
         * row - the row of data returned by the database cursor
         * index_start - the index of the row at which data for this
           object is known to start
         * offset - the number of additional fields that are known to
           exist in row for `klass`. This usually means the number of
           annotated results on `klass`.
        * using - the database alias on which the query is being executed.
         * klass_info - result of the get_klass_info function
    """
    if klass_info is None:
        return None
    klass, field_names, field_count, related_fields, reverse_related_fields, pk_idx = klass_info

    fields = row[index_start : index_start + field_count]
    # If the pk column is None (or the Oracle equivalent ''), then the related
    # object must be non-existent - set the relation to None.
    if fields[pk_idx] == None or fields[pk_idx] == '':
        obj = None
    elif field_names:
        obj = klass(**dict(zip(field_names, fields)))
    else:
        obj = klass(*fields)

    # If an object was retrieved, set the database state.
    if obj:
        obj._state.db = using
        obj._state.adding = False

    # Instantiate related fields
    index_end = index_start + field_count + offset
    # Iterate over each related object, populating any
    # select_related() fields
    for f, klass_info in related_fields:
        # Recursively retrieve the data for the related object
        cached_row = get_cached_row(row, index_end, using, klass_info)
        # If the recursive descent found an object, populate the
        # descriptor caches relevant to the object
        if cached_row:
            rel_obj, index_end = cached_row
            if obj is not None:
                # If the base object exists, populate the
                # descriptor cache
                setattr(obj, f.get_cache_name(), rel_obj)
            if f.unique and rel_obj is not None:
                # If the field is unique, populate the
                # reverse descriptor cache on the related object
                setattr(rel_obj, f.related.get_cache_name(), obj)

    # Now do the same, but for reverse related objects.
    # Only handle the restricted case - i.e., don't do a depth
    # descent into reverse relations unless explicitly requested
    for f, klass_info in reverse_related_fields:
        # Recursively retrieve the data for the related object
        cached_row = get_cached_row(row, index_end, using, klass_info)
        # If the recursive descent found an object, populate the
        # descriptor caches relevant to the object
        if cached_row:
            rel_obj, index_end = cached_row
            if obj is not None:
                # If the field is unique, populate the
                # reverse descriptor cache
                setattr(obj, f.related.get_cache_name(), rel_obj)
            if rel_obj is not None:
                # If the related object exists, populate
                # the descriptor cache.
                setattr(rel_obj, f.get_cache_name(), obj)
                # Now populate all the non-local field values on the related
                # object. If this object has deferred fields, we need to use
                # the opts from the original model to get non-local fields
                # correctly.
                opts = rel_obj._meta
                if getattr(rel_obj, '_deferred'):
                    opts = opts.proxy_for_model._meta
                for rel_field, rel_model in opts.get_fields_with_model():
                    if rel_model is not None:
                        setattr(rel_obj, rel_field.attname, getattr(obj, rel_field.attname))
                        # populate the field cache for any related object
                        # that has already been retrieved
                        if rel_field.rel:
                            try:
                                cached_obj = getattr(obj, rel_field.get_cache_name())
                                setattr(rel_obj, rel_field.get_cache_name(), cached_obj)
                            except AttributeError:
                                # Related object hasn't been cached yet
                                pass
    return obj, index_end


class RawQuerySet(object):
    """
    Provides an iterator which converts the results of raw SQL queries into
    annotated model instances.
    """
    def __init__(self, raw_query, model=None, query=None, params=None,
        translations=None, using=None):
        self.raw_query = raw_query
        self.model = model
        self._db = using
        self.query = query or sql.RawQuery(sql=raw_query, using=self.db, params=params)
        self.params = params or ()
        self.translations = translations or {}

    def __iter__(self):
        # Mapping of attrnames to row column positions. Used for constructing
        # the model using kwargs, needed when not all model's fields are present
        # in the query.
        model_init_field_names = {}
        # A list of tuples of (column name, column position). Used for
        # annotation fields.
        annotation_fields = []

        # Cache some things for performance reasons outside the loop.
        db = self.db
        compiler = connections[db].ops.compiler('SQLCompiler')(
            self.query, connections[db], db
        )
        need_resolv_columns = hasattr(compiler, 'resolve_columns')

        query = iter(self.query)

        # Find out which columns are model's fields, and which ones should be
        # annotated to the model.
        for pos, column in enumerate(self.columns):
            if column in self.model_fields:
                model_init_field_names[self.model_fields[column].attname] = pos
            else:
                annotation_fields.append((column, pos))

        # Find out which model's fields are not present in the query.
        skip = set()
        for field in self.model._meta.fields:
            if field.attname not in model_init_field_names:
                skip.add(field.attname)
        if skip:
            if self.model._meta.pk.attname in skip:
                raise InvalidQuery('Raw query must include the primary key')
            model_cls = deferred_class_factory(self.model, skip)
        else:
            model_cls = self.model
            # All model's fields are present in the query. So, it is possible
            # to use *args based model instantation. For each field of the model,
            # record the query column position matching that field.
            model_init_field_pos = []
            for field in self.model._meta.fields:
                model_init_field_pos.append(model_init_field_names[field.attname])
        if need_resolv_columns:
            fields = [self.model_fields.get(c, None) for c in self.columns]
        # Begin looping through the query values.
        for values in query:
            if need_resolv_columns:
                values = compiler.resolve_columns(values, fields)
            # Associate fields to values
            if skip:
                model_init_kwargs = {}
                for attname, pos in six.iteritems(model_init_field_names):
                    model_init_kwargs[attname] = values[pos]
                instance = model_cls(**model_init_kwargs)
            else:
                model_init_args = [values[pos] for pos in model_init_field_pos]
                instance = model_cls(*model_init_args)
            if annotation_fields:
                for column, pos in annotation_fields:
                    setattr(instance, column, values[pos])

            instance._state.db = db
            instance._state.adding = False

            yield instance

    def __repr__(self):
        return "<RawQuerySet: %r>" % (self.raw_query % tuple(self.params))

    def __getitem__(self, k):
        return list(self)[k]

    @property
    def db(self):
        "Return the database that will be used if this query is executed now"
        return self._db or router.db_for_read(self.model)

    def using(self, alias):
        """
        Selects which database this Raw QuerySet should excecute it's query against.
        """
        return RawQuerySet(self.raw_query, model=self.model,
                query=self.query.clone(using=alias),
                params=self.params, translations=self.translations,
                using=alias)

    @property
    def columns(self):
        """
        A list of model field names in the order they'll appear in the
        query results.
        """
        if not hasattr(self, '_columns'):
            self._columns = self.query.get_columns()

            # Adjust any column names which don't match field names
            for (query_name, model_name) in self.translations.items():
                try:
                    index = self._columns.index(query_name)
                    self._columns[index] = model_name
                except ValueError:
                    # Ignore translations for non-existant column names
                    pass

        return self._columns

    @property
    def model_fields(self):
        """
        A dict mapping column names to model field names.
        """
        if not hasattr(self, '_model_fields'):
            converter = connections[self.db].introspection.table_name_converter
            self._model_fields = {}
            for field in self.model._meta.fields:
                name, column = field.get_attname_column()
                self._model_fields[converter(column)] = field
        return self._model_fields


def insert_query(model, objs, fields, return_id=False, raw=False, using=None):
    """
    Inserts a new record for the given model. This provides an interface to
    the InsertQuery class and is how Model.save() is implemented. It is not
    part of the public API.
    """
    query = sql.InsertQuery(model)
    query.insert_values(fields, objs, raw=raw)
    return query.get_compiler(using=using).execute_sql(return_id)


def prefetch_related_objects(result_cache, related_lookups):
    """
    Helper function for prefetch_related functionality

    Populates prefetched objects caches for a list of results
    from a QuerySet
    """
    if len(result_cache) == 0:
        return # nothing to do

    model = result_cache[0].__class__

    # We need to be able to dynamically add to the list of prefetch_related
    # lookups that we look up (see below).  So we need some book keeping to
    # ensure we don't do duplicate work.
    done_lookups = set() # list of lookups like foo__bar__baz
    done_queries = {}    # dictionary of things like 'foo__bar': [results]

    auto_lookups = [] # we add to this as we go through.
    followed_descriptors = set() # recursion protection

    all_lookups = itertools.chain(related_lookups, auto_lookups)
    for lookup in all_lookups:
        if lookup in done_lookups:
            # We've done exactly this already, skip the whole thing
            continue
        done_lookups.add(lookup)

        # Top level, the list of objects to decorate is the result cache
        # from the primary QuerySet. It won't be for deeper levels.
        obj_list = result_cache

        attrs = lookup.split(LOOKUP_SEP)
        for level, attr in enumerate(attrs):
            # Prepare main instances
            if len(obj_list) == 0:
                break

            current_lookup = LOOKUP_SEP.join(attrs[0:level+1])
            if current_lookup in done_queries:
                # Skip any prefetching, and any object preparation
                obj_list = done_queries[current_lookup]
                continue

            # Prepare objects:
            good_objects = True
            for obj in obj_list:
                # Since prefetching can re-use instances, it is possible to have
                # the same instance multiple times in obj_list, so obj might
                # already be prepared.
                if not hasattr(obj, '_prefetched_objects_cache'):
                    try:
                        obj._prefetched_objects_cache = {}
                    except AttributeError:
                        # Must be in a QuerySet subclass that is not returning
                        # Model instances, either in Django or 3rd
                        # party. prefetch_related() doesn't make sense, so quit
                        # now.
                        good_objects = False
                        break
            if not good_objects:
                break

            # Descend down tree

            # We assume that objects retrieved are homogenous (which is the premise
            # of prefetch_related), so what applies to first object applies to all.
            first_obj = obj_list[0]
            prefetcher, descriptor, attr_found, is_fetched = get_prefetcher(first_obj, attr)

            if not attr_found:
                raise AttributeError("Cannot find '%s' on %s object, '%s' is an invalid "
                                     "parameter to prefetch_related()" %
                                     (attr, first_obj.__class__.__name__, lookup))

            if level == len(attrs) - 1 and prefetcher is None:
                # Last one, this *must* resolve to something that supports
                # prefetching, otherwise there is no point adding it and the
                # developer asking for it has made a mistake.
                raise ValueError("'%s' does not resolve to a item that supports "
                                 "prefetching - this is an invalid parameter to "
                                 "prefetch_related()." % lookup)

            if prefetcher is not None and not is_fetched:
                obj_list, additional_prl = prefetch_one_level(obj_list, prefetcher, attr)
                # We need to ensure we don't keep adding lookups from the
                # same relationships to stop infinite recursion. So, if we
                # are already on an automatically added lookup, don't add
                # the new lookups from relationships we've seen already.
                if not (lookup in auto_lookups and
                        descriptor in followed_descriptors):
                    for f in additional_prl:
                        new_prl = LOOKUP_SEP.join([current_lookup, f])
                        auto_lookups.append(new_prl)
                    done_queries[current_lookup] = obj_list
                followed_descriptors.add(descriptor)
            else:
                # Either a singly related object that has already been fetched
                # (e.g. via select_related), or hopefully some other property
                # that doesn't support prefetching but needs to be traversed.

                # We replace the current list of parent objects with the list
                # of related objects, filtering out empty or missing values so
                # that we can continue with nullable or reverse relations.
                new_obj_list = []
                for obj in obj_list:
                    try:
                        new_obj = getattr(obj, attr)
                    except exceptions.ObjectDoesNotExist:
                        continue
                    if new_obj is None:
                        continue
                    new_obj_list.append(new_obj)
                obj_list = new_obj_list


def get_prefetcher(instance, attr):
    """
    For the attribute 'attr' on the given instance, finds
    an object that has a get_prefetch_query_set().
    Returns a 4 tuple containing:
    (the object with get_prefetch_query_set (or None),
     the descriptor object representing this relationship (or None),
     a boolean that is False if the attribute was not found at all,
     a boolean that is True if the attribute has already been fetched)
    """
    prefetcher = None
    attr_found = False
    is_fetched = False

    # For singly related objects, we have to avoid getting the attribute
    # from the object, as this will trigger the query. So we first try
    # on the class, in order to get the descriptor object.
    rel_obj_descriptor = getattr(instance.__class__, attr, None)
    if rel_obj_descriptor is None:
        try:
            rel_obj = getattr(instance, attr)
            attr_found = True
        except AttributeError:
            pass
    else:
        attr_found = True
        if rel_obj_descriptor:
            # singly related object, descriptor object has the
            # get_prefetch_query_set() method.
            if hasattr(rel_obj_descriptor, 'get_prefetch_query_set'):
                prefetcher = rel_obj_descriptor
                if rel_obj_descriptor.is_cached(instance):
                    is_fetched = True
            else:
                # descriptor doesn't support prefetching, so we go ahead and get
                # the attribute on the instance rather than the class to
                # support many related managers
                rel_obj = getattr(instance, attr)
                if hasattr(rel_obj, 'get_prefetch_query_set'):
                    prefetcher = rel_obj
    return prefetcher, rel_obj_descriptor, attr_found, is_fetched


def prefetch_one_level(instances, prefetcher, attname):
    """
    Helper function for prefetch_related_objects

    Runs prefetches on all instances using the prefetcher object,
    assigning results to relevant caches in instance.

    The prefetched objects are returned, along with any additional
    prefetches that must be done due to prefetch_related lookups
    found from default managers.
    """
    # prefetcher must have a method get_prefetch_query_set() which takes a list
    # of instances, and returns a tuple:

    # (queryset of instances of self.model that are related to passed in instances,
    #  callable that gets value to be matched for returned instances,
    #  callable that gets value to be matched for passed in instances,
    #  boolean that is True for singly related objects,
    #  cache name to assign to).

    # The 'values to be matched' must be hashable as they will be used
    # in a dictionary.

    rel_qs, rel_obj_attr, instance_attr, single, cache_name =\
        prefetcher.get_prefetch_query_set(instances)
    # We have to handle the possibility that the default manager itself added
    # prefetch_related lookups to the QuerySet we just got back. We don't want to
    # trigger the prefetch_related functionality by evaluating the query.
    # Rather, we need to merge in the prefetch_related lookups.
    additional_prl = getattr(rel_qs, '_prefetch_related_lookups', [])
    if additional_prl:
        # Don't need to clone because the manager should have given us a fresh
        # instance, so we access an internal instead of using public interface
        # for performance reasons.
        rel_qs._prefetch_related_lookups = []

    all_related_objects = list(rel_qs)

    rel_obj_cache = {}
    for rel_obj in all_related_objects:
        rel_attr_val = rel_obj_attr(rel_obj)
        rel_obj_cache.setdefault(rel_attr_val, []).append(rel_obj)

    for obj in instances:
        instance_attr_val = instance_attr(obj)
        vals = rel_obj_cache.get(instance_attr_val, [])
        if single:
            # Need to assign to single cache on instance
            setattr(obj, cache_name, vals[0] if vals else None)
        else:
            # Multi, attribute represents a manager with an .all() method that
            # returns a QuerySet
            qs = getattr(obj, attname).all()
            qs._result_cache = vals
            # We don't want the individual qs doing prefetch_related now, since we
            # have merged this into the current work.
            qs._prefetch_done = True
            obj._prefetched_objects_cache[cache_name] = qs
    return all_related_objects, additional_prl
