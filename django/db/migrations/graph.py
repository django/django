from django.utils.datastructures import SortedSet


class MigrationsGraph(object):
    """
    Represents the digraph of all migrations in a project.

    Each migration is a node, and each dependency is an edge. There are
    no implicit dependencies between numbered migrations - the numbering is
    merely a convention to aid file listing. Every new numbered migration
    has a declared dependency to the previous number, meaning that VCS
    branch merges can be detected and resolved.

    Migrations files can be marked as replacing another set of migrations -
    this is to support the "squash" feature. The graph handler isn't resposible
    for these; instead, the code to load them in here should examine the
    migration files and if the replaced migrations are all either unapplied
    or not present, it should ignore the replaced ones, load in just the
    replacing migration, and repoint any dependencies that pointed to the
    replaced migrations to point to the replacing one.

    A node should be a tuple: (applabel, migration_name) - but the code
    here doesn't really care.
    """

    def __init__(self):
        self.nodes = {}
        self.dependencies = {}
        self.dependents = {}

    def add_node(self, node, implementation):
        self.nodes[node] = implementation

    def add_dependency(self, child, parent):
        self.nodes[child] = None
        self.nodes[parent] = None
        self.dependencies.setdefault(child, set()).add(parent)
        self.dependents.setdefault(parent, set()).add(child)

    def forwards_plan(self, node):
        """
        Given a node, returns a list of which previous nodes (dependencies)
        must be applied, ending with the node itself.
        This is the list you would follow if applying the migrations to
        a database.
        """
        if node not in self.nodes:
            raise ValueError("Node %r not a valid node" % node)
        return self.dfs(node, lambda x: self.dependencies.get(x, set()))

    def backwards_plan(self, node):
        """
        Given a node, returns a list of which dependent nodes (dependencies)
        must be unapplied, ending with the node itself.
        This is the list you would follow if removing the migrations from
        a database.
        """
        if node not in self.nodes:
            raise ValueError("Node %r not a valid node" % node)
        return self.dfs(node, lambda x: self.dependents.get(x, set()))

    def dfs(self, start, get_children):
        """
        Dynamic programming based depth first search, for finding dependencies.
        """
        cache = {}
        def _dfs(start, get_children, path):
            # If we already computed this, use that (dynamic programming)
            if (start, get_children) in cache:
                return cache[(start, get_children)]
            # If we've traversed here before, that's a circular dep
            if start in path:
                raise CircularDependencyException(path[path.index(start):] + [start])
            # Build our own results list, starting with us
            results = []
            results.append(start)
            # We need to add to results all the migrations this one depends on
            children = sorted(get_children(start))
            path.append(start)
            for n in children:
                results = _dfs(n, get_children, path) + results
            path.pop()
            # Use SortedSet to ensure only one instance of each result
            results = list(SortedSet(results))
            # Populate DP cache
            cache[(start, get_children)] = results
            # Done!
            return results
        return _dfs(start, get_children, [])


class CircularDependencyException(Exception):
    """
    Raised when there's an impossible-to-resolve circular dependency.
    """
    pass
