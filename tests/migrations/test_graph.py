import warnings

from django.db.migrations.exceptions import (
    CircularDependencyError, NodeNotFoundError,
)
from django.db.migrations.graph import RECURSION_DEPTH_WARNING, MigrationGraph
from django.test import SimpleTestCase
from django.utils.encoding import force_text


class GraphTests(SimpleTestCase):
    """
    Tests the digraph structure.
    """

    def test_simple_graph(self):
        """
        Tests a basic dependency graph:

        app_a:  0001 <-- 0002 <--- 0003 <-- 0004
                                 /
        app_b:  0001 <-- 0002 <-/
        """
        # Build graph
        graph = MigrationGraph()
        graph.add_node(("app_a", "0001"), None)
        graph.add_node(("app_a", "0002"), None)
        graph.add_node(("app_a", "0003"), None)
        graph.add_node(("app_a", "0004"), None)
        graph.add_node(("app_b", "0001"), None)
        graph.add_node(("app_b", "0002"), None)
        graph.add_dependency("app_a.0004", ("app_a", "0004"), ("app_a", "0003"))
        graph.add_dependency("app_a.0003", ("app_a", "0003"), ("app_a", "0002"))
        graph.add_dependency("app_a.0002", ("app_a", "0002"), ("app_a", "0001"))
        graph.add_dependency("app_a.0003", ("app_a", "0003"), ("app_b", "0002"))
        graph.add_dependency("app_b.0002", ("app_b", "0002"), ("app_b", "0001"))
        # Test root migration case
        self.assertEqual(
            graph.forwards_plan(("app_a", "0001")),
            [('app_a', '0001')],
        )
        # Test branch B only
        self.assertEqual(
            graph.forwards_plan(("app_b", "0002")),
            [("app_b", "0001"), ("app_b", "0002")],
        )
        # Test whole graph
        self.assertEqual(
            graph.forwards_plan(("app_a", "0004")),
            [
                ('app_b', '0001'), ('app_b', '0002'), ('app_a', '0001'),
                ('app_a', '0002'), ('app_a', '0003'), ('app_a', '0004'),
            ],
        )
        # Test reverse to b:0002
        self.assertEqual(
            graph.backwards_plan(("app_b", "0002")),
            [('app_a', '0004'), ('app_a', '0003'), ('app_b', '0002')],
        )
        # Test roots and leaves
        self.assertEqual(
            graph.root_nodes(),
            [('app_a', '0001'), ('app_b', '0001')],
        )
        self.assertEqual(
            graph.leaf_nodes(),
            [('app_a', '0004'), ('app_b', '0002')],
        )

    def test_complex_graph(self):
        """
        Tests a complex dependency graph:

        app_a:  0001 <-- 0002 <--- 0003 <-- 0004
                      \        \ /         /
        app_b:  0001 <-\ 0002 <-X         /
                      \          \       /
        app_c:         \ 0001 <-- 0002 <-
        """
        # Build graph
        graph = MigrationGraph()
        graph.add_node(("app_a", "0001"), None)
        graph.add_node(("app_a", "0002"), None)
        graph.add_node(("app_a", "0003"), None)
        graph.add_node(("app_a", "0004"), None)
        graph.add_node(("app_b", "0001"), None)
        graph.add_node(("app_b", "0002"), None)
        graph.add_node(("app_c", "0001"), None)
        graph.add_node(("app_c", "0002"), None)
        graph.add_dependency("app_a.0004", ("app_a", "0004"), ("app_a", "0003"))
        graph.add_dependency("app_a.0003", ("app_a", "0003"), ("app_a", "0002"))
        graph.add_dependency("app_a.0002", ("app_a", "0002"), ("app_a", "0001"))
        graph.add_dependency("app_a.0003", ("app_a", "0003"), ("app_b", "0002"))
        graph.add_dependency("app_b.0002", ("app_b", "0002"), ("app_b", "0001"))
        graph.add_dependency("app_a.0004", ("app_a", "0004"), ("app_c", "0002"))
        graph.add_dependency("app_c.0002", ("app_c", "0002"), ("app_c", "0001"))
        graph.add_dependency("app_c.0001", ("app_c", "0001"), ("app_b", "0001"))
        graph.add_dependency("app_c.0002", ("app_c", "0002"), ("app_a", "0002"))
        # Test branch C only
        self.assertEqual(
            graph.forwards_plan(("app_c", "0002")),
            [('app_b', '0001'), ('app_c', '0001'), ('app_a', '0001'), ('app_a', '0002'), ('app_c', '0002')],
        )
        # Test whole graph
        self.assertEqual(
            graph.forwards_plan(("app_a", "0004")),
            [
                ('app_b', '0001'), ('app_c', '0001'), ('app_a', '0001'),
                ('app_a', '0002'), ('app_c', '0002'), ('app_b', '0002'),
                ('app_a', '0003'), ('app_a', '0004'),
            ],
        )
        # Test reverse to b:0001
        self.assertEqual(
            graph.backwards_plan(("app_b", "0001")),
            [
                ('app_a', '0004'), ('app_c', '0002'), ('app_c', '0001'),
                ('app_a', '0003'), ('app_b', '0002'), ('app_b', '0001'),
            ],
        )
        # Test roots and leaves
        self.assertEqual(
            graph.root_nodes(),
            [('app_a', '0001'), ('app_b', '0001'), ('app_c', '0001')],
        )
        self.assertEqual(
            graph.leaf_nodes(),
            [('app_a', '0004'), ('app_b', '0002'), ('app_c', '0002')],
        )

    def test_circular_graph(self):
        """
        Tests a circular dependency graph.
        """
        # Build graph
        graph = MigrationGraph()
        graph.add_node(("app_a", "0001"), None)
        graph.add_node(("app_a", "0002"), None)
        graph.add_node(("app_a", "0003"), None)
        graph.add_node(("app_b", "0001"), None)
        graph.add_node(("app_b", "0002"), None)
        graph.add_dependency("app_a.0003", ("app_a", "0003"), ("app_a", "0002"))
        graph.add_dependency("app_a.0002", ("app_a", "0002"), ("app_a", "0001"))
        graph.add_dependency("app_a.0001", ("app_a", "0001"), ("app_b", "0002"))
        graph.add_dependency("app_b.0002", ("app_b", "0002"), ("app_b", "0001"))
        graph.add_dependency("app_b.0001", ("app_b", "0001"), ("app_a", "0003"))
        # Test whole graph
        self.assertRaises(
            CircularDependencyError,
            graph.forwards_plan, ("app_a", "0003"),
        )

    def test_circular_graph_2(self):
        graph = MigrationGraph()
        graph.add_node(('A', '0001'), None)
        graph.add_node(('C', '0001'), None)
        graph.add_node(('B', '0001'), None)
        graph.add_dependency('A.0001', ('A', '0001'), ('B', '0001'))
        graph.add_dependency('B.0001', ('B', '0001'), ('A', '0001'))
        graph.add_dependency('C.0001', ('C', '0001'), ('B', '0001'))

        self.assertRaises(
            CircularDependencyError,
            graph.forwards_plan, ('C', '0001')
        )

    def test_graph_recursive(self):
        graph = MigrationGraph()
        root = ("app_a", "1")
        graph.add_node(root, None)
        expected = [root]
        for i in range(2, 750):
            parent = ("app_a", str(i - 1))
            child = ("app_a", str(i))
            graph.add_node(child, None)
            graph.add_dependency(str(i), child, parent)
            expected.append(child)
        leaf = expected[-1]

        forwards_plan = graph.forwards_plan(leaf)
        self.assertEqual(expected, forwards_plan)

        backwards_plan = graph.backwards_plan(root)
        self.assertEqual(expected[::-1], backwards_plan)

    def test_graph_iterative(self):
        graph = MigrationGraph()
        root = ("app_a", "1")
        graph.add_node(root, None)
        expected = [root]
        for i in range(2, 1000):
            parent = ("app_a", str(i - 1))
            child = ("app_a", str(i))
            graph.add_node(child, None)
            graph.add_dependency(str(i), child, parent)
            expected.append(child)
        leaf = expected[-1]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always', RuntimeWarning)
            forwards_plan = graph.forwards_plan(leaf)

        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[-1].category, RuntimeWarning))
        self.assertEqual(str(w[-1].message), RECURSION_DEPTH_WARNING)
        self.assertEqual(expected, forwards_plan)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always', RuntimeWarning)
            backwards_plan = graph.backwards_plan(root)

        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[-1].category, RuntimeWarning))
        self.assertEqual(str(w[-1].message), RECURSION_DEPTH_WARNING)
        self.assertEqual(expected[::-1], backwards_plan)

    def test_plan_invalid_node(self):
        """
        Tests for forwards/backwards_plan of nonexistent node.
        """
        graph = MigrationGraph()
        message = "Node ('app_b', '0001') not a valid node"

        with self.assertRaisesMessage(NodeNotFoundError, message):
            graph.forwards_plan(("app_b", "0001"))

        with self.assertRaisesMessage(NodeNotFoundError, message):
            graph.backwards_plan(("app_b", "0001"))

    def test_missing_parent_nodes(self):
        """
        Tests for missing parent nodes.
        """
        # Build graph
        graph = MigrationGraph()
        graph.add_node(("app_a", "0001"), None)
        graph.add_node(("app_a", "0002"), None)
        graph.add_node(("app_a", "0003"), None)
        graph.add_node(("app_b", "0001"), None)
        graph.add_dependency("app_a.0003", ("app_a", "0003"), ("app_a", "0002"))
        graph.add_dependency("app_a.0002", ("app_a", "0002"), ("app_a", "0001"))
        msg = "Migration app_a.0001 dependencies reference nonexistent parent node ('app_b', '0002')"
        with self.assertRaisesMessage(NodeNotFoundError, msg):
            graph.add_dependency("app_a.0001", ("app_a", "0001"), ("app_b", "0002"))

    def test_missing_child_nodes(self):
        """
        Tests for missing child nodes.
        """
        # Build graph
        graph = MigrationGraph()
        graph.add_node(("app_a", "0001"), None)
        msg = "Migration app_a.0002 dependencies reference nonexistent child node ('app_a', '0002')"
        with self.assertRaisesMessage(NodeNotFoundError, msg):
            graph.add_dependency("app_a.0002", ("app_a", "0002"), ("app_a", "0001"))

    def test_infinite_loop(self):
        """
        Tests a complex dependency graph:

        app_a:        0001 <-
                             \
        app_b:        0001 <- x 0002 <-
                       /               \
        app_c:   0001<-  <------------- x 0002

        And apply squashing on app_c.
        """
        graph = MigrationGraph()

        graph.add_node(("app_a", "0001"), None)
        graph.add_node(("app_b", "0001"), None)
        graph.add_node(("app_b", "0002"), None)
        graph.add_node(("app_c", "0001_squashed_0002"), None)

        graph.add_dependency("app_b.0001", ("app_b", "0001"), ("app_c", "0001_squashed_0002"))
        graph.add_dependency("app_b.0002", ("app_b", "0002"), ("app_a", "0001"))
        graph.add_dependency("app_b.0002", ("app_b", "0002"), ("app_b", "0001"))
        graph.add_dependency("app_c.0001_squashed_0002", ("app_c", "0001_squashed_0002"), ("app_b", "0002"))

        with self.assertRaises(CircularDependencyError):
            graph.forwards_plan(("app_c", "0001_squashed_0002"))

    def test_stringify(self):
        graph = MigrationGraph()
        self.assertEqual(force_text(graph), "Graph: 0 nodes, 0 edges")

        graph.add_node(("app_a", "0001"), None)
        graph.add_node(("app_a", "0002"), None)
        graph.add_node(("app_a", "0003"), None)
        graph.add_node(("app_b", "0001"), None)
        graph.add_node(("app_b", "0002"), None)
        graph.add_dependency("app_a.0002", ("app_a", "0002"), ("app_a", "0001"))
        graph.add_dependency("app_a.0003", ("app_a", "0003"), ("app_a", "0002"))
        graph.add_dependency("app_a.0003", ("app_a", "0003"), ("app_b", "0002"))

        self.assertEqual(force_text(graph), "Graph: 5 nodes, 3 edges")
        self.assertEqual(repr(graph), "<MigrationGraph: nodes=5, edges=3>")
