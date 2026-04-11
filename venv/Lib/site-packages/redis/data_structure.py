import threading
from typing import Any, Generic, List, TypeVar

from redis.typing import Number

T = TypeVar("T")


class WeightedList(Generic[T]):
    """
    Thread-safe weighted list.
    """

    def __init__(self):
        self._items: List[tuple[Any, Number]] = []
        self._lock = threading.RLock()

    def add(self, item: Any, weight: float) -> None:
        """Add item with weight, maintaining sorted order"""
        with self._lock:
            # Find insertion point using binary search
            left, right = 0, len(self._items)
            while left < right:
                mid = (left + right) // 2
                if self._items[mid][1] < weight:
                    right = mid
                else:
                    left = mid + 1

            self._items.insert(left, (item, weight))

    def remove(self, item):
        """Remove first occurrence of item"""
        with self._lock:
            for i, (stored_item, weight) in enumerate(self._items):
                if stored_item == item:
                    self._items.pop(i)
                    return weight
            raise ValueError("Item not found")

    def get_by_weight_range(
        self, min_weight: float, max_weight: float
    ) -> List[tuple[Any, Number]]:
        """Get all items within weight range"""
        with self._lock:
            result = []
            for item, weight in self._items:
                if min_weight <= weight <= max_weight:
                    result.append((item, weight))
            return result

    def get_top_n(self, n: int) -> List[tuple[Any, Number]]:
        """Get top N the highest weighted items"""
        with self._lock:
            return [(item, weight) for item, weight in self._items[:n]]

    def update_weight(self, item, new_weight: float):
        with self._lock:
            """Update weight of an item"""
            old_weight = self.remove(item)
            self.add(item, new_weight)
            return old_weight

    def __iter__(self):
        """Iterate in descending weight order"""
        with self._lock:
            items_copy = (
                self._items.copy()
            )  # Create snapshot as lock released after each 'yield'

        for item, weight in items_copy:
            yield item, weight

    def __len__(self):
        with self._lock:
            return len(self._items)

    def __getitem__(self, index) -> tuple[Any, Number]:
        with self._lock:
            item, weight = self._items[index]
            return item, weight
