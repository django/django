import warnings

from django.conf import settings
from django.db import connection, transaction, IntegrityError
from django.db.models.fields import DateField, FieldDoesNotExist
from django.db.models.query_utils import Q
from django.db.models import signals, sql
from django.dispatch import dispatcher
from django.utils.datastructures import SortedDict

# Used to control how many objects are worked with at once in some cases (e.g.
# when deleting objects).
CHUNK_SIZE = 100
ITER_CHUNK_SIZE = CHUNK_SIZE

# Pull into this namespace for backwards compatibility
EmptyResultSet = sql.EmptyResultSet

class QuerySet(object):
    "Represents a lazy database lookup for a set of objects"
    def __init__(self, model=None, query=None):
        self.model = model
        self.query = query or sql.Query(self.model, connection)
        self._result_cache = None
        self._iter = None

    ########################
    # PYTHON MAGIC METHODS #
    ########################

    def __getstate__(self):
        """
        Allows the Queryset to be pickled.
        """
        # Force the cache to be fully populated.
        len(self)

        obj_dict = self.__dict__.copy()
        obj_dict['_iter'] = None
        return obj_dict

    def __repr__(self):
        return repr(list(self))

    def __len__(self):
        # Since __len__ is called quite frequently (for example, as part of
        # list(qs), we make some effort here to be as efficient as possible
        # whilst not messing up any existing iterators against the queryset.
        if self._result_cache is None:
            if self._iter:
                self._result_cache = list(self._iter)
            else:
                self._result_cache = list(self.iterator())
        elif self._iter:
            self._result_cache.extend(list(self._iter))
        return len(self._result_cache)

    def __iter__(self):
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

    def __nonzero__(self):
        if self._result_cache is not None:
            return bool(self._result_cache)
        try:
            iter(self).next()
        except StopIteration:
            return False
        return True

    def __getitem__(self, k):
        "Retrieve an item or slice from the set of results."
        if not isinstance(k, (slice, int, long)):
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
        except self.model.DoesNotExist, e:
            raise IndexError, e.args

    def __and__(self, other):
        self._merge_sanity_check(other)
        combined = self._clone()
        combined.query.combine(other.query, sql.AND)
        return combined

    def __or__(self, other):
        self._merge_sanity_check(other)
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
        if isinstance(fill_cache, dict):
            requested = fill_cache
        else:
            requested = None
        max_depth = self.query.max_depth
        extra_select = self.query.extra_select.keys()
        index_start = len(extra_select)
        for row in self.query.results_iter():
            if fill_cache:
                obj, _ = get_cached_row(self.model, row, index_start,
                        max_depth, requested=requested)
            else:
                obj = self.model(*row[index_start:])
            for i, k in enumerate(extra_select):
                setattr(obj, k, row[i])
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
        num = len(clone)
        if num == 1:
            return clone._result_cache[0]
        if not num:
            raise self.model.DoesNotExist("%s matching query does not exist."
                    % self.model._meta.object_name)
        raise self.model.MultipleObjectsReturned("get() returned more than one %s -- it returned %s! Lookup parameters were %s"
                % (self.model._meta.object_name, num, kwargs))

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
            try:
                params = dict([(k, v) for k, v in kwargs.items() if '__' not in k])
                params.update(defaults)
                obj = self.model(**params)
                obj.save()
                return obj, True
            except IntegrityError, e:
                return self.get(**kwargs), False

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
        while 1:
            # Collect all the objects to be deleted in this chunk, and all the
            # objects that are related to the objects that are to be deleted.
            seen_objs = SortedDict()
            for object in del_query[:CHUNK_SIZE]:
                object._collect_sub_objects(seen_objs)

            if not seen_objs:
                break
            delete_objects(seen_objs)

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None
    delete.alters_data = True

    def update(self, **kwargs):
        """
        Updates all elements in the current QuerySet, setting all the given
        fields to the appropriate values.
        """
        query = self.query.clone(sql.UpdateQuery)
        query.add_update_values(kwargs)
        query.execute_sql(None)
        transaction.commit_unless_managed()
        self._result_cache = None
    update.alters_data = True

    def _update(self, values):
        """
        A version of update that accepts field objects instead of field names.
        Used primarily for model saving and not intended for use by general
        code (it requires too much poking around at model internals to be
        useful at that level).
        """
        query = self.query.clone(sql.UpdateQuery)
        query.add_update_fields(values)
        query.execute_sql(None)
        self._result_cache = None
    _update.alters_data = True

    ##################################################
    # PUBLIC METHODS THAT RETURN A QUERYSET SUBCLASS #
    ##################################################

    def values(self, *fields):
        return self._clone(klass=ValuesQuerySet, setup=True, _fields=fields)

    def values_list(self, *fields, **kwargs):
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to values_list: %s'
                    % (kwargs.keys(),))
        if flat and len(fields) > 1:
            raise TypeError("'flat' is not valid when values_list is called with more than one field.")
        return self._clone(klass=ValuesListQuerySet, setup=True, flat=flat,
                _fields=fields)

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

    def none(self):
        """
        Returns an empty queryset.
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
            return self._filter_or_exclude(None, filter_obj)
        else:
            return self._filter_or_exclude(None, **filter_obj)

    def select_related(self, *fields, **kwargs):
        """
        Returns a new QuerySet instance that will select related objects. If
        fields are specified, they must be ForeignKey fields and only those
        related objects are included in the selection.
        """
        depth = kwargs.pop('depth', 0)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to select_related: %s'
                    % (kwargs.keys(),))
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

    def dup_select_related(self, other):
        """
        Copies the related selection status from the queryset 'other' to the
        current queryset.
        """
        self.query.select_related = other.query.select_related

    def order_by(self, *field_names):
        """Returns a new QuerySet instance with the ordering changed."""
        assert self.query.can_filter(), \
                "Cannot reorder a query once a slice has been taken."
        obj = self._clone()
        obj.query.clear_ordering()
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
            order_by=None, select_params=None):
        """
        Add extra SQL fragments to the query.
        """
        assert self.query.can_filter(), \
                "Cannot change a query once a slice has been taken"
        clone = self._clone()
        clone.query.add_extra(select, select_params, where, params, tables, order_by)
        return clone

    def reverse(self):
        """
        Reverses the ordering of the queryset.
        """
        clone = self._clone()
        clone.query.standard_ordering = not clone.query.standard_ordering
        return clone

    ###################
    # PRIVATE METHODS #
    ###################

    def _clone(self, klass=None, setup=False, **kwargs):
        if klass is None:
            klass = self.__class__
        c = klass(model=self.model, query=self.query.clone())
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
                    self._result_cache.append(self._iter.next())
            except StopIteration:
                self._iter = None

    def _merge_sanity_check(self, other):
        """
        Checks that we are merging two comparable queryset classes.
        """
        if self.__class__ is not other.__class__:
            raise TypeError("Cannot merge querysets of different types ('%s' and '%s'."
                    % (self.__class__.__name__, other.__class__.__name__))

class ValuesQuerySet(QuerySet):
    def __init__(self, *args, **kwargs):
        super(ValuesQuerySet, self).__init__(*args, **kwargs)
        # select_related isn't supported in values(). (FIXME -#3358)
        self.query.select_related = False

        # QuerySet.clone() will also set up the _fields attribute with the
        # names of the model fields to select.

    def iterator(self):
        self.query.trim_extra_select(self.extra_names)
        names = self.query.extra_select.keys() + self.field_names
        for row in self.query.results_iter():
            yield dict(zip(names, row))

    def _setup_query(self):
        """
        Constructs the field_names list that the values query will be
        retrieving.

        Called by the _clone() method after initialising the rest of the
        instance.
        """
        self.extra_names = []
        if self._fields:
            if not self.query.extra_select:
                field_names = list(self._fields)
            else:
                field_names = []
                for f in self._fields:
                    if self.query.extra_select.has_key(f):
                        self.extra_names.append(f)
                    else:
                        field_names.append(f)
        else:
            # Default to all fields.
            field_names = [f.attname for f in self.model._meta.fields]

        self.query.add_fields(field_names, False)
        self.query.default_cols = False
        self.field_names = field_names

    def _clone(self, klass=None, setup=False, **kwargs):
        """
        Cloning a ValuesQuerySet preserves the current fields.
        """
        c = super(ValuesQuerySet, self)._clone(klass, **kwargs)
        c._fields = self._fields[:]
        c.field_names = self.field_names
        c.extra_names = self.extra_names
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

    def _merge_sanity_check(self, other):
        super(ValuesQuerySet, self)._merge_sanity_check(other)
        if (set(self.extra_names) != set(other.extra_names) or
                set(self.field_names) != set(other.field_names)):
            raise TypeError("Merging '%s' classes must involve the same values in each case."
                    % self.__class__.__name__)

class ValuesListQuerySet(ValuesQuerySet):
    def iterator(self):
        self.query.trim_extra_select(self.extra_names)
        if self.flat and len(self._fields) == 1:
            for row in self.query.results_iter():
                yield row[0]
        elif not self.query.extra_select:
            for row in self.query.results_iter():
                yield row
        else:
            # When extra(select=...) is involved, the extra cols come are
            # always at the start of the row, so we need to reorder the fields
            # to match the order in self._fields.
            names = self.query.extra_select.keys() + self.field_names
            for row in self.query.results_iter():
                data = dict(zip(names, row))
                yield tuple([data[f] for f in self._fields])

    def _clone(self, *args, **kwargs):
        clone = super(ValuesListQuerySet, self)._clone(*args, **kwargs)
        clone.flat = self.flat
        return clone

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
    def __init__(self, model=None, query=None):
        super(EmptyQuerySet, self).__init__(model, query)
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

# QOperator, QNot, QAnd and QOr are temporarily retained for backwards
# compatibility. All the old functionality is now part of the 'Q' class.
class QOperator(Q):
    def __init__(self, *args, **kwargs):
        warnings.warn('Use Q instead of QOr, QAnd or QOperation.',
                DeprecationWarning, stacklevel=2)
        super(QOperator, self).__init__(*args, **kwargs)

QOr = QAnd = QOperator

def QNot(q):
    warnings.warn('Use ~q instead of QNot(q)', DeprecationWarning, stacklevel=2)
    return ~q

def get_cached_row(klass, row, index_start, max_depth=0, cur_depth=0,
        requested=None):
    """
    Helper function that recursively returns an object with the specified
    related attributes already populated.
    """
    if max_depth and requested is None and cur_depth > max_depth:
        # We've recursed deeply enough; stop now.
        return None

    restricted = requested is not None
    index_end = index_start + len(klass._meta.fields)
    obj = klass(*row[index_start:index_end])
    for f in klass._meta.fields:
        if (not f.rel or (not restricted and f.null) or
                (restricted and f.name not in requested) or f.rel.parent_link):
            continue
        if restricted:
            next = requested[f.name]
        else:
            next = None
        cached_row = get_cached_row(f.rel.to, row, index_end, max_depth,
                cur_depth+1, next)
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

            dispatcher.send(signal=signals.post_delete, sender=cls,
                    instance=instance)
            setattr(instance, cls._meta.pk.attname, None)

    transaction.commit_unless_managed()

def insert_query(model, values, return_id=False, raw_values=False):
    """
    Inserts a new record for the given model. This provides an interface to
    the InsertQuery class and is how Model.save() is implemented. It is not
    part of the public API.
    """
    query = sql.InsertQuery(model, connection)
    query.insert_values(values, raw_values)
    return query.execute_sql(return_id)

