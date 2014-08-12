from __future__ import unicode_literals
from django.db import router


class Operation(object):
    """
    Base class for migration operations.

    It's responsible for both mutating the in-memory model state
    (see db/migrations/state.py) to represent what it performs, as well
    as actually performing it against a live database.

    Note that some operations won't modify memory state at all (e.g. data
    copying operations), and some will need their modifications to be
    optionally specified by the user (e.g. custom Python code snippets)

    Due to the way this class deals with deconstruction, it should be
    considered immutable.
    """

    # If this migration can be run in reverse.
    # Some operations are impossible to reverse, like deleting data.
    reversible = True

    # Can this migration be represented as SQL? (things like RunPython cannot)
    reduces_to_sql = True

    # Should this operation be forced as atomic even on backends with no
    # DDL transaction support (i.e., does it have no DDL, like RunPython)
    atomic = False

    serialization_expand_args = []

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

    def references_model(self, name, app_label=None):
        """
        Returns True if there is a chance this operation references the given
        model name (as a string), with an optional app label for accuracy.

        Used for optimization. If in doubt, return True;
        returning a false positive will merely make the optimizer a little
        less efficient, while returning a false negative may result in an
        unusable optimized migration.
        """
        return True

    def references_field(self, model_name, name, app_label=None):
        """
        Returns True if there is a chance this operation references the given
        field name, with an optional app label for accuracy.

        Used for optimization. If in doubt, return True.
        """
        return self.references_model(model_name, app_label)

    def allowed_to_migrate(self, connection_alias, model):
        """
        Returns if we're allowed to migrate the model. Checks the router,
        if it's a proxy, if it's managed, and if it's swapped out.
        """
        return (
            router.allow_migrate(connection_alias, model) and
            not model._meta.proxy and
            not model._meta.swapped and
            model._meta.managed
        )

    def __repr__(self):
        return "<%s %s%s>" % (
            self.__class__.__name__,
            ", ".join(map(repr, self._constructor_args[0])),
            ",".join(" %s=%r" % x for x in self._constructor_args[1].items()),
        )

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (self.deconstruct() == other.deconstruct())

    def __ne__(self, other):
        return not (self == other)
