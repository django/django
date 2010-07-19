import re

from pymongo import ASCENDING, DESCENDING

from django.db import UnsupportedDatabaseOperation
from django.db.models import F
from django.db.models.sql.datastructures import FullResultSet, EmptyResultSet


# TODO: ...
class SQLCompiler(object):
    LOOKUP_TYPES = {
        "exact": lambda params, value_annotation, negated: params[0],
        "lt": lambda params, value_annotation, negated: {"$lt": params[0]},
        "isnull": lambda params, value_annotation, negated: {"$ne": None} if value_annotation == negated else None,
        "gt": lambda params, value_annotation, negated: {"$gt": params[0]},
        "in": lambda params, value_annotation, negated: {"$in": params},
        "regex": lambda params, value_annotation, negated: re.compile(params[0]),
        "iregex": lambda params, value_annotations, negated: re.compile(params[0], re.I)
    }
    
    def __init__(self, query, connection, using):
        self.query = query
        self.connection = connection
        self.using = using
    
    def get_filters(self, where):
        if where.connector != "AND":
            raise UnsupportedDatabaseOperation("MongoDB only supports joining "
                "filters with and, not or.")
        assert where.connector == "AND"
        filters = {}
        for child in where.children:
            if isinstance(child, self.query.where_class):
                child_filters = self.get_filters(child)
                for k, v in child_filters.iteritems():
                    assert k not in filters
                    if where.negated:
                        filters.update(self.negate(k, v))
                    else:
                        filters[k] = v
            else:
                try:
                    field, val = self.make_atom(*child, **{"negated": where.negated})
                    filters[field] = val
                except FullResultSet:
                    pass
        return filters
    
    def make_atom(self, lhs, lookup_type, value_annotation, params_or_value,
        negated):
        assert lookup_type in self.LOOKUP_TYPES, lookup_type
        if hasattr(lhs, "process"):
            lhs, params = lhs.process(
                lookup_type, params_or_value, self.connection
            )
        else:
            params = Field().get_db_prep_lookup(lookup_type, params_or_value, 
                connection=self.connection, prepared=True)
        assert isinstance(lhs, (list, tuple))
        table, column, _ = lhs
        assert table == self.query.model._meta.db_table
        if column == self.query.model._meta.pk.column:
            column = "_id"
        
        val = self.LOOKUP_TYPES[lookup_type](params, value_annotation, negated)
        return column, val
    
    def negate(self, k, v):
        # Regex lookups are of the form {"field": re.compile("pattern") and
        # need to be negated with $not, not $ne.
        if isinstance(v, dict) or isinstance(v, re._pattern_type):
            return {k: {"$not": v}}
        return {k: {"$ne": v}}
    
    def get_fields(self, aggregates):
        if self.query.select:
            fields = []
            for alias, field in self.query.select:
                assert alias == self.query.model._meta.db_table
                if field == self.query.model._meta.pk.column:
                    field = "_id"
                fields.append(field)
            return fields
        if not aggregates:
            assert self.query.default_cols
        return None
    
    def build_query(self, aggregates=False):
        if len([a for a in self.query.alias_map if self.query.alias_refcount[a]]) > 1:
            raise UnsupportedDatabaseOperation("MongoDB does not support "
                "operations across relations.")
        if self.query.extra:
            raise UnsupportedDatabaseOperation("MongoDB does not support extra().")
        assert not self.query.distinct
        assert not self.query.having
        
        filters = self.get_filters(self.query.where)
        fields = self.get_fields(aggregates=aggregates)
        collection = self.connection.db[self.query.model._meta.db_table]
        cursor = collection.find(filters, fields=fields)
        if self.query.order_by:
            cursor = cursor.sort([
                (ordering.lstrip("-"), DESCENDING if ordering.startswith("-") else ASCENDING)
                for ordering in self.query.order_by
            ])
        if self.query.low_mark:
            cursor = cursor.skip(self.query.low_mark)
        if self.query.high_mark is not None:
            if self.query.high_mark - self.query.low_mark == 0:
                raise EmptyResultSet
            cursor = cursor.limit(self.query.high_mark - self.query.low_mark)
        return cursor
    
    def results_iter(self):
        try:
            query = self.build_query()
        except EmptyResultSet:
            return
        fields = self.get_fields(aggregates=False)
        if fields is None:
            fields = [
                f.column if f is not self.query.model._meta.pk else "_id"
                for f in self.query.model._meta.fields
            ]
        for row in query:
            yield tuple(
                row[f] for f in fields
            )
    
    def has_results(self):
        try:
            self.build_query()[0]
        except IndexError:
            return False
        else:
            return True
    
    def get_aggregates(self):
        if len(self.query.aggregates) != 1:
            raise UnsupportedDatabaseOperation("MongoDB doesn't support "
                "multiple aggregates in a single query.")
        assert len(self.query.aggregates) == 1
        agg = self.query.aggregates.values()[0]
        if not isinstance(agg, self.query.aggregates_module.Count):
            raise UnsupportedDatabaseOperation("MongoDB does not support "
                "aggregates other than Count.")
        opts = self.query.model._meta
        if not (agg.col == "*" or agg.col == (opts.db_table, opts.pk.column)):
            raise UnsupportedDatabaseOperation("MongoDB does not support "
                "aggregation over fields besides the primary key.")

        return [self.build_query(aggregates=True).count()]


class SQLInsertCompiler(SQLCompiler):
    def insert(self, return_id=False):
        values = dict([
            (c, v)
            for c, v in zip(self.query.columns, self.query.params)
        ])
        if self.query.model._meta.pk.column in values:
            values["_id"] = values.pop(self.query.model._meta.pk.column)
        if "_id" in values and not values["_id"]:
            del values["_id"]
        return self.connection.db[self.query.model._meta.db_table].insert(values)

class SQLUpdateCompiler(SQLCompiler):
    def update(self, result_type):
        # TODO: more asserts
        filters = self.get_filters(self.query.where)

        vals = {}
        for field, o, value in self.query.values:
            if hasattr(value, "evaluate"):
                assert value.connector in (value.ADD, value.SUB)
                assert not value.negated
                assert not value.subtree_parents
                lhs, rhs = value.children
                if isinstance(lhs, F):
                    assert not isinstance(rhs, F)
                    if value.connector == value.SUB:
                        rhs = -rhs
                else:
                    assert value.connector == value.ADD
                    rhs, lhs = lhs, rhs
                vals.setdefault("$inc", {})[lhs.name] = rhs
            else:
                vals.setdefault("$set", {})[field.column] = value
        return self.connection.db[self.query.model._meta.db_table].update(
            filters,
            vals,
            multi=True
        )


class SQLDeleteCompiler(SQLCompiler):
    def delete(self, result_type):
        filters = self.get_filters(self.query.where)
        self.connection.db[self.query.model._meta.db_table].remove(filters)
