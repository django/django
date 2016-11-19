from django.db.utils import DatabaseError


class AmbiguityError(Exception):
    """
    Raised when more than one migration matches a name prefix.
    """
    pass


class BadMigrationError(Exception):
    """
    Raised when there's a bad migration (unreadable/bad format/etc.).
    """
    pass


class CircularDependencyError(Exception):
    """
    Raised when there's an impossible-to-resolve circular dependency.
    """
    pass


class InconsistentMigrationHistory(Exception):
    """
    Raised when an applied migration has some of its dependencies not applied.
    """
    pass


class InvalidBasesError(ValueError):
    """
    Raised when a model's base classes can't be resolved.
    """
    pass


class IrreversibleError(RuntimeError):
    """
    Raised when a irreversible migration is about to be reversed.
    """
    pass


class NodeNotFoundError(LookupError):
    """
    Raised when an attempt on a node is made that is not available in the graph.
    """

    def __init__(self, message, node, origin=None):
        self.message = message
        self.origin = origin
        self.node = node

    def __str__(self):
        return self.message

    def __repr__(self):
        return "NodeNotFoundError(%r)" % (self.node, )


class MigrationSchemaMissing(DatabaseError):
    pass


class InvalidMigrationPlan(ValueError):
    pass
