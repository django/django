"""
Query subclasses which provide extra functionality beyond simple data retrieval.
"""

from django.conf import settings
from django.core.exceptions import FieldError
from django.db import connections
from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields import DateField, DateTimeField, FieldDoesNotExist
from django.db.models.sql.constants import GET_ITERATOR_CHUNK_SIZE, SelectInfo
from django.db.models.sql.datastructures import Date, DateTime
from django.db.models.sql.query import Query
from django.db.models.sql.where import AND, Constraint
from django.utils.functional import Promise
from django.utils.encoding import force_text
from django.utils import six
from django.utils import timezone


__all__ = ['DeleteQuery', 'UpdateQuery', 'InsertQuery', 'DateQuery',
        'DateTimeQuery', 'AggregateQuery']


class DeleteQuery(Query):
    """
    Delete queries are done through this class, since they are more constrained
    than general queries.
    """

    compiler = 'SQLDeleteCompiler'

    def do_query(self, table, where, using):
        self.tables = [table]
        self.where = where
        self.get_compiler(using).execute_sql(None)

    def delete_batch(self, pk_list, using, field=None):
        """
        Set up and execute delete queries for all the objects in pk_list.

        More than one physical query may be executed if there are a
        lot of values in pk_list.
        """
        if not field:
            field = self.get_meta().pk
        for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
            where = self.where_class()
            where.add((Constraint(None, field.column, field), 'in',
                       pk_list[offset:offset + GET_ITERATOR_CHUNK_SIZE]), AND)
            self.do_query(self.get_meta().db_table, where, using=using)

    def delete_qs(self, query, using):
        """
        Delete the queryset in one SQL query (if possible). For simple queries
        this is done by copying the query.query.where to self.query, for
        complex queries by using subquery.
        """
        innerq = query.query
        # Make sure the inner query has at least one table in use.
        innerq.get_initial_alias()
        # The same for our new query.
        self.get_initial_alias()
        innerq_used_tables = [t for t in innerq.tables
                              if innerq.alias_refcount[t]]
        if ((not innerq_used_tables or innerq_used_tables == self.tables)
            and not len(innerq.having)):
            # There is only the base table in use in the query, and there are
            # no aggregate filtering going on.
            self.where = innerq.where
        else:
            pk = query.model._meta.pk
            if not connections[using].features.update_can_self_select:
                # We can't do the delete using subquery.
                values = list(query.values_list('pk', flat=True))
                if not values:
                    return
                self.delete_batch(values, using)
                return
            else:
                innerq.clear_select_clause()
                innerq.select = [
                    SelectInfo((self.get_initial_alias(), pk.column), None)
                ]
                values = innerq
            where = self.where_class()
            where.add((Constraint(None, pk.column, pk), 'in', values), AND)
            self.where = where
        self.get_compiler(using).execute_sql(None)


class UpdateQuery(Query):
    """
    Represents an "update" SQL query.
    """

    compiler = 'SQLUpdateCompiler'

    def __init__(self, *args, **kwargs):
        super(UpdateQuery, self).__init__(*args, **kwargs)
        self._setup_query()

    def _setup_query(self):
        """
        Runs on initialization and after cloning. Any attributes that would
        normally be set in __init__ should go in here, instead, so that they
        are also set up after a clone() call.
        """
        self.values = []
        self.related_ids = None
        if not hasattr(self, 'related_updates'):
            self.related_updates = {}

    def clone(self, klass=None, **kwargs):
        return super(UpdateQuery, self).clone(klass,
                related_updates=self.related_updates.copy(), **kwargs)

    def update_batch(self, pk_list, values, using):
        pk_field = self.get_meta().pk
        self.add_update_values(values)
        for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
            self.where = self.where_class()
            self.where.add((Constraint(None, pk_field.column, pk_field), 'in',
                            pk_list[offset:offset + GET_ITERATOR_CHUNK_SIZE]),
                           AND)
            self.get_compiler(using).execute_sql(None)

    def add_update_values(self, values):
        """
        Convert a dictionary of field name to value mappings into an update
        query. This is the entry point for the public update() method on
        querysets.
        """
        values_seq = []
        for name, val in six.iteritems(values):
            field, model, direct, m2m = self.get_meta().get_field_by_name(name)
            if not direct or m2m:
                raise FieldError('Cannot update model field %r (only non-relations and foreign keys permitted).' % field)
            if model:
                self.add_related_update(model, field, val)
                continue
            values_seq.append((field, model, val))
        return self.add_update_fields(values_seq)

    def add_update_fields(self, values_seq):
        """
        Turn a sequence of (field, model, value) triples into an update query.
        Used by add_update_values() as well as the "fast" update path when
        saving models.
        """
        # Check that no Promise object passes to the query. Refs #10498.
        values_seq = [(value[0], value[1], force_text(value[2]))
                      if isinstance(value[2], Promise) else value
                      for value in values_seq]
        self.values.extend(values_seq)

    def add_related_update(self, model, field, value):
        """
        Adds (name, value) to an update query for an ancestor model.

        Updates are coalesced so that we only run one update query per ancestor.
        """
        try:
            self.related_updates[model].append((field, None, value))
        except KeyError:
            self.related_updates[model] = [(field, None, value)]

    def get_related_updates(self):
        """
        Returns a list of query objects: one for each update required to an
        ancestor model. Each query will have the same filtering conditions as
        the current query but will only update a single table.
        """
        if not self.related_updates:
            return []
        result = []
        for model, values in six.iteritems(self.related_updates):
            query = UpdateQuery(model)
            query.values = values
            if self.related_ids is not None:
                query.add_filter(('pk__in', self.related_ids))
            result.append(query)
        return result


class InsertQuery(Query):
    compiler = 'SQLInsertCompiler'

    def __init__(self, *args, **kwargs):
        super(InsertQuery, self).__init__(*args, **kwargs)
        self.fields = []
        self.objs = []

    def clone(self, klass=None, **kwargs):
        extras = {
            'fields': self.fields[:],
            'objs': self.objs[:],
            'raw': self.raw,
        }
        extras.update(kwargs)
        return super(InsertQuery, self).clone(klass, **extras)

    def insert_values(self, fields, objs, raw=False):
        """
        Set up the insert query from the 'insert_values' dictionary. The
        dictionary gives the model field names and their target values.

        If 'raw_values' is True, the values in the 'insert_values' dictionary
        are inserted directly into the query, rather than passed as SQL
        parameters. This provides a way to insert NULL and DEFAULT keywords
        into the query, for example.
        """
        self.fields = fields
        # Check that no Promise object reaches the DB. Refs #10498.
        for field in fields:
            for obj in objs:
                value = getattr(obj, field.attname)
                if isinstance(value, Promise):
                    setattr(obj, field.attname, force_text(value))
        self.objs = objs
        self.raw = raw


class DateQuery(Query):
    """
    A DateQuery is a normal query, except that it specifically selects a single
    date field. This requires some special handling when converting the results
    back to Python objects, so we put it in a separate class.
    """

    compiler = 'SQLDateCompiler'

    def add_select(self, field_name, lookup_type, order='ASC'):
        """
        Converts the query into an extraction query.
        """
        try:
            result = self.setup_joins(
                field_name.split(LOOKUP_SEP),
                self.get_meta(),
                self.get_initial_alias(),
            )
        except FieldError:
            raise FieldDoesNotExist("%s has no field named '%s'" % (
                self.get_meta().object_name, field_name
            ))
        field = result[0]
        self._check_field(field)                # overridden in DateTimeQuery
        alias = result[3][-1]
        select = self._get_select((alias, field.column), lookup_type)
        self.clear_select_clause()
        self.select = [SelectInfo(select, None)]
        self.distinct = True
        self.order_by = [1] if order == 'ASC' else [-1]

        if field.null:
            self.add_filter(("%s__isnull" % field_name, False))

    def _check_field(self, field):
        assert isinstance(field, DateField), \
            "%r isn't a DateField." % field.name
        if settings.USE_TZ:
            assert not isinstance(field, DateTimeField), \
                "%r is a DateTimeField, not a DateField." % field.name

    def _get_select(self, col, lookup_type):
        return Date(col, lookup_type)


class DateTimeQuery(DateQuery):
    """
    A DateTimeQuery is like a DateQuery but for a datetime field. If time zone
    support is active, the tzinfo attribute contains the time zone to use for
    converting the values before truncating them. Otherwise it's set to None.
    """

    compiler = 'SQLDateTimeCompiler'

    def _check_field(self, field):
        assert isinstance(field, DateTimeField), \
                "%r isn't a DateTimeField." % field.name

    def _get_select(self, col, lookup_type):
        if self.tzinfo is None:
            tzname = None
        else:
            tzname = timezone._get_timezone_name(self.tzinfo)
        return DateTime(col, lookup_type, tzname)


class AggregateQuery(Query):
    """
    An AggregateQuery takes another query as a parameter to the FROM
    clause and only selects the elements in the provided list.
    """

    compiler = 'SQLAggregateCompiler'

    def add_subquery(self, query, using):
        self.subquery, self.sub_params = query.get_compiler(using).as_sql(with_col_aliases=True)
