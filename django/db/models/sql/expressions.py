from django.core.exceptions import FieldError
from django.db.models.fields import FieldDoesNotExist
from django.db.models.sql.constants import LOOKUP_SEP

class SQLEvaluator(object):
    def __init__(self, expression, query, allow_joins=True):
        self.expression = expression
        self.opts = query.get_meta()
        self.cols = {}

        self.contains_aggregate = False
        self.expression.prepare(self, query, allow_joins)

    def prepare(self):
        return self

    def as_sql(self, qn, connection):
        return self.expression.evaluate(self, qn, connection)

    def relabel_aliases(self, change_map):
        for node, col in self.cols.items():
            if hasattr(col, "relabel_aliases"):
                col.relabel_aliases(change_map)
            else:
                self.cols[node] = (change_map.get(col[0], col[0]), col[1])

    #####################################################
    # Vistor methods for initial expression preparation #
    #####################################################

    def prepare_node(self, node, query, allow_joins):
        for child in node.children:
            if hasattr(child, 'prepare'):
                child.prepare(self, query, allow_joins)

    def prepare_leaf(self, node, query, allow_joins):
        if not allow_joins and LOOKUP_SEP in node.name:
            raise FieldError("Joined field references are not permitted in this query")

        field_list = node.name.split(LOOKUP_SEP)
        if (len(field_list) == 1 and
            node.name in query.aggregate_select.keys()):
            self.contains_aggregate = True
            self.cols[node] = query.aggregate_select[node.name]
        else:
            try:
                field, source, opts, join_list, last, _ = query.setup_joins(
                    field_list, query.get_meta(),
                    query.get_initial_alias(), False)
                col, _, join_list = query.trim_joins(source, join_list, last, False)

                self.cols[node] = (join_list[-1], col)
            except FieldDoesNotExist:
                raise FieldError("Cannot resolve keyword %r into field. "
                                 "Choices are: %s" % (self.name,
                                                      [f.name for f in self.opts.fields]))

    ##################################################
    # Vistor methods for final expression evaluation #
    ##################################################

    def evaluate_node(self, node, qn, connection):
        expressions = []
        expression_params = []
        for child in node.children:
            if hasattr(child, 'evaluate'):
                sql, params = child.evaluate(self, qn, connection)
            else:
                sql, params = '%s', (child,)

            if len(getattr(child, 'children', [])) > 1:
                format = '(%s)'
            else:
                format = '%s'

            if sql:
                expressions.append(format % sql)
                expression_params.extend(params)

        return connection.ops.combine_expression(node.connector, expressions), expression_params

    def evaluate_leaf(self, node, qn, connection):
        col = self.cols[node]
        if hasattr(col, 'as_sql'):
            return col.as_sql(qn, connection), ()
        else:
            return '%s.%s' % (qn(col[0]), qn(col[1])), ()
