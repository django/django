from pymemcache.client.murmur3 import murmur3_32


class RendezvousHash:
    """
    Implements the Highest Random Weight (HRW) hashing algorithm most
    commonly referred to as rendezvous hashing.

    Originally developed as part of python-clandestined.

    Copyright (c) 2014 Ernest W. Durbin III
    """

    def __init__(self, nodes=None, seed=0, hash_function=murmur3_32):
        """
        Constructor.
        """
        self.nodes = []
        self.seed = seed
        if nodes is not None:
            self.nodes = nodes
        self.hash_function = lambda x: hash_function(x, seed)

    def add_node(self, node):
        if node not in self.nodes:
            self.nodes.append(node)

    def remove_node(self, node):
        if node in self.nodes:
            self.nodes.remove(node)
        else:
            raise ValueError("No such node %s to remove" % (node))

    def get_node(self, key):
        high_score = -1
        winner = None

        for node in self.nodes:
            score = self.hash_function(f"{node}-{key}")

            if score > high_score:
                (high_score, winner) = (score, node)
            elif score == high_score:
                (high_score, winner) = (score, max(str(node), str(winner)))

        return winner
