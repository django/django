"""
A class for storing a tree graph. Primarily used for filter constructs in the
ORM.
"""

import copy

from django.utils.hashable import make_hashable


class Node:
    """
    A single internal node in the tree graph. A Node should be viewed as a
    connection (the root) with the children being either leaf nodes or other
    Node instances.
    """

    # Standard connector type. Clients usually won't use this at all and
    # subclasses will usually override the value.
    default = "DEFAULT"

    def __init__(self, children=None, connector=None, negated=False):
        """Construct a new Node. If no connector is given, use the default."""
        self.children = children[:] if children else []
        self.connector = connector or self.default
        self.negated = negated

    @classmethod
    def create(cls, children=None, connector=None, negated=False):
        """
        Create a new instance using Node() instead of __init__() as some
        subclasses, e.g. django.db.models.query_utils.Q, may implement a custom
        __init__() with a signature that conflicts with the one defined in
        Node.__init__().
        """
        obj = Node(children, connector, negated)
        obj.__class__ = cls
        return obj

    def __str__(self):
        template = "(NOT (%s: %s))" if self.negated else "(%s: %s)"
        return template % (self.connector, ", ".join(str(c) for c in self.children))

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self)

    def __deepcopy__(self, memodict):
        obj = Node(connector=self.connector, negated=self.negated)
        obj.__class__ = self.__class__
        obj.children = copy.deepcopy(self.children, memodict)
        return obj

    def __len__(self):
        """Return the number of children this node has."""
        return len(self.children)

    def __bool__(self):
        """Return whether or not this node has children."""
        return bool(self.children)

    def __contains__(self, other):
        """Return True if 'other' is a direct child of this instance."""
        return other in self.children

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self.connector == other.connector
            and self.negated == other.negated
            and self.children == other.children
        )

    def __hash__(self):
        return hash(
            (
                self.__class__,
                self.connector,
                self.negated,
                *make_hashable(self.children),
            )
        )

    def add(self, data, conn_type):
        """
        Combine this tree and the data represented by data using the
        connector conn_type. The combine is done by squashing the node other
        away if possible.

        This tree (self) will never be pushed to a child node of the
        combined tree, nor will the connector or negated properties change.

        Return a node which can be used in place of data regardless if the
        node other got squashed or not.
        """
        if self.connector != conn_type:
            obj = self.create(self.children, self.connector, self.negated)
            self.connector = conn_type
            self.children = [obj, data]
            return data
        elif (
            isinstance(data, Node)
            and not data.negated
            and (data.connector == conn_type or len(data) == 1)
        ):
            # We can squash the other node's children directly into this node.
            # We are just doing (AB)(CD) == (ABCD) here, with the addition that
            # if the length of the other node is 1 the connector doesn't
            # matter. However, for the len(self) == 1 case we don't want to do
            # the squashing, as it would alter self.connector.
            self.children.extend(data.children)
            return self
        else:
            # We could use perhaps additional logic here to see if some
            # children could be used for pushdown here.
            self.children.append(data)
            return data

    def negate(self):
        """Negate the sense of the root connector."""
        self.negated = not self.negated
