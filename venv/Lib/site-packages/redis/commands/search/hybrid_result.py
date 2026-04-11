from dataclasses import dataclass
from typing import Any, Dict, List, Union


@dataclass
class HybridResult:
    """
    Represents the result of a hybrid search query execution
    Returned by the `hybrid_search` command, when using RESP version 2.
    """

    total_results: int
    results: List[Dict[str, Any]]
    warnings: List[Union[str, bytes]]
    execution_time: float


class HybridCursorResult:
    def __init__(self, search_cursor_id: int, vsim_cursor_id: int) -> None:
        """
        Represents the result of a hybrid search query execution with cursor

        search_cursor_id: int - cursor id for the search query
        vsim_cursor_id: int - cursor id for the vector similarity query
        """
        self.search_cursor_id = search_cursor_id
        self.vsim_cursor_id = vsim_cursor_id
