"""
Query subclasses which provide extra functionality beyond simple data retrieval.
"""

from django.core.exceptions import FieldError
from django.db.models.sql.constants import *
from django.db.models.sql.datastructures import Date
from django.db.models.sql.expressions import SQLEvaluator
from django.db.models.sql.query import Query
from django.db.models.sql.where import AND, Constraint

__all__ = ['DeleteQuery', 'UpdateQuery', 'InsertQuery', 'DateQuery',
        'AggregateQuery']

class DeleteQuery(Query):
    """
    Delete queries are done through this class, since they are more constrained
    than general queries.
    """
    def as_sql(self):
        """
        Creates the SQL for this query. Returns the SQL string and list of
        parameters.
        """
        assert len(self.tables) == 1, \
                "Can only delete from one table at a time."
        result = ['DELETE FROM %s' % self.quote_name_unless_alias(self.tables[0])]
        where, params = self.where.as_sql()
        result.append('WHERE %s' % where)
        return ' '.join(result), tuple(params)

    def do_query(self, table, where):
        self.tables = [table]
        self.where = where
        self.execute_sql(None)

    def delete_batch_related(self, pk_list):
        """
        Set up and execute delete queries for all the objects related to the
        primary key values in pk_list. To delete the objects themselves, use
        the delete_batch() method.

        More than one physical query may be executed if there are a
        lot of values in pk_list.
        """
        from django.contrib.contenttypes import generic
        cls = self.model
        for related in cls._meta.get_all_related_many_to_many_objects():
            if not isinstance(related.field, generic.GenericRelation):
                for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
                    where = self.where_class()
                    where.add((Constraint(None,
                            related.field.m2m_reverse_name(), related.field),
                            'in',
                            pk_list[offset : offset+GET_ITERATOR_CHUNK_SIZE]),
                            AND)
                    self.do_query(related.field.m2m_db_table(), where)

        for f in cls._meta.many_to_many:
            w1 = self.where_class()
            if isinstance(f, generic.GenericRelation):
                from django.contrib.contenttypes.models import ContentType
                field = f.rel.to._meta.get_field(f.content_type_field_name)
                w1.add((Constraint(None, field.column, field), 'exact',
                        ContentType.objects.get_for_model(cls).id), AND)
            for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
                where = self.where_class()
                where.add((Constraint(None, f.m2m_column_name(), f), 'in',
                        pk_list[offset : offset + GET_ITERATOR_CHUNK_SIZE]),
                        AND)
                if w1:
                    where.add(w1, AND)
                self.do_query(f.m2m_db_table(), where)

    def delete_batch(self, pk_list):
        """
        Set up and execute delete queries for all the objects in pk_list. This
        should be called after delete_batch_related(), if necessary.

        More than one physical query may be executed if there are a
        lot of values in pk_list.
        """
        for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
            where = self.where_class()
            field = self.model._meta.pk
            where.add((Constraint(None, field.column, field), 'in',
                    pk_list[offset : offset + GET_ITERATOR_CHUNK_SIZE]), AND)
            self.do_query(self.model._meta.db_table, where)

class UpdateQuery(Query):
    """
    Represents an "update" SQL query.
    """
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

    def execute_sql(self, result_type=None):
        """
        Execute the specified update. Returns the number of rows affected by
        the primary update query. The "primary update query" is the first
        non-empty query that is executed. Row counts for any subsequent,
        related queries are not available.
        """
        cursor = super(UpdateQuery, self).execute_sql(result_type)
        rows = cursor and cursor.rowcount or 0
        is_empty = cursor is None
        del cursor
        for query in self.get_related_updates():
            aux_rows = query.execute_sql(result_type)
            if is_empty:
                rows = aux_rows
                is_empty = False
        return rows

    def as_sql(self):
        """
        Creates the SQL for this query. Returns the SQL string and list of
        parameters.
        """
        self.pre_sql_setup()
        if not self.values:
            return '', ()
        table = self.tables[0]
        qn = self.quote_name_unless_alias
        result = ['UPDATE %s' % qn(table)]
        result.append('SET')
        values, update_params = [], []
        for name, val, placeholder in self.values:
            if hasattr(val, 'as_sql'):
                sql, params = val.as_sql(qn)
                values.append('%s = %s' % (qn(name), sql))
                update_params.extend(params)
            elif val is not None:
                values.append('%s = %s' % (qn(name), placeholder))
                update_params.append(val)
            else:
                values.append('%s = NULL' % qn(name))
        result.append(', '.join(values))
        where, params = self.where.as_sql()
        if where:
            result.append('WHERE %s' % where)
        return ' '.join(result), tuple(update_params + params)

    def pre_sql_setup(self):
        """
        If the update depends on results from other tables, we need to do some
        munging of the "where" conditions to match the format required for
        (portable) SQL updates. That is done here.

        Further, if we are going to be running multiple updates, we pull out
        the id values to update at this point so that they don't change as a
        result of the progressive updates.
        """
        self.select_related = False
        self.clear_ordering(True)
        super(UpdateQuery, self).pre_sql_setup()
        count = self.count_active_tables()
        if not self.related_updates and count == 1:
            return

        # We need to use a sub-select in the where clause to filter on things
        # from other tables.
        query = self.clone(klass=Query)
        query.bump_prefix()
        query.extra = {}
        query.select = []
        query.add_fields([query.model._meta.pk.name])
        must_pre_select = count > 1 and not self.connection.features.update_can_self_select

        # Now we adjust the current query: reset the where clause and get rid
        # of all the tables we don't need (since they're in the sub-select).
        self.where = self.where_class()
        if self.related_updates or must_pre_select:
            # Either we're using the idents in multiple update queries (so
            # don't want them to change), or the db backend doesn't support
            # selecting from the updating table (e.g. MySQL).
            idents = []
            for rows in query.execute_sql(MULTI):
                idents.extend([r[0] for r in rows])
            self.add_filter(('pk__in', idents))
            self.related_ids = idents
        else:
            # The fast path. Filters and updates in one query.
            self.add_filter(('pk__in', query))
        for alias in self.tables[1:]:
            self.alias_refcount[alias] = 0

    def clear_related(self, related_field, pk_list):
        """
        Set up and execute an update query that clears related entries for the
        keys in pk_list.

        This is used by the QuerySet.delete_objects() method.
        """
        for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
            self.where = self.where_class()
            f = self.model._meta.pk
            self.where.add((Constraint(None, f.column, f), 'in',
                    pk_list[offset : offset + GET_ITERATOR_CHUNK_SIZE]),
                    AND)
            self.values = [(related_field.column, None, '%s')]
            self.execute_sql(None)

    def add_update_values(self, values):
        """
        Convert a dictionary of field name to value mappings into an update
        query. This is the entry point for the public update() method on
        querysets.
        """
        values_seq = []
        for name, val in values.iteritems():
            field, model, direct, m2m = self.model._meta.get_field_by_name(name)
            if not direct or m2m:
                raise FieldError('Cannot update model field %r (only non-relations and foreign keys permitted).' % field)
            values_seq.append((field, model, val))
        return self.add_update_fields(values_seq)

    def add_update_fields(self, values_seq):
        """
        Turn a sequence of (field, model, value) triples into an update query.
        Used by add_update_values() as well as the "fast" update path when
        saving models.
        """
        from django.db.models.base import Model
        for field, model, val in values_seq:
            if hasattr(val, 'prepare_database_save'):
                val = val.prepare_database_save(field)
            else:
                val = field.get_db_prep_save(val)

            # Getting the placeholder for the field.
            if hasattr(field, 'get_placeholder'):
                placeholder = field.get_placeholder(val)
            else:
                placeholder = '%s'

            if hasattr(val, 'evaluate'):
                val = SQLEvaluator(val, self, allow_joins=False)
            if model:
                self.add_related_update(model, field.column, val, placeholder)
            else:
                self.values.append((field.column, val, placeholder))

    def add_related_update(self, model, column, value, placeholder):
        """
        Adds (name, value) to an update query for an ancestor model.

        Updates are coalesced so that we only run one update query per ancestor.
        """
        try:
            self.related_updates[model].append((column, value, placeholder))
        except KeyError:
            self.related_updates[model] = [(column, value, placeholder)]

    def get_related_updates(self):
        """
        Returns a list of query objects: one for each update required to an
        ancestor model. Each query will have the same filtering conditions as
        the current query but will only update a single table.
        """
        if not self.related_updates:
            return []
        result = []
        for model, values in self.related_updates.iteritems():
            query = UpdateQuery(model, self.connection)
            query.values = values
            if self.related_ids:
                query.add_filter(('pk__in', self.related_ids))
            result.append(query)
        return result

class InsertQuery(Query):
    def __init__(self, *args, **kwargs):
        super(InsertQuery, self).__init__(*args, **kwargs)
        self.columns = []
        self.values = []
        self.params = ()
        self.return_id = False

    def clone(self, klass=None, **kwargs):
        extras = {'columns': self.columns[:], 'values': self.values[:],
                  'params': self.params, 'return_id': self.return_id}
        extras.update(kwargs)
        return super(InsertQuery, self).clone(klass, **extras)

    def as_sql(self):
        # We don't need quote_name_unless_alias() here, since these are all
        # going to be column names (so we can avoid the extra overhead).
        qn = self.connection.ops.quote_name
        opts = self.model._meta
        result = ['INSERT INTO %s' % qn(opts.db_table)]
        result.append('(%s)' % ', '.join([qn(c) for c in self.columns]))
        result.append('VALUES (%s)' % ', '.join(self.values))
        params = self.params
        if self.return_id and self.connection.features.can_return_id_from_insert:
            col = "%s.%s" % (qn(opts.db_table), qn(opts.pk.column))
            r_fmt, r_params = self.connection.ops.return_insert_id()
            result.append(r_fmt % col)
            params = params + r_params
        return ' '.join(result), params

    def execute_sql(self, return_id=False):
        self.return_id = return_id
        cursor = super(InsertQuery, self).execute_sql(None)
        if not (return_id and cursor):
            return
        if self.connection.features.can_return_id_from_insert:
            return self.connection.ops.fetch_returned_insert_id(cursor)
        return self.connection.ops.last_insert_id(cursor,
                self.model._meta.db_table, self.model._meta.pk.column)

    def insert_values(self, insert_values, raw_values=False):
        """
        Set up the insert query from the 'insert_values' dictionary. The
        dictionary gives the model field names and their target values.

        If 'raw_values' is True, the values in the 'insert_values' dictionary
        are inserted directly into the query, rather than passed as SQL
        parameters. This provides a way to insert NULL and DEFAULT keywords
        into the query, for example.
        """
        placeholders, values = [], []
        for field, val in insert_values:
            if hasattr(field, 'get_placeholder'):
                # Some fields (e.g. geo fields) need special munging before
                # they can be inserted.
                placeholders.append(field.get_placeholder(val))
            else:
                placeholders.append('%s')

            self.columns.append(field.column)
            values.append(val)
        if raw_values:
            self.values.extend(values)
        else:
            self.params += tuple(values)
            self.values.extend(placeholders)

class DateQuery(Query):
    """
    A DateQuery is a normal query, except that it specifically selects a single
    date field. This requires some special handling when converting the results
    back to Python objects, so we put it in a separate class.
    """
    def __getstate__(self):
        """
        Special DateQuery-specific pickle handling.
        """
        for elt in self.select:
            if isinstance(elt, Date):
                # Eliminate a method reference that can't be pickled. The
                # __setstate__ method restores this.
                elt.date_sql_func = None
        return super(DateQuery, self).__getstate__()

    def __setstate__(self, obj_dict):
        super(DateQuery, self).__setstate__(obj_dict)
        for elt in self.select:
            if isinstance(elt, Date):
                self.date_sql_func = self.connection.ops.date_trunc_sql

    def results_iter(self):
        """
        Returns an iterator over the results from executing this query.
        """
        resolve_columns = hasattr(self, 'resolve_columns')
        if resolve_columns:
            from django.db.models.fields import DateTimeField
            fields = [DateTimeField()]
        else:
            from django.db.backends.util import typecast_timestamp
            needs_string_cast = self.connection.features.needs_datetime_string_cast

        offset = len(self.extra_select)
        for rows in self.execute_sql(MULTI):
            for row in rows:
                date = row[offset]
                if resolve_columns:
                    date = self.resolve_columns(row, fields)[offset]
                elif needs_string_cast:
                    date = typecast_timestamp(str(date))
                yield date

    def add_date_select(self, field, lookup_type, order='ASC'):
        """
        Converts the query into a date extraction query.
        """
        result = self.setup_joins([field.name], self.get_meta(),
                self.get_initial_alias(), False)
        alias = result[3][-1]
        select = Date((alias, field.column), lookup_type,
                self.connection.ops.date_trunc_sql)
        self.select = [select]
        self.select_fields = [None]
        self.select_related = False # See #7097.
        self.extra = {}
        self.distinct = True
        self.order_by = order == 'ASC' and [1] or [-1]

class AggregateQuery(Query):
    """
    An AggregateQuery takes another query as a parameter to the FROM
    clause and only selects the elements in the provided list.
    """
    def add_subquery(self, query):
        self.subquery, self.sub_params = query.as_sql(with_col_aliases=True)

    def as_sql(self, quote_func=None):
        """
        Creates the SQL for this query. Returns the SQL string and list of
        parameters.
        """
        sql = ('SELECT %s FROM (%s) subquery' % (
            ', '.join([
                aggregate.as_sql()
                for aggregate in self.aggregate_select.values()
            ]),
            self.subquery)
        )
        params = self.sub_params
        return (sql, params)
