"""
The main QuerySet implementation. This provides the public API for the ORM.
"""

import copy
import sys
import warnings
from collections import OrderedDict, deque

from django.conf import settings
from django.core import exceptions
from django.db import (
    DJANGO_VERSION_PICKLE_KEY, IntegrityError, connections, router,
    transaction,
)
from django.db.models import sql
from django.db.models.constants import LOOKUP_SEP
from django.db.models.deletion import Collector
from django.db.models.expressions import Date, DateTime, F
from django.db.models.fields import AutoField, Empty
from django.db.models.query_utils import (
    InvalidQuery, Q, deferred_class_factory,
)
from django.db.models.sql.constants import CURSOR
from django.utils import six, timezone
from django.utils.functional import partition
from django.utils.version import get_version

# The maximum number of items to display in a QuerySet.__repr__
REPR_OUTPUT_SIZE = 20

# Pull into this namespace for backwards compatibility.
EmptyResultSet = sql.EmptyResultSet


def _pickle_queryset(class_bases, class_dict):
    """
    Used by `__reduce__` to create the initial version of the `QuerySet` class
    onto which the output of `__getstate__` will be applied.

    See `__reduce__` for more details.
    """
    new = Empty()
    new.__class__ = type(class_bases[0].__name__, class_bases, class_dict)
    return new


class QuerySet(object):
    """
    Represents a lazy database lookup for a set of objects.
    """

    def __init__(self, model=None, query=None, using=None, hints=None):
        self.model = model
        self._db = using
        self._hints = hints or {}
        self.query = query or sql.Query(self.model)
        self._result_cache = None
        self._sticky_filter = False
        self._for_write = False
        self._prefetch_related_lookups = []
        self._prefetch_done = False
        self._known_related_objects = {}        # {rel_field, {pk: rel_obj}}

    def as_manager(cls):
        # Address the circular dependency between `Queryset` and `Manager`.
        from django.db.models.manager import Manager
        manager = Manager.from_queryset(cls)()
        manager._built_with_as_manager = True
        return manager
    as_manager.queryset_only = True
    as_manager = classmethod(as_manager)

    ########################
    # PYTHON MAGIC METHODS #
    ########################

    def __deepcopy__(self, memo):
        """
        Deep copy of a QuerySet doesn't populate the cache
        """
        obj = self.__class__()
        for k, v in self.__dict__.items():
            if k == '_result_cache':
                obj.__dict__[k] = None
            else:
                obj.__dict__[k] = copy.deepcopy(v, memo)
        return obj

    def __getstate__(self):
        """
        Allows the QuerySet to be pickled.
        """
        # Force the cache to be fully populated.
        self._fetch_all()
        obj_dict = self.__dict__.copy()
        obj_dict[DJANGO_VERSION_PICKLE_KEY] = get_version()
        return obj_dict

    def __setstate__(self, state):
        msg = None
        pickled_version = state.get(DJANGO_VERSION_PICKLE_KEY)
        if pickled_version:
            current_version = get_version()
            if current_version != pickled_version:
                msg = ("Pickled queryset instance's Django version %s does"
                    " not match the current version %s."
                    % (pickled_version, current_version))
        else:
            msg = "Pickled queryset instance's Django version is not specified."

        if msg:
            warnings.warn(msg, RuntimeWarning, stacklevel=2)

        self.__dict__.update(state)

    def __reduce__(self):
        """
        Used by pickle to deal with the types that we create dynamically when
        specialized queryset such as `ValuesQuerySet` are used in conjunction
        with querysets that are *subclasses* of `QuerySet`.

        See `_clone` implementation for more details.
        """
        if hasattr(self, '_specialized_queryset_class'):
            class_bases = (
                self._specialized_queryset_class,
                self._base_queryset_class,
            )
            class_dict = {
                '_specialized_queryset_class': self._specialized_queryset_class,
                '_base_queryset_class': self._base_queryset_class,
            }
            return _pickle_queryset, (class_bases, class_dict), self.__getstate__()
        return super(QuerySet, self).__reduce__()

    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)

    def __len__(self):
        self._fetch_all()
        return len(self._result_cache)

    def __iter__(self):
        """
        The queryset iterator protocol uses three nested iterators in the
        default case:
            1. sql.compiler:execute_sql()
               - Returns 100 rows at time (constants.GET_ITERATOR_CHUNK_SIZE)
                 using cursor.fetchmany(). This part is responsible for
                 doing some column masking, and returning the rows in chunks.
            2. sql/compiler.results_iter()
               - Returns one row at time. At this point the rows are still just
                 tuples. In some cases the return values are converted to
                 Python values at this location.
            3. self.iterator()
               - Responsible for turning the rows into model objects.
        """
        self._fetch_all()
        return iter(self._result_cache)

    def __bool__(self):
        self._fetch_all()
        return bool(self._result_cache)

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice,) + six.integer_types):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0)) or
                (isinstance(k, slice) and (k.start is None or k.start >= 0) and
                 (k.stop is None or k.stop >= 0))), \
            "Negative indexing is not supported."

        if self._result_cache is not None:
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
            return list(qs)[::k.step] if k.step else qs

        qs = self._clone()
        qs.query.set_limits(k, k + 1)
        return list(qs)[0]

    def __and__(self, other):
        self._merge_sanity_check(other)
        if isinstance(other, EmptyQuerySet):
            return other
        if isinstance(self, EmptyQuerySet):
            return self
        combined = self._clone()
        combined._merge_known_related_objects(other)
        combined.query.combine(other.query, sql.AND)
        return combined

    def __or__(self, other):
        self._merge_sanity_check(other)
        if isinstance(self, EmptyQuerySet):
            return other
        if isinstance(other, EmptyQuerySet):
            return self
        combined = self._clone()
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
        db = self.db
        compiler = self.query.get_compiler(using=db)
        # Execute the query. This will also fill compiler.select, klass_info,
        # and annotations.
        results = compiler.execute_sql()
        select, klass_info, annotation_col_map = (compiler.select, compiler.klass_info,
                                                  compiler.annotation_col_map)
        if klass_info is None:
            return
        model_cls = klass_info['model']
        select_fields = klass_info['select_fields']
        model_fields_start, model_fields_end = select_fields[0], select_fields[-1] + 1
        init_list = [f[0].target.attname
                     for f in select[model_fields_start:model_fields_end]]
        if len(init_list) != len(model_cls._meta.concrete_fields):
            init_set = set(init_list)
            skip = [f.attname for f in model_cls._meta.concrete_fields
                    if f.attname not in init_set]
            model_cls = deferred_class_factory(model_cls, skip)
        related_populators = get_related_populators(klass_info, select, db)
        for row in compiler.results_iter(results):
            obj = model_cls.from_db(db, init_list, row[model_fields_start:model_fields_end])
            if related_populators:
                for rel_populator in related_populators:
                    rel_populator.populate(row, obj)
            if annotation_col_map:
                for attr_name, col_pos in annotation_col_map.items():
                    setattr(obj, attr_name, row[col_pos])

            # Add the known related objects to the model, if there are any
            if self._known_related_objects:
                for field, rel_objs in self._known_related_objects.items():
                    # Avoid overwriting objects loaded e.g. by select_related
                    if hasattr(obj, field.get_cache_name()):
                        continue
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
            # The default_alias property may raise a TypeError, so we use
            # a try/except construct rather than hasattr in order to remain
            # consistent between PY2 and PY3 (hasattr would swallow
            # the TypeError on PY2).
            try:
                arg.default_alias
            except (AttributeError, TypeError):
                raise TypeError("Complex aggregates require an alias")
            kwargs[arg.default_alias] = arg

        query = self.query.clone()
        for (alias, aggregate_expr) in kwargs.items():
            query.add_annotation(aggregate_expr, alias, is_summary=True)
            if not query.annotations[alias].contains_aggregate:
                raise TypeError("%s is not an aggregate expression" % alias)
        return query.get_aggregation(self.db, kwargs.keys())

    def count(self):
        """
        Performs a SELECT COUNT() and returns the number of records as an
        integer.

        If the QuerySet is already fully cached this simply returns the length
        of the cached results set to avoid multiple SELECT COUNT(*) calls.
        """
        if self._result_cache is not None:
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
                self.model._meta.object_name
            )
        raise self.model.MultipleObjectsReturned(
            "get() returned more than one %s -- it returned %s!" %
            (self.model._meta.object_name, num)
        )

    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self.model(**kwargs)
        self._for_write = True
        obj.save(force_insert=True, using=self.db)
        return obj

    def _populate_pk_values(self, objs):
        for obj in objs:
            if obj.pk is None:
                obj.pk = obj._meta.pk.get_pk_value_on_save(obj)

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
        fields = self.model._meta.local_concrete_fields
        objs = list(objs)
        self._populate_pk_values(objs)
        with transaction.atomic(using=self.db, savepoint=False):
            if (connection.features.can_combine_inserts_with_and_without_auto_increment_pk
                    and self.model._meta.has_auto_field):
                self._batched_insert(objs, fields, batch_size)
            else:
                objs_with_pk, objs_without_pk = partition(lambda o: o.pk is None, objs)
                if objs_with_pk:
                    self._batched_insert(objs_with_pk, fields, batch_size)
                if objs_without_pk:
                    fields = [f for f in fields if not isinstance(f, AutoField)]
                    self._batched_insert(objs_without_pk, fields, batch_size)

        return objs

    def get_or_create(self, defaults=None, **kwargs):
        """
        Looks up an object with the given kwargs, creating one if necessary.
        Returns a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        lookup, params = self._extract_model_params(defaults, **kwargs)
        self._for_write = True
        try:
            return self.get(**lookup), False
        except self.model.DoesNotExist:
            return self._create_object_from_params(lookup, params)

    def update_or_create(self, defaults=None, **kwargs):
        """
        Looks up an object with the given kwargs, updating one with defaults
        if it exists, otherwise creates a new one.
        Returns a tuple (object, created), where created is a boolean
        specifying whether an object was created.
        """
        defaults = defaults or {}
        lookup, params = self._extract_model_params(defaults, **kwargs)
        self._for_write = True
        try:
            obj = self.get(**lookup)
        except self.model.DoesNotExist:
            obj, created = self._create_object_from_params(lookup, params)
            if created:
                return obj, created
        for k, v in six.iteritems(defaults):
            setattr(obj, k, v)

        with transaction.atomic(using=self.db, savepoint=False):
            obj.save(using=self.db)
        return obj, False

    def _create_object_from_params(self, lookup, params):
        """
        Tries to create an object using passed params.
        Used by get_or_create and update_or_create
        """
        try:
            with transaction.atomic(using=self.db):
                obj = self.create(**params)
            return obj, True
        except IntegrityError:
            exc_info = sys.exc_info()
            try:
                return self.get(**lookup), False
            except self.model.DoesNotExist:
                pass
            six.reraise(*exc_info)

    def _extract_model_params(self, defaults, **kwargs):
        """
        Prepares `lookup` (kwargs that are valid model attributes), `params`
        (for creating a model instance) based on given kwargs; for use by
        get_or_create and update_or_create.
        """
        defaults = defaults or {}
        lookup = kwargs.copy()
        for f in self.model._meta.fields:
            if f.attname in lookup:
                lookup[f.name] = lookup.pop(f.attname)
        params = {k: v for k, v in kwargs.items() if LOOKUP_SEP not in k}
        params.update(defaults)
        return lookup, params

    def _earliest_or_latest(self, field_name=None, direction="-"):
        """
        Returns the latest object, according to the model's
        'get_latest_by' option or optional given field_name.
        """
        order_by = field_name or getattr(self.model._meta, 'get_latest_by')
        assert bool(order_by), "earliest() and latest() require either a "\
            "field_name parameter or 'get_latest_by' in the model"
        assert self.query.can_filter(), \
            "Cannot change a query once a slice has been taken."
        obj = self._clone()
        obj.query.set_limits(high=1)
        obj.query.clear_ordering(force_empty=True)
        obj.query.add_ordering('%s%s' % (direction, order_by))
        return obj.get()

    def earliest(self, field_name=None):
        return self._earliest_or_latest(field_name=field_name, direction="")

    def latest(self, field_name=None):
        return self._earliest_or_latest(field_name=field_name, direction="-")

    def first(self):
        """
        Returns the first object of a query, returns None if no match is found.
        """
        objects = list((self if self.ordered else self.order_by('pk'))[:1])
        if objects:
            return objects[0]
        return None

    def last(self):
        """
        Returns the last object of a query, returns None if no match is found.
        """
        objects = list((self.reverse() if self.ordered else self.order_by('-pk'))[:1])
        if objects:
            return objects[0]
        return None

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
        return {obj._get_pk_val(): obj for obj in qs}

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
    delete.queryset_only = True

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
        with transaction.atomic(using=self.db, savepoint=False):
            rows = query.get_compiler(self.db).execute_sql(CURSOR)
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
        return query.get_compiler(self.db).execute_sql(CURSOR)
    _update.alters_data = True
    _update.queryset_only = False

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

    def raw(self, raw_query, params=None, translations=None, using=None):
        if using is None:
            using = self.db
        return RawQuerySet(raw_query, model=self.model,
                params=params, translations=translations,
                using=using)

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
        Returns a list of date objects representing all available dates for
        the given field_name, scoped to 'kind'.
        """
        assert kind in ("year", "month", "day"), \
            "'kind' must be one of 'year', 'month' or 'day'."
        assert order in ('ASC', 'DESC'), \
            "'order' must be either 'ASC' or 'DESC'."
        return self.annotate(
            datefield=Date(field_name, kind),
            plain_field=F(field_name)
        ).values_list(
            'datefield', flat=True
        ).distinct().filter(plain_field__isnull=False).order_by(('-' if order == 'DESC' else '') + 'datefield')

    def datetimes(self, field_name, kind, order='ASC', tzinfo=None):
        """
        Returns a list of datetime objects representing all available
        datetimes for the given field_name, scoped to 'kind'.
        """
        assert kind in ("year", "month", "day", "hour", "minute", "second"), \
            "'kind' must be one of 'year', 'month', 'day', 'hour', 'minute' or 'second'."
        assert order in ('ASC', 'DESC'), \
            "'order' must be either 'ASC' or 'DESC'."
        if settings.USE_TZ:
            if tzinfo is None:
                tzinfo = timezone.get_current_timezone()
        else:
            tzinfo = None
        return self.annotate(
            datetimefield=DateTime(field_name, kind, tzinfo),
            plain_field=F(field_name)
        ).values_list(
            'datetimefield', flat=True
        ).distinct().filter(plain_field__isnull=False).order_by(('-' if order == 'DESC' else '') + 'datetimefield')

    def none(self):
        """
        Returns an empty QuerySet.
        """
        clone = self._clone()
        clone.query.set_empty()
        return clone

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

    def select_for_update(self, nowait=False):
        """
        Returns a new QuerySet instance that will select objects with a
        FOR UPDATE lock.
        """
        obj = self._clone()
        obj._for_write = True
        obj.query.select_for_update = True
        obj.query.select_for_update_nowait = nowait
        return obj

    def select_related(self, *fields):
        """
        Returns a new QuerySet instance that will select related objects.

        If fields are specified, they must be ForeignKey fields and only those
        related objects are included in the selection.

        If select_related(None) is called, the list is cleared.
        """
        obj = self._clone()
        if fields == (None,):
            obj.query.select_related = False
        elif fields:
            obj.query.add_select_related(fields)
        else:
            obj.query.select_related = True
        return obj

    def prefetch_related(self, *lookups):
        """
        Returns a new QuerySet instance that will prefetch the specified
        Many-To-One and Many-To-Many related objects when the QuerySet is
        evaluated.

        When prefetch_related() is called more than once, the list of lookups to
        prefetch is appended to. If prefetch_related(None) is called, the list
        is cleared.
        """
        clone = self._clone()
        if lookups == (None,):
            clone._prefetch_related_lookups = []
        else:
            clone._prefetch_related_lookups.extend(lookups)
        return clone

    def annotate(self, *args, **kwargs):
        """
        Return a query set in which the returned objects have been annotated
        with extra data or aggregations.
        """
        annotations = OrderedDict()  # To preserve ordering of args
        for arg in args:
            # The default_alias property may raise a TypeError, so we use
            # a try/except construct rather than hasattr in order to remain
            # consistent between PY2 and PY3 (hasattr would swallow
            # the TypeError on PY2).
            try:
                if arg.default_alias in kwargs:
                    raise ValueError("The named annotation '%s' conflicts with the "
                                     "default name for another annotation."
                                     % arg.default_alias)
            except (AttributeError, TypeError):
                raise TypeError("Complex annotations require an alias")
            annotations[arg.default_alias] = arg
        annotations.update(kwargs)

        obj = self._clone()
        names = getattr(self, '_fields', None)
        if names is None:
            names = {f.name for f in self.model._meta.get_fields()}

        # Add the annotations to the query
        for alias, annotation in annotations.items():
            if alias in names:
                raise ValueError("The annotation '%s' conflicts with a field on "
                                 "the model." % alias)
            obj.query.add_annotation(annotation, alias, is_summary=False)
        # expressions need to be added to the query before we know if they contain aggregates
        added_aggregates = []
        for alias, annotation in obj.query.annotations.items():
            if alias in annotations and annotation.contains_aggregate:
                added_aggregates.append(alias)
        if added_aggregates:
            obj._setup_aggregate_query(list(added_aggregates))

        return obj

    def order_by(self, *field_names):
        """
        Returns a new QuerySet instance with the ordering changed.
        """
        assert self.query.can_filter(), \
            "Cannot reorder a query once a slice has been taken."
        obj = self._clone()
        obj.query.clear_ordering(force_empty=False)
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
        Selects which database this QuerySet should execute its query against.
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
        elif self.query.default_ordering and self.query.get_meta().ordering:
            return True
        else:
            return False
    ordered = property(ordered)

    @property
    def db(self):
        "Return the database that will be used if this query is executed now"
        if self._for_write:
            return self._db or router.db_for_write(self.model, **self._hints)
        return self._db or router.db_for_read(self.model, **self._hints)

    ###################
    # PRIVATE METHODS #
    ###################

    def _insert(self, objs, fields, return_id=False, raw=False, using=None):
        """
        Inserts a new record for the given model. This provides an interface to
        the InsertQuery class and is how Model.save() is implemented.
        """
        self._for_write = True
        if using is None:
            using = self.db
        query = sql.InsertQuery(self.model)
        query.insert_values(fields, objs, raw=raw)
        return query.get_compiler(using=using).execute_sql(return_id)
    _insert.alters_data = True
    _insert.queryset_only = False

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
        for batch in [objs[i:i + batch_size]
                      for i in range(0, len(objs), batch_size)]:
            self.model._base_manager._insert(batch, fields=fields,
                                             using=self.db)

    def _clone(self, klass=None, setup=False, **kwargs):
        base_queryset_class = getattr(self, '_base_queryset_class', self.__class__)
        if klass is None:
            klass = self.__class__
        elif not (issubclass(base_queryset_class, klass) or issubclass(klass, base_queryset_class)):
            class_bases = (klass, base_queryset_class)
            class_dict = {
                '_base_queryset_class': base_queryset_class,
                '_specialized_queryset_class': klass,
            }
            klass = type(klass.__name__, class_bases, class_dict)

        query = self.query.clone()
        if self._sticky_filter:
            query.filter_is_sticky = True
        c = klass(model=self.model, query=query, using=self._db, hints=self._hints)
        c._for_write = self._for_write
        c._prefetch_related_lookups = self._prefetch_related_lookups[:]
        c._known_related_objects = self._known_related_objects
        c.__dict__.update(kwargs)
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

    def _fetch_all(self):
        if self._result_cache is None:
            self._result_cache = list(self.iterator())
        if self._prefetch_related_lookups and not self._prefetch_done:
            self._prefetch_related_objects()

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
        if self.query.group_by is None:
            self.query.group_by = True

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

    def _add_hints(self, **hints):
        """
        Update hinting information for later use by Routers
        """
        # If there is any hinting information, add it to what we already know.
        # If we have a new hint for an existing key, overwrite with the new value.
        self._hints.update(hints)

    def _has_filters(self):
        """
        Checks if this QuerySet has any filtering going on. Note that this
        isn't equivalent for checking if all objects are present in results,
        for example qs[1:]._has_filters() -> False.
        """
        return self.query.has_filters()

    def is_compatible_query_object_type(self, opts):
        model = self.model
        return (
            model == opts.concrete_model or
            opts.concrete_model in model._meta.get_parent_list() or
            model in opts.get_parent_list()
        )
    is_compatible_query_object_type.queryset_only = True


class InstanceCheckMeta(type):
    def __instancecheck__(self, instance):
        return instance.query.is_empty()


class EmptyQuerySet(six.with_metaclass(InstanceCheckMeta)):
    """
    Marker class usable for checking if a queryset is empty by .none():
        isinstance(qs.none(), EmptyQuerySet) -> True
    """

    def __init__(self, *args, **kwargs):
        raise TypeError("EmptyQuerySet can't be instantiated")


class ValuesQuerySet(QuerySet):
    def __init__(self, *args, **kwargs):
        super(ValuesQuerySet, self).__init__(*args, **kwargs)
        # select_related isn't supported in values(). (FIXME -#3358)
        self.query.select_related = False

        # QuerySet.clone() will also set up the _fields attribute with the
        # names of the model fields to select.

    def only(self, *fields):
        raise NotImplementedError("ValuesQuerySet does not implement only()")

    def defer(self, *fields):
        raise NotImplementedError("ValuesQuerySet does not implement defer()")

    def iterator(self):
        # Purge any extra columns that haven't been explicitly asked for
        extra_names = list(self.query.extra_select)
        field_names = self.field_names
        annotation_names = list(self.query.annotation_select)

        names = extra_names + field_names + annotation_names

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
        if self.query.group_by is True:
            self.query.add_fields([f.attname for f in self.model._meta.concrete_fields], False)
            self.query.set_group_by()
        self.query.clear_deferred_loading()
        self.query.clear_select_fields()
        if self._fields:
            self.extra_names = []
            self.annotation_names = []
            if not self.query._extra and not self.query._annotations:
                # Short cut - if there are no extra or annotations, then
                # the values() clause must be just field names.
                self.field_names = list(self._fields)
            else:
                self.query.default_cols = False
                self.field_names = []
                for f in self._fields:
                    # we inspect the full extra_select list since we might
                    # be adding back an extra select item that we hadn't
                    # had selected previously.
                    if self.query._extra and f in self.query._extra:
                        self.extra_names.append(f)
                    elif f in self.query.annotation_select:
                        self.annotation_names.append(f)
                    else:
                        self.field_names.append(f)
        else:
            # Default to all fields.
            self.extra_names = None
            self.field_names = [f.attname for f in self.model._meta.concrete_fields]
            self.annotation_names = None

        self.query.select = []
        if self.extra_names is not None:
            self.query.set_extra_mask(self.extra_names)
        self.query.add_fields(self.field_names, True)
        if self.annotation_names is not None:
            self.query.set_annotation_mask(self.annotation_names)

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
        c.annotation_names = self.annotation_names
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

    def _merge_sanity_check(self, other):
        super(ValuesQuerySet, self)._merge_sanity_check(other)
        if (set(self.extra_names) != set(other.extra_names) or
                set(self.field_names) != set(other.field_names) or
                self.annotation_names != other.annotation_names):
            raise TypeError("Merging '%s' classes must involve the same values in each case."
                    % self.__class__.__name__)

    def _setup_aggregate_query(self, aggregates):
        """
        Prepare the query for computing a result that contains aggregate annotations.
        """
        self.query.set_group_by()

        if self.annotation_names is not None:
            self.annotation_names.extend(aggregates)
            self.query.set_annotation_mask(self.annotation_names)

        super(ValuesQuerySet, self)._setup_aggregate_query(aggregates)

    def _as_sql(self, connection):
        """
        For ValuesQuerySet (and subclasses like ValuesListQuerySet), they can
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

    def is_compatible_query_object_type(self, opts):
        """
        ValueQuerySets do not need to be checked for compatibility.
        We trust that users of ValueQuerySets know what they are doing.
        """
        return True


class ValuesListQuerySet(ValuesQuerySet):
    def iterator(self):
        compiler = self.query.get_compiler(self.db)
        if self.flat and len(self._fields) == 1:
            for row in compiler.results_iter():
                yield row[0]
        elif not self.query.extra_select and not self.query.annotation_select:
            for row in compiler.results_iter():
                yield tuple(row)
        else:
            # When extra(select=...) or an annotation is involved, the extra
            # cols are always at the start of the row, and we need to reorder
            # the fields to match the order in self._fields.
            extra_names = list(self.query.extra_select)
            field_names = self.field_names
            annotation_names = list(self.query.annotation_select)

            names = extra_names + field_names + annotation_names

            # If a field list has been specified, use it. Otherwise, use the
            # full list of fields, including extras and annotations.
            if self._fields:
                fields = list(self._fields) + [f for f in annotation_names if f not in self._fields]
            else:
                fields = names

            for row in compiler.results_iter():
                data = dict(zip(names, row))
                yield tuple(data[f] for f in fields)

    def _clone(self, *args, **kwargs):
        clone = super(ValuesListQuerySet, self)._clone(*args, **kwargs)
        if not hasattr(clone, "flat"):
            # Only assign flat if the clone didn't already get it from kwargs
            clone.flat = self.flat
        return clone


class RawQuerySet(object):
    """
    Provides an iterator which converts the results of raw SQL queries into
    annotated model instances.
    """
    def __init__(self, raw_query, model=None, query=None, params=None,
            translations=None, using=None, hints=None):
        self.raw_query = raw_query
        self.model = model
        self._db = using
        self._hints = hints or {}
        self.query = query or sql.RawQuery(sql=raw_query, using=self.db, params=params)
        self.params = params or ()
        self.translations = translations or {}

    def resolve_model_init_order(self):
        """
        Resolve the init field names and value positions
        """
        model_init_fields = [f for f in self.model._meta.fields if f.column in self.columns]
        annotation_fields = [(column, pos) for pos, column in enumerate(self.columns)
                             if column not in self.model_fields]
        model_init_order = [self.columns.index(f.column) for f in model_init_fields]
        model_init_names = [f.attname for f in model_init_fields]
        return model_init_names, model_init_order, annotation_fields

    def __iter__(self):
        # Cache some things for performance reasons outside the loop.
        db = self.db
        compiler = connections[db].ops.compiler('SQLCompiler')(
            self.query, connections[db], db
        )

        query = iter(self.query)

        try:
            model_init_names, model_init_pos, annotation_fields = self.resolve_model_init_order()

            # Find out which model's fields are not present in the query.
            skip = set()
            for field in self.model._meta.fields:
                if field.attname not in model_init_names:
                    skip.add(field.attname)
            if skip:
                if self.model._meta.pk.attname in skip:
                    raise InvalidQuery('Raw query must include the primary key')
                model_cls = deferred_class_factory(self.model, skip)
            else:
                model_cls = self.model
            fields = [self.model_fields.get(c, None) for c in self.columns]
            converters = compiler.get_converters([
                f.get_col(f.model._meta.db_table) if f else None for f in fields
            ])
            for values in query:
                if converters:
                    values = compiler.apply_converters(values, converters)
                # Associate fields to values
                model_init_values = [values[pos] for pos in model_init_pos]
                instance = model_cls.from_db(db, model_init_names, model_init_values)
                if annotation_fields:
                    for column, pos in annotation_fields:
                        setattr(instance, column, values[pos])
                yield instance
        finally:
            # Done iterating the Query. If it has its own cursor, close it.
            if hasattr(self.query, 'cursor') and self.query.cursor:
                self.query.cursor.close()

    def __repr__(self):
        return "<RawQuerySet: %s>" % self.query

    def __getitem__(self, k):
        return list(self)[k]

    @property
    def db(self):
        "Return the database that will be used if this query is executed now"
        return self._db or router.db_for_read(self.model, **self._hints)

    def using(self, alias):
        """
        Selects which database this Raw QuerySet should execute its query against.
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
                    # Ignore translations for non-existent column names
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


class Prefetch(object):
    def __init__(self, lookup, queryset=None, to_attr=None):
        # `prefetch_through` is the path we traverse to perform the prefetch.
        self.prefetch_through = lookup
        # `prefetch_to` is the path to the attribute that stores the result.
        self.prefetch_to = lookup
        if to_attr:
            self.prefetch_to = LOOKUP_SEP.join(lookup.split(LOOKUP_SEP)[:-1] + [to_attr])

        self.queryset = queryset
        self.to_attr = to_attr

    def add_prefix(self, prefix):
        self.prefetch_through = LOOKUP_SEP.join([prefix, self.prefetch_through])
        self.prefetch_to = LOOKUP_SEP.join([prefix, self.prefetch_to])

    def get_current_prefetch_through(self, level):
        return LOOKUP_SEP.join(self.prefetch_through.split(LOOKUP_SEP)[:level + 1])

    def get_current_prefetch_to(self, level):
        return LOOKUP_SEP.join(self.prefetch_to.split(LOOKUP_SEP)[:level + 1])

    def get_current_to_attr(self, level):
        parts = self.prefetch_to.split(LOOKUP_SEP)
        to_attr = parts[level]
        as_attr = self.to_attr and level == len(parts) - 1
        return to_attr, as_attr

    def get_current_queryset(self, level):
        if self.get_current_prefetch_to(level) == self.prefetch_to:
            return self.queryset
        return None

    def __eq__(self, other):
        if isinstance(other, Prefetch):
            return self.prefetch_to == other.prefetch_to
        return False

    def __hash__(self):
        return hash(self.__class__) ^ hash(self.prefetch_to)


def normalize_prefetch_lookups(lookups, prefix=None):
    """
    Helper function that normalize lookups into Prefetch objects.
    """
    ret = []
    for lookup in lookups:
        if not isinstance(lookup, Prefetch):
            lookup = Prefetch(lookup)
        if prefix:
            lookup.add_prefix(prefix)
        ret.append(lookup)
    return ret


def prefetch_related_objects(result_cache, related_lookups):
    """
    Helper function for prefetch_related functionality

    Populates prefetched objects caches for a list of results
    from a QuerySet
    """

    if len(result_cache) == 0:
        return  # nothing to do

    related_lookups = normalize_prefetch_lookups(related_lookups)

    # We need to be able to dynamically add to the list of prefetch_related
    # lookups that we look up (see below).  So we need some book keeping to
    # ensure we don't do duplicate work.
    done_queries = {}    # dictionary of things like 'foo__bar': [results]

    auto_lookups = set()  # we add to this as we go through.
    followed_descriptors = set()  # recursion protection

    all_lookups = deque(related_lookups)
    while all_lookups:
        lookup = all_lookups.popleft()
        if lookup.prefetch_to in done_queries:
            if lookup.queryset:
                raise ValueError("'%s' lookup was already seen with a different queryset. "
                                 "You may need to adjust the ordering of your lookups." % lookup.prefetch_to)

            continue

        # Top level, the list of objects to decorate is the result cache
        # from the primary QuerySet. It won't be for deeper levels.
        obj_list = result_cache

        through_attrs = lookup.prefetch_through.split(LOOKUP_SEP)
        for level, through_attr in enumerate(through_attrs):
            # Prepare main instances
            if len(obj_list) == 0:
                break

            prefetch_to = lookup.get_current_prefetch_to(level)
            if prefetch_to in done_queries:
                # Skip any prefetching, and any object preparation
                obj_list = done_queries[prefetch_to]
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

            # We assume that objects retrieved are homogeneous (which is the premise
            # of prefetch_related), so what applies to first object applies to all.
            first_obj = obj_list[0]
            prefetcher, descriptor, attr_found, is_fetched = get_prefetcher(first_obj, through_attr)

            if not attr_found:
                raise AttributeError("Cannot find '%s' on %s object, '%s' is an invalid "
                                     "parameter to prefetch_related()" %
                                     (through_attr, first_obj.__class__.__name__, lookup.prefetch_through))

            if level == len(through_attrs) - 1 and prefetcher is None:
                # Last one, this *must* resolve to something that supports
                # prefetching, otherwise there is no point adding it and the
                # developer asking for it has made a mistake.
                raise ValueError("'%s' does not resolve to an item that supports "
                                 "prefetching - this is an invalid parameter to "
                                 "prefetch_related()." % lookup.prefetch_through)

            if prefetcher is not None and not is_fetched:
                obj_list, additional_lookups = prefetch_one_level(obj_list, prefetcher, lookup, level)
                # We need to ensure we don't keep adding lookups from the
                # same relationships to stop infinite recursion. So, if we
                # are already on an automatically added lookup, don't add
                # the new lookups from relationships we've seen already.
                if not (lookup in auto_lookups and descriptor in followed_descriptors):
                    done_queries[prefetch_to] = obj_list
                    new_lookups = normalize_prefetch_lookups(additional_lookups, prefetch_to)
                    auto_lookups.update(new_lookups)
                    all_lookups.extendleft(new_lookups)
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
                        new_obj = getattr(obj, through_attr)
                    except exceptions.ObjectDoesNotExist:
                        continue
                    if new_obj is None:
                        continue
                    # We special-case `list` rather than something more generic
                    # like `Iterable` because we don't want to accidentally match
                    # user models that define __iter__.
                    if isinstance(new_obj, list):
                        new_obj_list.extend(new_obj)
                    else:
                        new_obj_list.append(new_obj)
                obj_list = new_obj_list


def get_prefetcher(instance, attr):
    """
    For the attribute 'attr' on the given instance, finds
    an object that has a get_prefetch_queryset().
    Returns a 4 tuple containing:
    (the object with get_prefetch_queryset (or None),
     the descriptor object representing this relationship (or None),
     a boolean that is False if the attribute was not found at all,
     a boolean that is True if the attribute has already been fetched)
    """
    prefetcher = None
    is_fetched = False

    # For singly related objects, we have to avoid getting the attribute
    # from the object, as this will trigger the query. So we first try
    # on the class, in order to get the descriptor object.
    rel_obj_descriptor = getattr(instance.__class__, attr, None)
    if rel_obj_descriptor is None:
        attr_found = hasattr(instance, attr)
    else:
        attr_found = True
        if rel_obj_descriptor:
            # singly related object, descriptor object has the
            # get_prefetch_queryset() method.
            if hasattr(rel_obj_descriptor, 'get_prefetch_queryset'):
                prefetcher = rel_obj_descriptor
                if rel_obj_descriptor.is_cached(instance):
                    is_fetched = True
            else:
                # descriptor doesn't support prefetching, so we go ahead and get
                # the attribute on the instance rather than the class to
                # support many related managers
                rel_obj = getattr(instance, attr)
                if hasattr(rel_obj, 'get_prefetch_queryset'):
                    prefetcher = rel_obj
    return prefetcher, rel_obj_descriptor, attr_found, is_fetched


def prefetch_one_level(instances, prefetcher, lookup, level):
    """
    Helper function for prefetch_related_objects

    Runs prefetches on all instances using the prefetcher object,
    assigning results to relevant caches in instance.

    The prefetched objects are returned, along with any additional
    prefetches that must be done due to prefetch_related lookups
    found from default managers.
    """
    # prefetcher must have a method get_prefetch_queryset() which takes a list
    # of instances, and returns a tuple:

    # (queryset of instances of self.model that are related to passed in instances,
    #  callable that gets value to be matched for returned instances,
    #  callable that gets value to be matched for passed in instances,
    #  boolean that is True for singly related objects,
    #  cache name to assign to).

    # The 'values to be matched' must be hashable as they will be used
    # in a dictionary.

    rel_qs, rel_obj_attr, instance_attr, single, cache_name = (
        prefetcher.get_prefetch_queryset(instances, lookup.get_current_queryset(level)))
    # We have to handle the possibility that the QuerySet we just got back
    # contains some prefetch_related lookups. We don't want to trigger the
    # prefetch_related functionality by evaluating the query. Rather, we need
    # to merge in the prefetch_related lookups.
    additional_lookups = getattr(rel_qs, '_prefetch_related_lookups', [])
    if additional_lookups:
        # Don't need to clone because the manager should have given us a fresh
        # instance, so we access an internal instead of using public interface
        # for performance reasons.
        rel_qs._prefetch_related_lookups = []

    all_related_objects = list(rel_qs)

    rel_obj_cache = {}
    for rel_obj in all_related_objects:
        rel_attr_val = rel_obj_attr(rel_obj)
        rel_obj_cache.setdefault(rel_attr_val, []).append(rel_obj)

    to_attr, as_attr = lookup.get_current_to_attr(level)
    # Make sure `to_attr` does not conflict with a field.
    if as_attr and instances:
        # We assume that objects retrieved are homogeneous (which is the premise
        # of prefetch_related), so what applies to first object applies to all.
        model = instances[0].__class__
        try:
            model._meta.get_field(to_attr)
        except exceptions.FieldDoesNotExist:
            pass
        else:
            msg = 'to_attr={} conflicts with a field on the {} model.'
            raise ValueError(msg.format(to_attr, model.__name__))

    for obj in instances:
        instance_attr_val = instance_attr(obj)
        vals = rel_obj_cache.get(instance_attr_val, [])

        if single:
            val = vals[0] if vals else None
            to_attr = to_attr if as_attr else cache_name
            setattr(obj, to_attr, val)
        else:
            if as_attr:
                setattr(obj, to_attr, vals)
            else:
                # Cache in the QuerySet.all().
                qs = getattr(obj, to_attr).all()
                qs._result_cache = vals
                # We don't want the individual qs doing prefetch_related now,
                # since we have merged this into the current work.
                qs._prefetch_done = True
                obj._prefetched_objects_cache[cache_name] = qs
    return all_related_objects, additional_lookups


class RelatedPopulator(object):
    """
    RelatedPopulator is used for select_related() object instantiation.

    The idea is that each select_related() model will be populated by a
    different RelatedPopulator instance. The RelatedPopulator instances get
    klass_info and select (computed in SQLCompiler) plus the used db as
    input for initialization. That data is used to compute which columns
    to use, how to instantiate the model, and how to populate the links
    between the objects.

    The actual creation of the objects is done in populate() method. This
    method gets row and from_obj as input and populates the select_related()
    model instance.
    """
    def __init__(self, klass_info, select, db):
        self.db = db
        # Pre-compute needed attributes. The attributes are:
        #  - model_cls: the possibly deferred model class to instantiate
        #  - either:
        #    - cols_start, cols_end: usually the columns in the row are
        #      in the same order model_cls.__init__ expects them, so we
        #      can instantiate by model_cls(*row[cols_start:cols_end])
        #    - reorder_for_init: When select_related descends to a child
        #      class, then we want to reuse the already selected parent
        #      data. However, in this case the parent data isn't necessarily
        #      in the same order that Model.__init__ expects it to be, so
        #      we have to reorder the parent data. The reorder_for_init
        #      attribute contains a function used to reorder the field data
        #      in the order __init__ expects it.
        #  - pk_idx: the index of the primary key field in the reordered
        #    model data. Used to check if a related object exists at all.
        #  - init_list: the field attnames fetched from the database. For
        #    deferred models this isn't the same as all attnames of the
        #    model's fields.
        #  - related_populators: a list of RelatedPopulator instances if
        #    select_related() descends to related models from this model.
        #  - cache_name, reverse_cache_name: the names to use for setattr
        #    when assigning the fetched object to the from_obj. If the
        #    reverse_cache_name is set, then we also set the reverse link.
        select_fields = klass_info['select_fields']
        from_parent = klass_info['from_parent']
        if not from_parent:
            self.cols_start = select_fields[0]
            self.cols_end = select_fields[-1] + 1
            self.init_list = [
                f[0].target.attname for f in select[self.cols_start:self.cols_end]
            ]
            self.reorder_for_init = None
        else:
            model_init_attnames = [
                f.attname for f in klass_info['model']._meta.concrete_fields
            ]
            reorder_map = []
            for idx in select_fields:
                field = select[idx][0].target
                init_pos = model_init_attnames.index(field.attname)
                reorder_map.append((init_pos, field.attname, idx))
            reorder_map.sort()
            self.init_list = [v[1] for v in reorder_map]
            pos_list = [row_pos for _, _, row_pos in reorder_map]

            def reorder_for_init(row):
                return [row[row_pos] for row_pos in pos_list]
            self.reorder_for_init = reorder_for_init

        self.model_cls = self.get_deferred_cls(klass_info, self.init_list)
        self.pk_idx = self.init_list.index(self.model_cls._meta.pk.attname)
        self.related_populators = get_related_populators(klass_info, select, self.db)
        field = klass_info['field']
        reverse = klass_info['reverse']
        self.reverse_cache_name = None
        if reverse:
            self.cache_name = field.rel.get_cache_name()
            self.reverse_cache_name = field.get_cache_name()
        else:
            self.cache_name = field.get_cache_name()
            if field.unique:
                self.reverse_cache_name = field.rel.get_cache_name()

    def get_deferred_cls(self, klass_info, init_list):
        model_cls = klass_info['model']
        if len(init_list) != len(model_cls._meta.concrete_fields):
            init_set = set(init_list)
            skip = [
                f.attname for f in model_cls._meta.concrete_fields
                if f.attname not in init_set
            ]
            model_cls = deferred_class_factory(model_cls, skip)
        return model_cls

    def populate(self, row, from_obj):
        if self.reorder_for_init:
            obj_data = self.reorder_for_init(row)
        else:
            obj_data = row[self.cols_start:self.cols_end]
        if obj_data[self.pk_idx] is None:
            obj = None
        else:
            obj = self.model_cls.from_db(self.db, self.init_list, obj_data)
        if obj and self.related_populators:
            for rel_iter in self.related_populators:
                rel_iter.populate(row, obj)
        setattr(from_obj, self.cache_name, obj)
        if obj and self.reverse_cache_name:
            setattr(obj, self.reverse_cache_name, from_obj)


def get_related_populators(klass_info, select, db):
    iterators = []
    related_klass_infos = klass_info.get('related_klass_infos', [])
    for rel_klass_info in related_klass_infos:
        rel_cls = RelatedPopulator(rel_klass_info, select, db)
        iterators.append(rel_cls)
    return iterators
