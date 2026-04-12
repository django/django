"""Defines any IO utilities used by isort"""

import dataclasses
import re
import tokenize
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from io import BytesIO, StringIO, TextIOWrapper
from pathlib import Path
from typing import Any, TextIO

from isort.exceptions import UnsupportedEncoding

_ENCODING_PATTERN = re.compile(rb"^[ \t\f]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)")


@dataclasses.dataclass(frozen=True)
class File:
    stream: TextIO
    path: Path
    encoding: str

    @staticmethod
    def detect_encoding(filename: str | Path, readline: Callable[[], bytes]) -> str:
        try:
            return tokenize.detect_encoding(readline)[0]
        except Exception:
            raise UnsupportedEncoding(filename)

    @staticmethod
    def from_contents(contents: str, filename: str) -> "File":
        encoding = File.detect_encoding(filename, BytesIO(contents.encode("utf-8")).readline)
        return File(stream=StringIO(contents), path=Path(filename).resolve(), encoding=encoding)

    @property
    def extension(self) -> str:
        return self.path.suffix.lstrip(".")

    @staticmethod
    def _open(filename: str | Path) -> TextIOWrapper:
        """Open a file in read only mode using the encoding detected by
        detect_encoding().
        """
        buffer = open(filename, "rb")
        try:
            encoding = File.detect_encoding(filename, buffer.readline)
            buffer.seek(0)
            text = TextIOWrapper(buffer, encoding, line_buffering=True, newline="")
            text.mode = "r"  # type: ignore
            return text
        except Exception:
            buffer.close()
            raise

    @staticmethod
    @contextmanager
    def read(filename: str | Path) -> Iterator["File"]:
        file_path = Path(filename).resolve()
        stream = None
        try:
            stream = File._open(file_path)
            yield File(stream=stream, path=file_path, encoding=stream.encoding)
        finally:
            if stream is not None:
                stream.close()


class _EmptyIO(StringIO):
    def write(self, *args: Any, **kwargs: Any) -> None:  # type: ignore # skipcq: PTC-W0049
        pass


Empty = _EmptyIO()
