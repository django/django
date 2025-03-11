import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class TrieNode:
    def __init__(self, config_file: str = "", config_data: Optional[Dict[str, Any]] = None) -> None:
        if not config_data:
            config_data = {}

        self.nodes: Dict[str, TrieNode] = {}
        self.config_info: Tuple[str, Dict[str, Any]] = (config_file, config_data)


class Trie:
    """
    A prefix tree to store the paths of all config files and to search the nearest config
    associated with each file
    """

    def __init__(self, config_file: str = "", config_data: Optional[Dict[str, Any]] = None) -> None:
        self.root: TrieNode = TrieNode(config_file, config_data)

    def insert(self, config_file: str, config_data: Dict[str, Any]) -> None:
        resolved_config_path_as_tuple = Path(config_file).parent.resolve().parts

        temp = self.root

        for path in resolved_config_path_as_tuple:
            if path not in temp.nodes:
                temp.nodes[path] = TrieNode()

            temp = temp.nodes[path]

        temp.config_info = (config_file, config_data)

    def search(self, filename: str) -> Tuple[str, Dict[str, Any]]:
        """
        Returns the closest config relative to filename by doing a depth
        first search on the prefix tree.
        """
        resolved_file_path_as_tuple = Path(filename).resolve().parts

        temp = self.root

        last_stored_config: Tuple[str, Dict[str, Any]] = ("", {})

        for path in resolved_file_path_as_tuple:
            if temp.config_info[0]:
                last_stored_config = temp.config_info

            if path not in temp.nodes:
                break

            temp = temp.nodes[path]

        return last_stored_config


@lru_cache(maxsize=1000)
def exists_case_sensitive(path: str) -> bool:
    """Returns if the given path exists and also matches the case on Windows.

    When finding files that can be imported, it is important for the cases to match because while
    file os.path.exists("module.py") and os.path.exists("MODULE.py") both return True on Windows,
    Python can only import using the case of the real file.
    """
    result = os.path.exists(path)
    if result and (sys.platform.startswith("win") or sys.platform == "darwin"):  # pragma: no cover
        directory, basename = os.path.split(path)
        result = basename in os.listdir(directory)
    return result
