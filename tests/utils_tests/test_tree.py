import copy
import unittest

from django.db.models.sql import AND, OR
from django.utils.tree import Node


class NodeTests(unittest.TestCase):
    def setUp(self):
        self.node1_children = [("a", 1), ("b", 2)]
        self.node1 = Node(self.node1_children)
        self.node2 = Node()

    def test_str(self):
        self.assertEqual(str(self.node1), "(DEFAULT: ('a', 1), ('b', 2))")
        self.assertEqual(str(self.node2), "(DEFAULT: )")

    def test_repr(self):
        self.assertEqual(repr(self.node1), "<Node: (DEFAULT: ('a', 1), ('b', 2))>")
        self.assertEqual(repr(self.node2), "<Node: (DEFAULT: )>")

    def test_hash(self):
        node3 = Node(self.node1_children, negated=True)
        node4 = Node(self.node1_children, connector="OTHER")
        node5 = Node(self.node1_children)
        node6 = Node([["a", 1], ["b", 2]])
        node7 = Node([("a", [1, 2])])
        node8 = Node([("a", (1, 2))])
        self.assertNotEqual(hash(self.node1), hash(self.node2))
        self.assertNotEqual(hash(self.node1), hash(node3))
        self.assertNotEqual(hash(self.node1), hash(node4))
        self.assertEqual(hash(self.node1), hash(node5))
        self.assertEqual(hash(self.node1), hash(node6))
        self.assertEqual(hash(self.node2), hash(Node()))
        self.assertEqual(hash(node7), hash(node8))

    def test_len(self):
        self.assertEqual(len(self.node1), 2)
        self.assertEqual(len(self.node2), 0)

    def test_bool(self):
        self.assertTrue(self.node1)
        self.assertFalse(self.node2)

    def test_contains(self):
        self.assertIn(("a", 1), self.node1)
        self.assertNotIn(("a", 1), self.node2)

    def test_add(self):
        # start with the same children of node1 then add an item
        node3 = Node(self.node1_children)
        node3_added_child = ("c", 3)
        # add() returns the added data
        self.assertEqual(node3.add(node3_added_child, Node.default), node3_added_child)
        # we added exactly one item, len() should reflect that
        self.assertEqual(len(self.node1) + 1, len(node3))
        self.assertEqual(str(node3), "(DEFAULT: ('a', 1), ('b', 2), ('c', 3))")

    def test_add_eq_child_mixed_connector(self):
        node = Node(["a", "b"], OR)
        self.assertEqual(node.add("a", AND), "a")
        self.assertEqual(node, Node([Node(["a", "b"], OR), "a"], AND))

    def test_negate(self):
        # negated is False by default
        self.assertFalse(self.node1.negated)
        self.node1.negate()
        self.assertTrue(self.node1.negated)
        self.node1.negate()
        self.assertFalse(self.node1.negated)

    def test_new_instance(self):
        SubNode = type("SubNode", (Node,), {})

        a = SubNode([SubNode(["a", "b"], OR), "c"], AND)
        b = SubNode._new_instance(a.children, a.connector, a.negated)
        self.assertEqual(a, b)
        # Children lists are the same object, but equal.
        self.assertIsNot(a.children, b.children)
        self.assertEqual(a.children, b.children)
        # Child Node objects are the same objects.
        for a_child, b_child in zip(a.children, b.children):
            if isinstance(a_child, Node):
                self.assertIs(a_child, b_child)
            self.assertEqual(a_child, b_child)

    def test_copy(self):
        a = Node([Node(["a", "b"], OR), "c"], AND)
        b = copy.copy(a)
        self.assertEqual(a, b)
        # Children lists are the same object.
        self.assertIs(a.children, b.children)
        # Child Node objects are the same objects.
        for a_child, b_child in zip(a.children, b.children):
            if isinstance(a_child, Node):
                self.assertIs(a_child, b_child)
            self.assertEqual(a_child, b_child)

    def test_deepcopy(self):
        a = Node([Node(["a", "b"], OR), "c"], AND)
        b = copy.deepcopy(a)
        self.assertEqual(a, b)
        # Children lists are not be the same object, but equal.
        self.assertIsNot(a.children, b.children)
        self.assertEqual(a.children, b.children)
        # Child Node objects are not be the same objects.
        for a_child, b_child in zip(a.children, b.children):
            if isinstance(a_child, Node):
                self.assertIsNot(a_child, b_child)
            self.assertEqual(a_child, b_child)

    def test_eq_children(self):
        node = Node(self.node1_children)
        self.assertEqual(node, self.node1)
        self.assertNotEqual(node, self.node2)

    def test_eq_connector(self):
        new_node = Node(connector="NEW")
        default_node = Node(connector="DEFAULT")
        self.assertEqual(default_node, self.node2)
        self.assertNotEqual(default_node, new_node)

    def test_eq_negated(self):
        node = Node(negated=False)
        negated = Node(negated=True)
        self.assertNotEqual(negated, node)
