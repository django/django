#!/usr/bin/env python
"""Test the final fix for trim_docstring."""

def trim_docstring_fixed(docstring):
    """
    Uniformly trim leading/trailing whitespace from docstrings.

    Based on https://www.python.org/dev/peps/pep-0257/#handling-docstring-indentation
    """
    if not docstring or not docstring.strip():
        return ''
    # Convert tabs to spaces and split into lines
    lines = docstring.expandtabs().splitlines()
    # Skip the first line when computing indentation (according to PEP 257)
    # If there's only one line or no non-empty lines after the first, use 0 as indent
    non_empty_lines = [line for line in lines[1:] if line.lstrip()]
    if non_empty_lines:
        indent = min(len(line) - len(line.lstrip()) for line in non_empty_lines)
    else:
        indent = 0
    trimmed = [lines[0].lstrip()] + [line[indent:].rstrip() for line in lines[1:]]
    return "\n".join(trimmed).strip()

# Test all cases
test_cases = [
    ("Single line", "test tests something."),
    ("Two lines, second empty", "test tests something.\n"),
    ("Two lines, second whitespace only", "test tests something.\n    "),
    ("Standard Python style", "test tests something.\n\n    This is a longer description.\n    With more content."),
    ("Django style", "\n    test tests something.\n\n    This is a longer description."),
    ("Multiple indents", "test tests something.\n\n        Level 1 indent.\n            Level 2 indent.\n        Back to level 1."),
]

for name, docstring in test_cases:
    print(f"Test: {name}")
    print("=" * 60)
    print("Input:", repr(docstring))
    try:
        result = trim_docstring_fixed(docstring)
        print("Output:", repr(result))
    except Exception as e:
        print(f"ERROR: {e}")
    print()
