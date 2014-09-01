from __future__ import unicode_literals

from .base import Operation


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
            database_operation.database_forwards(app_label, schema_editor, from_state, to_state)
            from_state = to_state

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # We calculate state separately in here since our state functions aren't useful
        base_state = to_state
        for pos, database_operation in enumerate(reversed(self.database_operations)):
            to_state = base_state.clone()
            for dbop in self.database_operations[:-(pos + 1)]:
                dbop.state_forwards(app_label, to_state)
            from_state = base_state.clone()
            database_operation.state_forwards(app_label, from_state)
            database_operation.database_backwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Custom state/database change combination"


class RunSQL(Operation):
    """
    Runs some raw SQL. A reverse SQL statement may be provided.

    Also accepts a list of operations that represent the state change effected
    by this SQL change, in case it's custom column/table creation/deletion.
    """

    def __init__(self, sql, reverse_sql=None, state_operations=None):
        self.sql = sql
        self.reverse_sql = reverse_sql
        self.state_operations = state_operations or []

    @property
    def reversible(self):
        return self.reverse_sql is not None

    def state_forwards(self, app_label, state):
        for state_operation in self.state_operations:
            state_operation.state_forwards(app_label, state)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        statements = schema_editor.connection.ops.prepare_sql_script(self.sql)
        for statement in statements:
            schema_editor.execute(statement)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if self.reverse_sql is None:
            raise NotImplementedError("You cannot reverse this operation")
        statements = schema_editor.connection.ops.prepare_sql_script(self.reverse_sql)
        for statement in statements:
            schema_editor.execute(statement)

    def describe(self):
        return "Raw SQL operation"


class RunPython(Operation):
    """
    Runs Python code in a context suitable for doing versioned ORM operations.
    """

    reduces_to_sql = False

    def __init__(self, code, reverse_code=None, atomic=True):
        self.atomic = atomic
        # Forwards code
        if not callable(code):
            raise ValueError("RunPython must be supplied with a callable")
        self.code = code
        # Reverse code
        if reverse_code is None:
            self.reverse_code = None
        else:
            if not callable(reverse_code):
                raise ValueError("RunPython must be supplied with callable arguments")
            self.reverse_code = reverse_code

    @property
    def reversible(self):
        return self.reverse_code is not None

    def state_forwards(self, app_label, state):
        # RunPython objects have no state effect. To add some, combine this
        # with SeparateDatabaseAndState.
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        # We now execute the Python code in a context that contains a 'models'
        # object, representing the versioned models as an app registry.
        # We could try to override the global cache, but then people will still
        # use direct imports, so we go with a documentation approach instead.
        self.code(from_state.render(), schema_editor)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if self.reverse_code is None:
            raise NotImplementedError("You cannot reverse this operation")
        self.reverse_code(from_state.render(), schema_editor)

    def describe(self):
        return "Raw Python operation"
