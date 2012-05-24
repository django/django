"""
Classes to represent the default SQL aggregate functions
"""

from django.db.models.sql import expressions

class Aggregate(expressions.SQLEvaluator):
    """
    Default SQL Aggregate.
    """

    def __init__(self, expression, query, promote_joins=False, is_summary=False, **extra):
        """Instantiate an SQL aggregate

         * expression is the aggregate query expression to be evaluated.
         * query is the backend-specific query instance to which the aggregate
           is to be added.
         * promote_joins dictates whether or not table joins will be promoted
           to LEFT OUTER when constructing the SQL for the query.
         * extra is a dictionary of additional data to provide for the
           aggregate definition
        """
        self.is_summary = is_summary
        self.extra = extra
        super(Aggregate, self).__init__(expression, query, promote_joins=promote_joins)

Avg = Aggregate
Count = Aggregate
Max = Aggregate
Min = Aggregate
StdDev = Aggregate
Sum = Aggregate
Variance = Aggregate
