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
        """
        self.children = children[:] if children else []
        self.connector = connector or self.default
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
        return obj

    def __len__(self):
        """
        The size of a node if the number of children it has.
        """
        return len(self.children)

    def __bool__(self):
        """
        For truth value testing.
        """
        return bool(self.children)

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    def __contains__(self, other):
        """
        Returns True is 'other' is a direct child of this instance.
        """
        return other in self.children

    def _prepare_data(self, data):
        """
        A subclass hook for doing subclass specific transformations of the
        given data on combine() or add().
        """
        return data

    def add(self, data, conn_type, squash=True):
        """
        Combines this tree and the data represented by data using the
        connector conn_type. The combine is done by squashing the node other
        away if possible.

        This tree (self) will never be pushed to a child node of the
        combined tree, nor will the connector or negated properties change.

        The function returns a node which can be used in place of data
        regardless if the node other got squashed or not.

        If `squash` is False the data is prepared and added as a child to
        this tree without further logic.
        """
        if data in self.children:
            return data
        data = self._prepare_data(data)
        if not squash:
            self.children.append(data)
            return data
        if self.connector == conn_type:
            # We can reuse self.children to append or squash the node other.
            if (isinstance(data, Node) and not data.negated
                    and (data.connector == conn_type or len(data) == 1)):
                # We can squash the other node's children directly into this
                # node. We are just doing (AB)(CD) == (ABCD) here, with the
                # addition that if the length of the other node is 1 the
                # connector doesn't matter. However, for the len(self) == 1
                # case we don't want to do the squashing, as it would alter
                # self.connector.
                self.children.extend(data.children)
                return self
            else:
                # We could use perhaps additional logic here to see if some
                # children could be used for pushdown here.
                self.children.append(data)
                return data
        else:
            obj = self._new_instance(self.children, self.connector,
                                     self.negated)
            self.connector = conn_type
            self.children = [obj, data]
            return data

    def negate(self):
        """
        Negate the sense of the root connector.
        """
        self.negated = not self.negated
