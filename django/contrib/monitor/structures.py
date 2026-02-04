
import heapq
import collections
import threading

class QueryHeap:
    """
    A thread-safe Min-Heap to keep track of the Top K items (by value).
    Used to store the Slowest Queries.
    """
    def __init__(self, k=10):
        self.k = k
        self.heap = []  # List of (duration, sql)
        self.lock = threading.Lock()

    def add(self, duration, sql):
        with self.lock:
            if len(self.heap) < self.k:
                heapq.heappush(self.heap, (duration, sql))
            elif duration > self.heap[0][0]:
                # If this query is slower than the fastest query in our heap (which is the 'cutoff'),
                # replace it. The heap property ensures heap[0] is the minimum of the Top K.
                heapq.heapreplace(self.heap, (duration, sql))

    def get_top_k(self):
        """Return sorted list (descending) of queries."""
        with self.lock:
            # Sort by duration descending
            return sorted(self.heap, key=lambda x: x[0], reverse=True)

class StatsBuffer:
    """
    A thread-safe circular buffer for request latencies.
    """
    def __init__(self, maxlen=100):
        self.buffer = collections.deque(maxlen=maxlen)
        self.lock = threading.Lock()

    def append(self, value):
        with self.lock:
            self.buffer.append(value)

    def get_stats(self):
        with self.lock:
            if not self.buffer:
                return 0, 0, 0
            data = list(self.buffer)
            avg = sum(data) / len(data)
            return min(data), avg, max(data)
            
    def get_data(self):
        with self.lock:
            return list(self.buffer)

class UrlTrieNode:
    def __init__(self):
        self.children = {}
        self.count = 0
        self.total_time = 0.0

class UrlTrie:
    """
    A Trie to store URL stats. 
    Can be used to analyze hot paths.
    """
    def __init__(self):
        self.root = UrlTrieNode()
        self.lock = threading.Lock()

    def add(self, path, duration):
        segments = [s for s in path.strip('/').split('/') if s]
        with self.lock:
            node = self.root
            node.count += 1
            node.total_time += duration
            
            for segment in segments:
                if segment not in node.children:
                    node.children[segment] = UrlTrieNode()
                node = node.children[segment]
                node.count += 1
                node.total_time += duration

    def get_hot_paths(self, limit=5):
        """
        DFS to find the paths with the highest total time.
        This is a simplified version; ideally we'd use a heap during traversal.
        """
        results = []
        with self.lock:
            self._dfs(self.root, "", results)
        
        # Sort by total_time descending
        return sorted(results, key=lambda x: x[1], reverse=True)[:limit]

    def _dfs(self, node, current_path, results):
        if not node.children:
            # Leaf node
            if current_path:
                results.append((current_path, node.total_time))
            return
        
        # Also add intermediate paths if they are significant? 
        # For now, let's just collect leaves or "endpoints".
        # But in a REST API, /users/ might be an endpoint too.
        # We'll just collect everything that has > 0 time, but that's too much.
        # Let's collect only nodes where ratio of self-time vs children-time?
        # Simpler: Just collect all full paths existing in Trie.
        
        for segment, child in node.children.items():
            new_path = f"{current_path}/{segment}"
            # results.append((new_path, child.total_time)) # Add everything?
            self._dfs(child, new_path, results)
            
            # If a node has many visits but no specific child dominates?
            
