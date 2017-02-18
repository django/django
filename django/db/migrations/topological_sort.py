def topological_sort_as_sets(dependency_graph):
    """Variation of Kahn's algorithm (1962) that returns sets.

    Takes a dependency graph as a dictionary of node => dependencies.

    Yields sets of items in topological order, where the first set contains
    all nodes without dependencies, and each following set contains all
    nodes that depend on the nodes in the previously yielded sets.
    """
    todo = dependency_graph.copy()
    while todo:
        current = {node for node, deps in todo.items() if len(deps) == 0}

        if not current:
            raise ValueError('Cyclic dependency in graph: {}'.format(
                ', '.join(repr(x) for x in todo.items())))

        yield current

        # remove current from todo's nodes & dependencies
        todo = {node: (dependencies - current) for node, dependencies in
                todo.items() if node not in current}


def stable_topological_sort(l, dependency_graph):
    result = []
    for layer in topological_sort_as_sets(dependency_graph):
        for node in l:
            if node in layer:
                result.append(node)
    return result
