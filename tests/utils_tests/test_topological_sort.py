from django.test import SimpleTestCase
from django.utils.topological_sort import (
    CyclicDependencyError, stable_topological_sort, topological_sort_as_sets,
)


class TopologicalSortTests(SimpleTestCase):

    def test_basic(self):
        dependency_graph = {
            1: {2, 3},
            2: set(),
            3: set(),
            4: {5, 6},
            5: set(),
            6: {5},
        }
        self.assertEqual(list(topological_sort_as_sets(dependency_graph)), [{2, 3, 5}, {1, 6}, {4}])
        self.assertEqual(stable_topological_sort([1, 2, 3, 4, 5, 6], dependency_graph), [2, 3, 5, 1, 6, 4])

    def test_cyclic_dependency(self):
        msg = 'Cyclic dependency in graph: (1, {2}), (2, {1})'
        with self.assertRaisesMessage(CyclicDependencyError, msg):
            list(topological_sort_as_sets({1: {2}, 2: {1}}))
