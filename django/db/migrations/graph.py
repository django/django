from __future__ import unicode_literals

import warnings
from collections import deque
from functools import total_ordering

from django.db.migrations.state import ProjectState
from django.utils.datastructures import OrderedSet
from django.utils.encoding import python_2_unicode_compatible

from .exceptions import CircularDependencyError, NodeNotFoundError

RECURSION_DEPTH_WARNING = (
    "Maximum recursion depth exceeded while generating migration graph, "
    "falling back to iterative approach. If you're experiencing performance issues, "
    "consider squashing migrations as described at "
    "https://docs.djangoproject.com/en/dev/topics/migrations/#squashing-migrations."
)


@python_2_unicode_compatible
@total_ordering
class Node(object):
    """
    A single node in the migration graph. Contains direct links to adjacent
    nodes in either direction.
    """
    def __init__(self, key):
        self.key = key
        self.children = set()
        self.parents = set()

    def __eq__(self, other):
        return self.key == other

    def __lt__(self, other):
        return self.key < other

    def __hash__(self):
        return hash(self.key)

    def __getitem__(self, item):
        return self.key[item]

    def __str__(self):
        return str(self.key)

    def __repr__(self):
        return '<Node: (%r, %r)>' % self.key

    def add_child(self, child):
        self.children.add(child)

    def add_parent(self, parent):
        self.parents.add(parent)

    # Use manual caching, @cached_property effectively doubles the
    # recursion depth for each recursion.
    def ancestors(self):
        # Use self.key instead of self to speed up the frequent hashing
        # when constructing an OrderedSet.
        if '_ancestors' not in self.__dict__:
            ancestors = deque([self.key])
            for parent in sorted(self.parents):
                ancestors.extendleft(reversed(parent.ancestors()))
            self.__dict__['_ancestors'] = list(OrderedSet(ancestors))
        return self.__dict__['_ancestors']

    # Use manual caching, @cached_property effectively doubles the
    # recursion depth for each recursion.
    def descendants(self):
        # Use self.key instead of self to speed up the frequent hashing
        # when constructing an OrderedSet.
        if '_descendants' not in self.__dict__:
            descendants = deque([self.key])
            for child in sorted(self.children):
                descendants.extendleft(reversed(child.descendants()))
            self.__dict__['_descendants'] = list(OrderedSet(descendants))
        return self.__dict__['_descendants']


@python_2_unicode_compatible
class MigrationGraph(object):
    """
    Represents the digraph of all migrations in a project.

    Each migration is a node, and each dependency is an edge. There are
    no implicit dependencies between numbered migrations - the numbering is
    merely a convention to aid file listing. Every new numbered migration
    has a declared dependency to the previous number, meaning that VCS
    branch merges can be detected and resolved.

    Migrations files can be marked as replacing another set of migrations -
    this is to support the "squash" feature. The graph handler isn't responsible
    for these; instead, the code to load them in here should examine the
    migration files and if the replaced migrations are all either unapplied
    or not present, it should ignore the replaced ones, load in just the
    replacing migration, and repoint any dependencies that pointed to the
    replaced migrations to point to the replacing one.

    A node should be a tuple: (app_path, migration_name). The tree special-cases
    things within an app - namely, root nodes and leaf nodes ignore dependencies
    to other apps.
    """

    def __init__(self):
        self.node_map = {}
        self.nodes = {}
        self.cached = False

    def add_node(self, key, implementation):
        node = Node(key)
        self.node_map[key] = node
        self.nodes[key] = implementation
        self.clear_cache()

    def add_dependency(self, migration, child, parent):
        if child not in self.nodes:
            raise NodeNotFoundError(
                "Migration %s dependencies reference nonexistent child node %r" % (migration, child),
                child
            )
        if parent not in self.nodes:
            raise NodeNotFoundError(
                "Migration %s dependencies reference nonexistent parent node %r" % (migration, parent),
                parent
            )
        self.node_map[child].add_parent(self.node_map[parent])
        self.node_map[parent].add_child(self.node_map[child])
        self.clear_cache()

    def clear_cache(self):
        if self.cached:
            for node in self.nodes:
                self.node_map[node].__dict__.pop('_ancestors', None)
                self.node_map[node].__dict__.pop('_descendants', None)
            self.cached = False

    def forwards_plan(self, target):
        """
        Given a node, returns a list of which previous nodes (dependencies)
        must be applied, ending with the node itself.
        This is the list you would follow if applying the migrations to
        a database.
        """
        if target not in self.nodes:
            raise NodeNotFoundError("Node %r not a valid node" % (target, ), target)
        # Use parent.key instead of parent to speed up the frequent hashing in ensure_not_cyclic
        self.ensure_not_cyclic(target, lambda x: (parent.key for parent in self.node_map[x].parents))
        self.cached = True
        node = self.node_map[target]
        try:
            return node.ancestors()
        except RuntimeError:
            # fallback to iterative dfs
            warnings.warn(RECURSION_DEPTH_WARNING, RuntimeWarning)
            return self.iterative_dfs(node)

    def backwards_plan(self, target):
        """
        Given a node, returns a list of which dependent nodes (dependencies)
        must be unapplied, ending with the node itself.
        This is the list you would follow if removing the migrations from
        a database.
        """
        if target not in self.nodes:
            raise NodeNotFoundError("Node %r not a valid node" % (target, ), target)
        # Use child.key instead of child to speed up the frequent hashing in ensure_not_cyclic
        self.ensure_not_cyclic(target, lambda x: (child.key for child in self.node_map[x].children))
        self.cached = True
        node = self.node_map[target]
        try:
            return node.descendants()
        except RuntimeError:
            # fallback to iterative dfs
            warnings.warn(RECURSION_DEPTH_WARNING, RuntimeWarning)
            return self.iterative_dfs(node, forwards=False)

    def iterative_dfs(self, start, forwards=True):
        """
        Iterative depth first search, for finding dependencies.
        """
        visited = deque()
        visited.append(start)
        if forwards:
            stack = deque(sorted(start.parents))
        else:
            stack = deque(sorted(start.children))
        while stack:
            node = stack.popleft()
            visited.appendleft(node)
            if forwards:
                children = sorted(node.parents, reverse=True)
            else:
                children = sorted(node.children, reverse=True)
            # reverse sorting is needed because prepending using deque.extendleft
            # also effectively reverses values
            stack.extendleft(children)

        return list(OrderedSet(visited))

    def root_nodes(self, app=None):
        """
        Returns all root nodes - that is, nodes with no dependencies inside
        their app. These are the starting point for an app.
        """
        roots = set()
        for node in self.nodes:
            if (not any(key[0] == node[0] for key in self.node_map[node].parents)
                    and (not app or app == node[0])):
                roots.add(node)
        return sorted(roots)

    def leaf_nodes(self, app=None):
        """
        Returns all leaf nodes - that is, nodes with no dependents in their app.
        These are the "most current" version of an app's schema.
        Having more than one per app is technically an error, but one that
        gets handled further up, in the interactive command - it's usually the
        result of a VCS merge and needs some user input.
        """
        leaves = set()
        for node in self.nodes:
            if (not any(key[0] == node[0] for key in self.node_map[node].children)
                    and (not app or app == node[0])):
                leaves.add(node)
        return sorted(leaves)

    def ensure_not_cyclic(self, start, get_children):
        # Algo from GvR:
        # http://neopythonic.blogspot.co.uk/2009/01/detecting-cycles-in-directed-graph.html
        todo = set(self.nodes)
        while todo:
            node = todo.pop()
            stack = [node]
            while stack:
                top = stack[-1]
                for node in get_children(top):
                    if node in stack:
                        cycle = stack[stack.index(node):]
                        raise CircularDependencyError(", ".join("%s.%s" % n for n in cycle))
                    if node in todo:
                        stack.append(node)
                        todo.remove(node)
                        break
                else:
                    node = stack.pop()

    def __str__(self):
        return 'Graph: %s nodes, %s edges' % self._nodes_and_edges()

    def __repr__(self):
        nodes, edges = self._nodes_and_edges()
        return '<%s: nodes=%s, edges=%s>' % (self.__class__.__name__, nodes, edges)

    def _nodes_and_edges(self):
        return len(self.nodes), sum(len(node.parents) for node in self.node_map.values())

    def make_state(self, nodes=None, at_end=True, real_apps=None):
        """
        Given a migration node or nodes, returns a complete ProjectState for it.
        If at_end is False, returns the state before the migration has run.
        If nodes is not provided, returns the overall most current project state.
        """
        if nodes is None:
            nodes = list(self.leaf_nodes())
        if len(nodes) == 0:
            return ProjectState()
        if not isinstance(nodes[0], tuple):
            nodes = [nodes]
        plan = []
        for node in nodes:
            for migration in self.forwards_plan(node):
                if migration not in plan:
                    if not at_end and migration in nodes:
                        continue
                    plan.append(migration)
        project_state = ProjectState(real_apps=real_apps)
        for node in plan:
            project_state = self.nodes[node].mutate_state(project_state, preserve=False)
        return project_state

    def __contains__(self, node):
        return node in self.nodes
