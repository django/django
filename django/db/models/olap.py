from django.db import NotSupportedError
from django.db.models import Func

__all__ = [
    'Cube', 'GroupingSets', 'RollUp',
]

# thoughts for this file:
# output_field
# group by functionality


class SQLiteOLAPMixin:
    def as_sql(self, compiler, connection, function=None, template=None, arg_joiner=None, **extra_context):
        raise NotSupportedError("SQLite does not support %s" % str(self.function))


class Cube(SQLiteOLAPMixin, Func):
    function = "CUBE"
    template = "cube(%(expression)s)"
    requires_custom_group_by = True

    def as_mysql(self, compiler, connection, function=None, template=None, arg_joiner=None, **extra_context):
        return NotSupportedError("MySQL and MariaDB do not support CUBE")


class GroupingSets(SQLiteOLAPMixin, Func):
    function = 'GROUPING SETS'
    template = 'GROUPING SETS(%(expression)s)'
    requires_custom_group_by = True

    def as_mysql(self, compiler, connection, function=None, template=None, arg_joiner=None, **extra_context):
        return NotSupportedError("MySQL and MariaDB do not support GROUPING SETS")


class RollUp(SQLiteOLAPMixin, Func):
    function = 'ROLLUP'
    template = 'rollup(%(expressions)s)'
    requires_custom_group_by = True

    def as_mysql(self, compiler, connection, function=None, template='', arg_joiner=None, **extra_context):
        # https://dev.mysql.com/doc/refman/8.0/en/group-by-modifiers.html
        return super().as_sql(
            compiler, connection, function, template='%(expression)s WITH ROLLUP', arg_joiner=arg_joiner,
            **extra_context,
        )
