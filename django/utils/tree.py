"""
A class for storing a tree graph. Primarily used for filter constructs in the
ORM.
"""

import copy

class Node(object):
    """
    A single internal node in the tree graph. A Node should be viewed as a
    connection (the root) with the children being either leaf nodes or other
    Node instances.
    """
    # Standard connection type. Clients usually won't use this at all and
    # subclasses will usually override the value.
    default = 'DEFAULT'

    def __init__(self, children=None, connection=None):
        self.children = children and children[:] or []
        self.connection = connection or self.default
        self.subtree_parents = []
        self.negated = False

    def __str__(self):
        return '(%s: %s)' % (self.connection, ', '.join([str(c) for c in
            self.children]))

    def __deepcopy__(self, memodict):
        """
        Utility method used by copy.deepcopy().
        """
        obj = self.__class__(connection=self.connection)
        obj.children = copy.deepcopy(self.children, memodict)
        obj.subtree_parents = copy.deepcopy(self.subtree_parents, memodict)
        obj.negated = self.negated
        return obj

    def __len__(self):
        """
        The size of a node if the number of children it has.
        """
        return len(self.children)

    def __nonzero__(self):
        """
        For truth value testing.
        """
        return bool(self.children)

    def __contains__(self, other):
        """
        Returns True is 'other' is a direct child of this instance.
        """
        return other in self.children

    def add(self, node, conn_type):
        """
        Adds a new node to the tree. If the conn_type is the same as the root's
        current connection type, the node is added to the first level.
        Otherwise, the whole tree is pushed down one level and a new root
        connection is created, connecting the existing tree and the new node.
        """
        if len(self.children) < 2:
            self.connection = conn_type
        if self.connection == conn_type:
            if isinstance(node, Node) and (node.connection == conn_type
                    or len(node) == 1):
                self.children.extend(node.children)
            else:
                self.children.append(node)
        else:
            obj = Node(self.children, self.connection)
            self.connection = conn_type
            self.children = [obj, node]

    def negate(self):
        """
        Negate the sense of the root connection.

        Interpreting the meaning of this negate is up to client code. This
        method is useful for implementing "not" arrangements.
        """
        self.children = [NegatedNode(self.children, self.connection)]
        self.connection = self.default

    def start_subtree(self, conn_type):
        """
        Sets up internal state so that new nodes are added to a subtree of the
        current node. The conn_type is required so that the new subtree is
        connected correctly to any existing nodes in the tree.
        """
        if len(self.children) == 1:
            self.connection = conn_type
        elif self.connection != conn_type:
            self.children = [Node(self.children, self.connection)]
            self.connection = conn_type

        self.subtree_parents.append(Node(self.children, self.connection))
        self.connection = self.default
        self.children = []

    def end_subtree(self):
        """
        Closes off the most recently unmatched start_subtree() call.

        This puts the current state into a node of the parent tree and returns
        the current instances state to be the parent.
        """
        obj = self.subtree_parents.pop()
        node = Node(self.children, self.connection)
        self.connection = obj.connection
        self.children = obj.children
        self.children.append(node)

class NegatedNode(Node):
    """
    A class that indicates the connection type should be negated (whatever that
    means -- it's up to the client) when used by the client code.
    """
    def __init__(self, children=None, connection=None):
        super(NegatedNode, self).__init__(children, connection)
        self.negated = True

