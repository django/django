import os
from pathlib import Path
from typing import Iterable, Iterator, List, Set

from isort.settings import Config


def find(
    paths: Iterable[str], config: Config, skipped: List[str], broken: List[str]
) -> Iterator[str]:
    """Fines and provides an iterator for all Python source files defined in paths."""
    visited_dirs: Set[Path] = set()

    for path in paths:
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(
                path, topdown=True, followlinks=config.follow_links
            ):
                base_path = Path(dirpath)
                for dirname in list(dirnames):
                    full_path = base_path / dirname
                    resolved_path = full_path.resolve()
                    if config.is_skipped(full_path):
                        skipped.append(dirname)
                        dirnames.remove(dirname)
                    else:
                        if resolved_path in visited_dirs:  # pragma: no cover
                            dirnames.remove(dirname)
                    visited_dirs.add(resolved_path)

                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if config.is_supported_filetype(filepath):
                        if config.is_skipped(Path(os.path.abspath(filepath))):
                            skipped.append(filename)
                        else:
                            yield filepath
        elif not os.path.exists(path):
            broken.append(path)
        else:
            yield path
