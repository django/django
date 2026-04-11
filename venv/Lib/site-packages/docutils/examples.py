# $Id: examples.py 10045 2025-03-09 01:02:23Z aa-turner $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
This module contains practical examples of Docutils client code.

Importing this module from client code is not recommended; its contents are
subject to change in future Docutils releases.  Instead, it is recommended
that you copy and paste the parts you need into your own code, modifying as
necessary.
"""

from __future__ import annotations


from docutils import core, io

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any, Literal

    from docutils import nodes
    from docutils.nodes import StrPath
    from docutils.core import Publisher


def html_parts(input_string: str | bytes,
               source_path: StrPath | None = None,
               destination_path: StrPath | None = None,
               input_encoding: Literal['unicode'] | str = 'unicode',
               doctitle: bool = True,
               initial_header_level: int = 1,
               ) -> dict[str, str]:
    """
    Given an input string, returns a dictionary of HTML document parts.

    Dictionary keys are the names of parts, and values are Unicode strings;
    encoding is up to the client.

    Parameters:

    - `input_string`: A multi-line text string; required.
    - `source_path`: Path to the source file or object.  Optional, but useful
      for diagnostic output (system messages).
    - `destination_path`: Path to the file or object which will receive the
      output; optional.  Used for determining relative paths (stylesheets,
      source links, etc.).
    - `input_encoding`: The encoding of `input_string`.  If it is an encoded
      8-bit string, provide the correct encoding.  If it is a Unicode string,
      use "unicode", the default.
    - `doctitle`: Disable the promotion of a lone top-level section title to
      document title (and subsequent section title to document subtitle
      promotion); enabled by default.
    - `initial_header_level`: The initial level for header elements (e.g. 1
      for "<h1>").
    """
    overrides = {'input_encoding': input_encoding,
                 'doctitle_xform': doctitle,
                 'initial_header_level': initial_header_level}
    parts = core.publish_parts(
        source=input_string, source_path=source_path,
        destination_path=destination_path,
        writer='html', settings_overrides=overrides)
    return parts


def html_body(input_string: str | bytes,
              source_path: StrPath | None = None,
              destination_path: StrPath | None = None,
              input_encoding: Literal['unicode'] | str = 'unicode',
              output_encoding: Literal['unicode'] | str = 'unicode',
              doctitle: bool = True,
              initial_header_level: int = 1,
              ) -> str | bytes:
    """
    Given an input string, returns an HTML fragment as a string.

    The return value is the contents of the <body> element.

    Parameters (see `html_parts()` for the remainder):

    - `output_encoding`: The desired encoding of the output.  If a Unicode
      string is desired, use the default value of "unicode" .
    """
    parts = html_parts(
        input_string=input_string, source_path=source_path,
        destination_path=destination_path,
        input_encoding=input_encoding, doctitle=doctitle,
        initial_header_level=initial_header_level)
    fragment = parts['html_body']
    if output_encoding != 'unicode':
        fragment = fragment.encode(output_encoding)
    return fragment


def internals(source: str,
              source_path: StrPath | None = None,
              input_encoding: Literal['unicode'] | str = 'unicode',
              settings_overrides: dict[str, Any] | None = None,
              ) -> tuple[nodes.document, Publisher]:
    """
    Return the document tree and publisher, for exploring Docutils internals.

    Parameters: see `html_parts()`.
    """
    if settings_overrides is None:
        settings_overrides = {}
    overrides = settings_overrides | {'input_encoding': input_encoding}

    publisher = core.Publisher('standalone', 'rst', 'null',
                               source_class=io.StringInput,
                               destination_class=io.NullOutput)
    publisher.process_programmatic_settings(settings_spec=None,
                                            settings_overrides=overrides,
                                            config_section=None)
    publisher.set_source(source, source_path)
    publisher.publish()
    return publisher.document, publisher


if __name__ == '__main__':
    print(internals('test')[0])
