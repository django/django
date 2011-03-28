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
    # Standard connector type. Clients usually won't use this at all and
    # subclasses will usually override the value.
    default = 'DEFAULT'

    def __init__(self, children=None, connector=None, negated=False):
        """
        Constructs a new Node. If no connector is given, the default will be
        used.

        Warning: You probably don't want to pass in the 'negated' parameter. It
        is NOT the same as constructing a node and calling negate() on the
        result.
        """
        self.children = children and children[:] or []
        self.connector = connector or self.default
        self.subtree_parents = []
        self.negated = negated

    # We need this because of django.db.models.query_utils.Q. Q. __init__() is
    # problematic, but it is a natural Node subclass in all other respects.
    def _new_instance(cls, children=None, connector=None, negated=False):
        """
        This is called to create a new instance of this class when we need new
        Nodes (or subclasses) in the internal code in this class. Normally, it
        just shadows __init__(). However, subclasses with an __init__ signature
        that is not an extension of Node.__init__ might need to implement this
        method to allow a Node to create a new instance of them (if they have
        any extra setting up to do).
        """
        obj = Node(children, connector, negated)
        obj.__class__ = cls
        return obj
    _new_instance = classmethod(_new_instance)

    def __str__(self):
        if self.negated:
            return '(NOT (%s: %s))' % (self.connector, ', '.join([str(c) for c
                    in self.children]))
        return '(%s: %s)' % (self.connector, ', '.join([str(c) for c in
                self.children]))

    def __deepcopy__(self, memodict):
        """
        Utility method used by copy.deepcopy().
        """
        obj = Node(connector=self.connector, negated=self.negated)
        obj.__class__ = self.__class__
        obj.children = copy.deepcopy(self.children, memodict)
        obj.subtree_parents = copy.deepcopy(self.subtree_parents, memodict)
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
        current connector type, the node is added to the first level.
        Otherwise, the whole tree is pushed down one level and a new root
        connector is created, connecting the existing tree and the new node.
        """
        if node in self.children and conn_type == self.connector:
            return
        if len(self.children) < 2:
            self.connector = conn_type
        if self.connector == conn_type:
            if isinstance(node, Node) and (node.connector == conn_type or
                    len(node) == 1):
                self.children.extend(node.children)
            else:
                self.children.append(node)
        else:
            obj = self._new_instance(self.children, self.connector,
                    self.negated)
            self.connector = conn_type
            self.children = [obj, node]

    def negate(self):
        """
        Negate the sense of the root connector. This reorganises the children
        so that the current node has a single child: a negated node containing
        all the previous children. This slightly odd construction makes adding
        new children behave more intuitively.

        Interpreting the meaning of this negate is up to client code. This
        method is useful for implementing "not" arrangements.
        """
        self.children = [self._new_instance(self.children, self.connector,
                not self.negated)]
        self.connector = self.default

    def start_subtree(self, conn_type):
        """
        Sets up internal state so that new nodes are added to a subtree of the
        current node. The conn_type specifies how the sub-tree is joined to the
        existing children.
        """
        if len(self.children) == 1:
            self.connector = conn_type
        elif self.connector != conn_type:
            self.children = [self._new_instance(self.children, self.connector,
                    self.negated)]
            self.connector = conn_type
            self.negated = False

        self.subtree_parents.append(self.__class__(self.children,
                self.connector, self.negated))
        self.connector = self.default
        self.negated = False
        self.children = []

    def end_subtree(self):
        """
        Closes off the most recently unmatched start_subtree() call.

        This puts the current state into a node of the parent tree and returns
        the current instances state to be the parent.
        """
        obj = self.subtree_parents.pop()
        node = self.__class__(self.children, self.connector)
        self.connector = obj.connector
        self.negated = obj.negated
        self.children = obj.children
        self.children.append(node)

