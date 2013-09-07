import re
from .base import Operation
from django.db import models, router
from django.db.migrations.state import ModelState


class SeparateDatabaseAndState(Operation):
    """
    Takes two lists of operations - ones that will be used for the database,
    and ones that will be used for the state change. This allows operations
    that don't support state change to have it applied, or have operations
    that affect the state or not the database, or so on.
    """

    def __init__(self, database_operations=None, state_operations=None):
        self.database_operations = database_operations or []
        self.state_operations = state_operations or []

    def state_forwards(self, app_label, state):
        for state_operation in self.state_operations:
            state_operation.state_forwards(app_label, state)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        # We calculate state separately in here since our state functions aren't useful
        for database_operation in self.database_operations:
            to_state = from_state.clone()
            database_operation.state_forwards(app_label, to_state)
            database_operation.database_forwards(self, app_label, schema_editor, from_state, to_state)
            from_state = to_state

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # We calculate state separately in here since our state functions aren't useful
        base_state = to_state
        for pos, database_operation in enumerate(reversed(self.database_operations)):
            to_state = base_state.clone()
            for dbop in self.database_operations[:-(pos+1)]:
                dbop.state_forwards(app_label, to_state)
            from_state = base_state.clone()
            database_operation.state_forwards(app_label, from_state)
            database_operation.database_backwards(self, app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Custom state/database change combination"


class RunSQL(Operation):
    """
    Runs some raw SQL - a single statement by default, but it will attempt
    to parse and split it into multiple statements if multiple=True.

    A reverse SQL statement may be provided.

    Also accepts a list of operations that represent the state change effected
    by this SQL change, in case it's custom column/table creation/deletion.
    """

    def __init__(self, sql, reverse_sql=None, state_operations=None, multiple=False):
        self.sql = sql
        self.reverse_sql = reverse_sql
        self.state_operations = state_operations or []
        self.multiple = multiple

    def state_forwards(self, app_label, state):
        for state_operation in self.state_operations:
            state_operation.state_forwards(app_label, state)

    def _split_sql(self, sql):
        regex = r"(?mx) ([^';]* (?:'[^']*'[^';]*)*)"
        comment_regex = r"(?mx) (?:^\s*$)|(?:--.*$)"
        # First, strip comments
        sql = "\n".join([x.strip().replace("%", "%%") for x in re.split(comment_regex, sql) if x.strip()])
        # Now get each statement
        for st in re.split(regex, sql)[1:][::2]:
            yield st

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if self.multiple:
            statements = self._split_sql(self.sql)
        else:
            statements = [self.sql]
        for statement in statements:
            schema_editor.execute(statement)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if self.reverse_sql is None:
            raise NotImplementedError("You cannot reverse this operation")
        if self.multiple:
            statements = self._split_sql(self.reverse_sql)
        else:
            statements = [self.reverse_sql]
        for statement in statements:
            schema_editor.execute(statement)

    def describe(self):
        return "Raw SQL operation"
