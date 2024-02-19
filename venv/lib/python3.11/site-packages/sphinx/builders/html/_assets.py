from __future__ import annotations

import os
import warnings
import zlib
from typing import TYPE_CHECKING

from sphinx.deprecation import RemovedInSphinx90Warning
from sphinx.errors import ThemeError

if TYPE_CHECKING:
    from pathlib import Path


class _CascadingStyleSheet:
    filename: str | os.PathLike[str]
    priority: int
    attributes: dict[str, str]

    def __init__(
        self,
        filename: str | os.PathLike[str], /, *,
        priority: int = 500,
        rel: str = 'stylesheet',
        type: str = 'text/css',
        **attributes: str,
    ) -> None:
        object.__setattr__(self, 'filename', filename)
        object.__setattr__(self, 'priority', priority)
        object.__setattr__(self, 'attributes', {'rel': rel, 'type': type, **attributes})

    def __str__(self):
        attr = ', '.join(f'{k}={v!r}' for k, v in self.attributes.items())
        return (f'{self.__class__.__name__}({self.filename!r}, '
                f'priority={self.priority}, '
                f'{attr})')

    def __eq__(self, other):
        if isinstance(other, str):
            warnings.warn('The str interface for _CascadingStyleSheet objects is deprecated. '
                          'Use css.filename instead.', RemovedInSphinx90Warning, stacklevel=2)
            return self.filename == other
        if not isinstance(other, _CascadingStyleSheet):
            return NotImplemented
        return (self.filename == other.filename
                and self.priority == other.priority
                and self.attributes == other.attributes)

    def __hash__(self):
        return hash((self.filename, self.priority, *sorted(self.attributes.items())))

    def __setattr__(self, key, value):
        msg = f'{self.__class__.__name__} is immutable'
        raise AttributeError(msg)

    def __delattr__(self, key):
        msg = f'{self.__class__.__name__} is immutable'
        raise AttributeError(msg)

    def __getattr__(self, key):
        warnings.warn('The str interface for _CascadingStyleSheet objects is deprecated. '
                      'Use css.filename instead.', RemovedInSphinx90Warning, stacklevel=2)
        return getattr(os.fspath(self.filename), key)

    def __getitem__(self, key):
        warnings.warn('The str interface for _CascadingStyleSheet objects is deprecated. '
                      'Use css.filename instead.', RemovedInSphinx90Warning, stacklevel=2)
        return os.fspath(self.filename)[key]


class _JavaScript:
    filename: str | os.PathLike[str]
    priority: int
    attributes: dict[str, str]

    def __init__(
        self,
        filename: str | os.PathLike[str], /, *,
        priority: int = 500,
        **attributes: str,
    ) -> None:
        object.__setattr__(self, 'filename', filename)
        object.__setattr__(self, 'priority', priority)
        object.__setattr__(self, 'attributes', attributes)

    def __str__(self):
        attr = ''
        if self.attributes:
            attr = ', ' + ', '.join(f'{k}={v!r}' for k, v in self.attributes.items())
        return (f'{self.__class__.__name__}({self.filename!r}, '
                f'priority={self.priority}'
                f'{attr})')

    def __eq__(self, other):
        if isinstance(other, str):
            warnings.warn('The str interface for _JavaScript objects is deprecated. '
                          'Use js.filename instead.', RemovedInSphinx90Warning, stacklevel=2)
            return self.filename == other
        if not isinstance(other, _JavaScript):
            return NotImplemented
        return (self.filename == other.filename
                and self.priority == other.priority
                and self.attributes == other.attributes)

    def __hash__(self):
        return hash((self.filename, self.priority, *sorted(self.attributes.items())))

    def __setattr__(self, key, value):
        msg = f'{self.__class__.__name__} is immutable'
        raise AttributeError(msg)

    def __delattr__(self, key):
        msg = f'{self.__class__.__name__} is immutable'
        raise AttributeError(msg)

    def __getattr__(self, key):
        warnings.warn('The str interface for _JavaScript objects is deprecated. '
                      'Use js.filename instead.', RemovedInSphinx90Warning, stacklevel=2)
        return getattr(os.fspath(self.filename), key)

    def __getitem__(self, key):
        warnings.warn('The str interface for _JavaScript objects is deprecated. '
                      'Use js.filename instead.', RemovedInSphinx90Warning, stacklevel=2)
        return os.fspath(self.filename)[key]


def _file_checksum(outdir: Path, filename: str | os.PathLike[str]) -> str:
    filename = os.fspath(filename)
    # Don't generate checksums for HTTP URIs
    if '://' in filename:
        return ''
    # Some themes and extensions have used query strings
    # for a similar asset checksum feature.
    # As we cannot safely strip the query string,
    # raise an error to the user.
    if '?' in filename:
        msg = f'Local asset file paths must not contain query strings: {filename!r}'
        raise ThemeError(msg)
    try:
        # Remove all carriage returns to avoid checksum differences
        content = outdir.joinpath(filename).read_bytes().translate(None, b'\r')
    except FileNotFoundError:
        return ''
    if not content:
        return ''
    return f'{zlib.crc32(content):08x}'
