"""
Query subclasses which provide extra functionality beyond simple data
retrieval.
"""

from django.core.exceptions import FieldError
from django.db.models.aggregates import Aggregate
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Col, Combinable, F, Func, Subquery
from django.db.models.sql.constants import (
    GET_ITERATOR_CHUNK_SIZE,
    NO_RESULTS,
    ROW_COUNT,
)
from django.db.models.sql.query import Query

__all__ = ["DeleteQuery", "UpdateQuery", "InsertQuery", "AggregateQuery"]


class DeleteQuery(Query):
    """A DELETE SQL query."""

    compiler = "SQLDeleteCompiler"

    def do_query(self, table, where, using):
        self.alias_map = {table: self.alias_map[table]}
        self.where = where
        return self.get_compiler(using).execute_sql(ROW_COUNT)

    def delete_batch(self, pk_list, using):
        """
        Set up and execute delete queries for all the objects in pk_list.

        More than one physical query may be executed if there are a
        lot of values in pk_list.
        """
        # number of objects deleted
        num_deleted = 0
        field = self.get_meta().pk
        for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
            self.clear_where()
            self.add_filter(
                f"{field.attname}__in",
                pk_list[offset : offset + GET_ITERATOR_CHUNK_SIZE],
            )
            num_deleted += self.do_query(
                self.get_meta().db_table, self.where, using=using
            )
        return num_deleted


class UpdateQuery(Query):
    """An UPDATE SQL query."""

    compiler = "SQLUpdateCompiler"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_query()

    def _setup_query(self):
        """
        Run on initialization and at the end of chaining. Any attributes that
        would normally be set in __init__() should go here instead.
        """
        self.values = []
        self.related_ids = None
        self.related_updates = {}

    def clone(self):
        obj = super().clone()
        obj.related_updates = self.related_updates.copy()
        return obj

    def update_batch(self, pk_list, values, using):
        self.add_update_values(values)
        for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
            self.clear_where()
            self.add_filter(
                "pk__in", pk_list[offset : offset + GET_ITERATOR_CHUNK_SIZE]
            )
            self.get_compiler(using).execute_sql(NO_RESULTS)

    def add_update_values(self, values):
        """
        Convert a dictionary of field name to value mappings into an update
        query. This is the entry point for the public update() method on
        querysets.
        """
        values_seq = []
        for name, val in values.items():
            field = self.get_meta().get_field(name)
            model = field.model._meta.concrete_model
            if field.name == "pk" and model._meta.is_composite_pk:
                raise FieldError(
                    "Composite primary key fields must be updated individually."
                )
            if not field.concrete:
                raise FieldError(
                    "Cannot update model field %r (only concrete fields are permitted)."
                    % field
                )
            if model is not self.get_meta().concrete_model:
                self.add_related_update(model, field, val)
                continue
            values_seq.append((field, model, val))
        return self.add_update_fields(values_seq)

    def add_update_fields(self, values_seq):
        """
        Append a sequence of (field, model, value) triples to the internal list
        that will be used to generate the UPDATE query. Might be more usefully
        called add_update_targets() to hint at the extra information here.
        """
        for field, model, val in values_seq:
            # Omit generated fields.
            if field.generated:
                continue
            if isinstance(val, (F, Aggregate)) and self.annotations:
                val = self._write_subquery(field, model, val)
            elif hasattr(val, "resolve_expression"):
                # Resolve expressions here so that annotations are no longer
                # needed
                val = val.resolve_expression(self, allow_joins=False, for_save=True)
            self.values.append((field, model, val))

    def _write_subquery(self, model_field, model, val):
        def get_direct_aggregate_query():
            expression, filter, order_by = val.get_source_expressions()
            expression = expression.name if isinstance(expression, F) else expression
            related_name, field = expression.split(LOOKUP_SEP, 1)
            related_field = model._meta.get_field(related_name)
            related_model = related_field.related_model
            func = val.__class__
            return (
                related_model.objects.filter(**filter if filter else {})
                .order_by(*order_by if order_by else ())
                .values(related_field.field.attname)
                .annotate(expression=func(field))
                .values(expression)
            )

        def get_direct_annotation_query(
            model=model, val=val, annotations={}, group_by=()
        ):
            if isinstance(val, F):
                annotated_field = val.name
                resolved_annotation = annotations.get(annotated_field)
                filters = {}
                order_by = ()
                if isinstance(resolved_annotation, Aggregate):
                    val = resolved_annotation
                    resolved_annotation, filters, order_by = (
                        resolved_annotation.get_source_expressions()
                    )
                elif isinstance(resolved_annotation, Func):
                    args, kwargs = getattr(
                        resolved_annotation, "_constructor_args", ((), {})
                    )
                    _args = ()
                    for arg in args:
                        if isinstance(arg, Col):
                            related_field = arg.target.attname
                            pre_related_field = (
                                arg.target.model.relatedpoint_set.field.attname.split(
                                    "_id", 1
                                )
                            )
                            _args += (
                                resolved_annotation.__class__(
                                    f"{pre_related_field[0]}__{related_field}"
                                ),
                            )
                        else:
                            _args += (arg,)

                    return get_direct_annotation_query(
                        model=model,
                        val=annotated_field,
                        annotations={
                            annotated_field: resolved_annotation.__class__(
                                *_args, **kwargs
                            )
                        },
                    )
                target_field = resolved_annotation.target.attname
                related_model = resolved_annotation.target.model
                return (
                    get_direct_annotation_query(
                        model=related_model,
                        val=annotated_field,
                        group_by=(target_field,),
                        annotations={annotated_field: val.__class__(target_field)},
                    )
                    .filter(**filters if filters else {})
                    .order_by(*order_by if order_by else ())
                )
            else:
                return (
                    model.objects.values(*group_by).annotate(**annotations).values(val)
                )

        if isinstance(val, Aggregate):
            query = get_direct_aggregate_query()
        else:
            query = get_direct_annotation_query(annotations=self.annotations)
        return Subquery(query[:1])

    def add_related_update(self, model, field, value):
        """
        Add (name, value) to an update query for an ancestor model.

        Update are coalesced so that only one update query per ancestor is run.
        """
        self.related_updates.setdefault(model, []).append((field, None, value))

    def get_related_updates(self):
        """
        Return a list of query objects: one for each update required to an
        ancestor model. Each query will have the same filtering conditions as
        the current query but will only update a single table.
        """
        if not self.related_updates:
            return []
        result = []
        for model, values in self.related_updates.items():
            query = UpdateQuery(model)
            query.values = values
            if self.related_ids is not None:
                query.add_filter("pk__in", self.related_ids[model])
            result.append(query)
        return result


class InsertQuery(Query):
    compiler = "SQLInsertCompiler"

    def __init__(
        self, *args, on_conflict=None, update_fields=None, unique_fields=None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.fields = []
        self.objs = []
        self.on_conflict = on_conflict
        self.update_fields = update_fields or []
        self.unique_fields = unique_fields or []

    def insert_values(self, fields, objs, raw=False):
        self.fields = fields
        self.objs = objs
        self.raw = raw


class AggregateQuery(Query):
    """
    Take another query as a parameter to the FROM clause and only select the
    elements in the provided list.
    """

    compiler = "SQLAggregateCompiler"

    def __init__(self, model, inner_query):
        self.inner_query = inner_query
        super().__init__(model)
