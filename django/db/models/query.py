from django.db import backend, connection
from django.db.models.exceptions import *

LOOKUP_SEPARATOR = '__'

####################
# HELPER FUNCTIONS #
####################

# Django currently supports two forms of ordering.
# Form 1 (deprecated) example:
#     order_by=(('pub_date', 'DESC'), ('headline', 'ASC'), (None, 'RANDOM'))
# Form 2 (new-style) example:
#     order_by=('-pub_date', 'headline', '?')
# Form 1 is deprecated and will no longer be supported for Django's first
# official release. The following code converts from Form 1 to Form 2.

LEGACY_ORDERING_MAPPING = {'ASC': '_', 'DESC': '-_', 'RANDOM': '?'}

def handle_legacy_orderlist(order_list):
    if not order_list or isinstance(order_list[0], basestring):
        return order_list
    else:
        import warnings
        new_order_list = [LEGACY_ORDERING_MAPPING[j.upper()].replace('_', str(i)) for i, j in order_list]
        warnings.warn("%r ordering syntax is deprecated. Use %r instead." % (order_list, new_order_list), DeprecationWarning)
        return new_order_list

def orderfield2column(f, opts):
    try:
        return opts.get_field(f, False).column
    except FieldDoesNotExist:
        return f

def orderlist2sql(order_list, opts, prefix=''):
    if prefix.endswith('.'):
        prefix = backend.quote_name(prefix[:-1]) + '.'
    output = []
    for f in handle_legacy_orderlist(order_list):
        if f.startswith('-'):
            output.append('%s%s DESC' % (prefix, backend.quote_name(orderfield2column(f[1:], opts))))
        elif f == '?':
            output.append(backend.get_random_function_sql())
        else:
            output.append('%s%s ASC' % (prefix, backend.quote_name(orderfield2column(f, opts))))
    return ', '.join(output)

class QOperator:
    "Base class for QAnd and QOr"
    def __init__(self, *args):
        self.args = args

    def __repr__(self):
        return '(%s)' % self.operator.join([repr(el) for el in self.args])

    def get_sql(self, opts):
        tables, joins, where, params = [], {}, [], []
        for val in self.args:
            tables2, joins2, where2, params2 = val.get_sql(opts)
            tables.extend(tables2)
            joins.update(joins2)
            where.extend(where2)
            params.extend(params2)
        return tables, joins, ['(%s)' % self.operator.join(where)], params

class QAnd(QOperator):
    "Encapsulates a combined query that uses 'AND'."
    operator = ' AND '
    def __or__(self, other):
        if isinstance(other, (QAnd, QOr, Q)):
            return QOr(self, other)
        else:
            raise TypeError, other

    def __and__(self, other):
        if isinstance(other, QAnd):
            return QAnd(*(self.args+other.args))
        elif isinstance(other, (Q, QOr)):
            return QAnd(*(self.args+(other,)))
        else:
            raise TypeError, other

class QOr(QOperator):
    "Encapsulates a combined query that uses 'OR'."
    operator = ' OR '
    def __and__(self, other):
        if isinstance(other, (QAnd, QOr, Q)):
            return QAnd(self, other)
        else:
            raise TypeError, other

    def __or__(self, other):
        if isinstance(other, QOr):
            return QOr(*(self.args+other.args))
        elif isinstance(other, (Q, QAnd)):
            return QOr(*(self.args+(other,)))
        else:
            raise TypeError, other

class Q:
    "Encapsulates queries for the 'complex' parameter to Django API functions."
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __repr__(self):
        return 'Q%r' % self.kwargs

    def __and__(self, other):
        if isinstance(other, (Q, QAnd, QOr)):
            return QAnd(self, other)
        else:
            raise TypeError, other

    def __or__(self, other):
        if isinstance(other, (Q, QAnd, QOr)):
            return QOr(self, other)
        else:
            raise TypeError, other

    def get_sql(self, opts):
        return parse_lookup(self.kwargs.items(), opts)


def get_where_clause(lookup_type, table_prefix, field_name, value):
    if table_prefix.endswith('.'):
        table_prefix = backend.quote_name(table_prefix[:-1])+'.'
    field_name = backend.quote_name(field_name)
    try:
        return '%s%s %s' % (table_prefix, field_name, (backend.OPERATOR_MAPPING[lookup_type] % '%s'))
    except KeyError:
        pass
    if lookup_type == 'in':
        return '%s%s IN (%s)' % (table_prefix, field_name, ','.join(['%s' for v in value]))
    elif lookup_type in ('range', 'year'):
        return '%s%s BETWEEN %%s AND %%s' % (table_prefix, field_name)
    elif lookup_type in ('month', 'day'):
        return "%s = %%s" % backend.get_date_extract_sql(lookup_type, table_prefix + field_name)
    elif lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))
    raise TypeError, "Got invalid lookup_type: %s" % repr(lookup_type)

def get_cached_row(klass, row, index_start):
    "Helper function that recursively returns an object with cache filled"
    index_end = index_start + len(klass._meta.fields)
    obj = klass(*row[index_start:index_end])
    for f in klass._meta.fields:
        if f.rel and not f.null:
            rel_obj, index_end = get_cached_row(f.rel.to, row, index_end)
            setattr(obj, f.get_cache_name(), rel_obj)
    return obj, index_end

def fill_table_cache(opts, select, tables, where, old_prefix, cache_tables_seen):
    """
    Helper function that recursively populates the select, tables and where (in
    place) for fill-cache queries.
    """
    for f in opts.fields:
        if f.rel and not f.null:
            db_table = f.rel.to._meta.db_table
            if db_table not in cache_tables_seen:
                tables.append(backend.quote_name(db_table))
            else: # The table was already seen, so give it a table alias.
                new_prefix = '%s%s' % (db_table, len(cache_tables_seen))
                tables.append('%s %s' % (backend.quote_name(db_table), backend.quote_name(new_prefix)))
                db_table = new_prefix
            cache_tables_seen.append(db_table)
            where.append('%s.%s = %s.%s' % \
                (backend.quote_name(old_prefix), backend.quote_name(f.column),
                backend.quote_name(db_table), backend.quote_name(f.rel.get_related_field().column)))
            select.extend(['%s.%s' % (backend.quote_name(db_table), backend.quote_name(f2.column)) for f2 in f.rel.to._meta.fields])
            fill_table_cache(f.rel.to._meta, select, tables, where, db_table, cache_tables_seen)

def throw_bad_kwarg_error(kwarg):
    # Helper function to remove redundancy.
    raise TypeError, "got unexpected keyword argument '%s'" % kwarg

def parse_lookup(kwarg_items, opts):
    # Helper function that handles converting API kwargs (e.g.
    # "name__exact": "tom") to SQL.

    # 'joins' is a dictionary describing the tables that must be joined to complete the query.
    # Each key-value pair follows the form
    #   alias: (table, join_type, condition)
    # where
    #   alias is the AS alias for the joined table
    #   table is the actual table name to be joined
    #   join_type is the type of join (INNER JOIN, LEFT OUTER JOIN, etc)
    #   condition is the where-like statement over which narrows the join.
    #
    # alias will be derived from the lookup list name.
    # At present, this method only every returns INNER JOINs; the option is there for others
    # to implement custom Q()s, etc that return other join types.
    tables, joins, where, params = [], {}, [], []
    for kwarg, kwarg_value in kwarg_items:
        if kwarg in ('order_by', 'limit', 'offset', 'select_related', 'distinct', 'select', 'tables', 'where', 'params'):
            continue
        if kwarg_value is None:
            continue
        if kwarg == 'complex':
            tables2, joins2, where2, params2 = kwarg_value.get_sql(opts)
            tables.extend(tables2)
            joins.update(joins2)
            where.extend(where2)
            params.extend(params2)
            continue
        if kwarg == '_or':
            for val in kwarg_value:
                tables2, joins2, where2, params2 = parse_lookup(val, opts)
                tables.extend(tables2)
                joins.update(joins2)
                where.append('(%s)' % ' OR '.join(where2))
                params.extend(params2)
            continue
        lookup_list = kwarg.split(LOOKUP_SEPARATOR)
        # pk="value" is shorthand for (primary key)__exact="value"
        if lookup_list[-1] == 'pk':
            if opts.pk.rel:
                lookup_list = lookup_list[:-1] + [opts.pk.name, opts.pk.rel.field_name, 'exact']
            else:
                lookup_list = lookup_list[:-1] + [opts.pk.name, 'exact']
        if len(lookup_list) == 1:
            throw_bad_kwarg_error(kwarg)
        lookup_type = lookup_list.pop()
        current_opts = opts # We'll be overwriting this, so keep a reference to the original opts.
        current_table_alias = current_opts.db_table
        param_required = False
        while lookup_list or param_required:
            try:
                # "current" is a piece of the lookup list. For example, in
                # choices.get_list(poll__sites__id__exact=5), lookup_list is
                # ["poll", "sites", "id"], and the first current is "poll".
                try:
                    current = lookup_list.pop(0)
                except IndexError:
                    # If we're here, lookup_list is empty but param_required
                    # is set to True, which means the kwarg was bad.
                    # Example: choices.get_list(poll__exact='foo')
                    throw_bad_kwarg_error(kwarg)
                # Try many-to-many relationships first...
                for f in current_opts.many_to_many:
                    if f.name == current:
                        rel_table_alias = backend.quote_name(current_table_alias + LOOKUP_SEPARATOR + current)

                        joins[rel_table_alias] = (
                            backend.quote_name(f.get_m2m_db_table(current_opts)),
                            "INNER JOIN",
                            '%s.%s = %s.%s' %
                                (backend.quote_name(current_table_alias),
                                backend.quote_name(current_opts.pk.column),
                                rel_table_alias,
                                backend.quote_name(current_opts.object_name.lower() + '_id'))
                        )

                        # Optimization: In the case of primary-key lookups, we
                        # don't have to do an extra join.
                        if lookup_list and lookup_list[0] == f.rel.to._meta.pk.name and lookup_type == 'exact':
                            where.append(get_where_clause(lookup_type, rel_table_alias+'.',
                                f.rel.to._meta.object_name.lower()+'_id', kwarg_value))
                            params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                            lookup_list.pop()
                            param_required = False
                        else:
                            new_table_alias = current_table_alias + LOOKUP_SEPARATOR + current

                            joins[backend.quote_name(new_table_alias)] = (
                                backend.quote_name(f.rel.to._meta.db_table),
                                "INNER JOIN",
                                '%s.%s = %s.%s' %
                                    (rel_table_alias,
                                    backend.quote_name(f.rel.to._meta.object_name.lower() + '_id'),
                                    backend.quote_name(new_table_alias),
                                    backend.quote_name(f.rel.to._meta.pk.column))
                            )
                            current_table_alias = new_table_alias
                            param_required = True
                        current_opts = f.rel.to._meta
                        raise StopIteration
                for f in current_opts.fields:
                    # Try many-to-one relationships...
                    if f.rel and f.name == current:
                        # Optimization: In the case of primary-key lookups, we
                        # don't have to do an extra join.
                        if lookup_list and lookup_list[0] == f.rel.to._meta.pk.name and lookup_type == 'exact':
                            where.append(get_where_clause(lookup_type, current_table_alias+'.', f.column, kwarg_value))
                            params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                            lookup_list.pop()
                            param_required = False
                        # 'isnull' lookups in many-to-one relationships are a special case,
                        # because we don't want to do a join. We just want to find out
                        # whether the foreign key field is NULL.
                        elif lookup_type == 'isnull' and not lookup_list:
                            where.append(get_where_clause(lookup_type, current_table_alias+'.', f.column, kwarg_value))
                            params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                        else:
                            new_table_alias = current_table_alias + LOOKUP_SEPARATOR + current

                            joins[backend.quote_name(new_table_alias)] = (
                                backend.quote_name(f.rel.to._meta.db_table),
                                "INNER JOIN",
                                '%s.%s = %s.%s' %
                                    (backend.quote_name(current_table_alias),
                                    backend.quote_name(f.column),
                                    backend.quote_name(new_table_alias),
                                    backend.quote_name(f.rel.to._meta.pk.column))
                            )
                            current_table_alias = new_table_alias
                            param_required = True
                        current_opts = f.rel.to._meta
                        raise StopIteration
                    # Try direct field-name lookups...
                    if f.name == current:
                        where.append(get_where_clause(lookup_type, current_table_alias+'.', f.column, kwarg_value))
                        params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                        param_required = False
                        raise StopIteration
                # If we haven't hit StopIteration at this point, "current" must be
                # an invalid lookup, so raise an exception.
                throw_bad_kwarg_error(kwarg)
            except StopIteration:
                continue
    return tables, joins, where, params
