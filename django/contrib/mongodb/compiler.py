from django.db.models.sql.datastructures import FullResultSet


# TODO: ...
class SQLCompiler(object):
    LOOKUP_TYPES = {
        "exact": lambda params: params[0],
        "lt": lambda params: {"$lt": params[0]},
        "isnull": lambda params: params[0]
    }
    
    def __init__(self, query, connection, using):
        self.query = query
        self.connection = connection
        self.using = using
    
    def get_filters(self, where):
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
    
    def make_atom(self, lhs, lookup_type, value_annotation, params_or_value, negated):
        assert lookup_type in self.LOOKUP_TYPES, lookup_type
        if hasattr(lhs, "process"):
            lhs, params = lhs.process(lookup_type, params_or_value, self.connection)
        else:
            params = Field().get_db_prep_lookup(lookup_type, params_or_value, 
                connection=self.connection, prepared=True)
        assert isinstance(lhs, (list, tuple))
        table, column, _ = lhs
        assert table == self.query.model._meta.db_table
        if column == self.query.model._meta.pk.column:
            column = "_id"
        
        return column, self.LOOKUP_TYPES[lookup_type](params)
    
    def negate(self, k, v):
        if isinstance(v, dict):
            return {k: {"$not": v}}
        return {k: {"$ne": v}}
    
    def build_query(self, aggregates=False):
        assert len([a for a in self.query.alias_map if self.query.alias_refcount[a]]) <= 1
        if not aggregates:
            assert self.query.default_cols
        assert not self.query.distinct
        assert not self.query.extra
        assert not self.query.having
        assert self.query.high_mark is None
        assert not self.query.order_by
        
        filters = self.get_filters(self.query.where)
        return self.connection.db[self.query.model._meta.db_table].find(filters)
    
    def results_iter(self):
        query = self.build_query()
        for row in query:
            yield tuple(
                row[f.column if f is not self.query.model._meta.pk else "_id"]
                for f in self.query.model._meta.fields
            )
    
    def has_results(self):
        try:
            self.build_query()[0]
        except IndexError:
            return False
        else:
            return True
    
    def get_aggregates(self):
        assert len(self.query.aggregates) == 1
        agg = self.query.aggregates.values()[0]
        assert (
            isinstance(agg, self.query.aggregates_module.Count) and (
                agg.col == "*" or 
                isinstance(agg.col, tuple) and agg.col == (self.query.model._meta.db_table, self.query.model._meta.pk.column)
            )
        )
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
        # TODO: Don't use set for everything, use INC and such where
        # appropriate.
        return self.connection.db[self.query.model._meta.db_table].update(
            filters,
            {"$set": dict((f.column, val) for f, o, val in self.query.values)},
            multi=True
        )
