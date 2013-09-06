class Operation(object):
    """
    Base class for migration operations.

    It's responsible for both mutating the in-memory model state
    (see db/migrations/state.py) to represent what it performs, as well
    as actually performing it against a live database.

    Note that some operations won't modify memory state at all (e.g. data
    copying operations), and some will need their modifications to be
    optionally specified by the user (e.g. custom Python code snippets)
    """

    # If this migration can be run in reverse.
    # Some operations are impossible to reverse, like deleting data.
    reversible = True

    def __new__(cls, *args, **kwargs):
        # We capture the arguments to make returning them trivial
        self = object.__new__(cls)
        self._constructor_args = (args, kwargs)
        return self

    def deconstruct(self):
        """
        Returns a 3-tuple of class import path (or just name if it lives
        under django.db.migrations), positional arguments, and keyword
        arguments.
        """
        return (
            self.__class__.__name__,
            self._constructor_args[0],
            self._constructor_args[1],
        )

    def state_forwards(self, app_label, state):
        """
        Takes the state from the previous migration, and mutates it
        so that it matches what this migration would perform.
        """
        raise NotImplementedError('subclasses of Operation must provide a state_forwards() method')

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """
        Performs the mutation on the database schema in the normal
        (forwards) direction.
        """
        raise NotImplementedError('subclasses of Operation must provide a database_forwards() method')

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """
        Performs the mutation on the database schema in the reverse
        direction - e.g. if this were CreateModel, it would in fact
        drop the model's table.
        """
        raise NotImplementedError('subclasses of Operation must provide a database_backwards() method')

    def describe(self):
        """
        Outputs a brief summary of what the action does.
        """
        return "%s: %s" % (self.__class__.__name__, self._constructor_args)
