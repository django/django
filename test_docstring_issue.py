#!/usr/bin/env python
"""Test script to reproduce the docstring issue."""

import sys
sys.path.insert(0, '/app/.stitch-workspace/django')

from django.contrib.admindocs.utils import trim_docstring, parse_rst

# Test case 1: Docstring with content on first line (like standard Python docstrings)
def test_function_standard():
    """test tests something.

    This is a longer description.
    """
    pass

# Test case 2: Django-style docstring with empty first line
def test_function_django():
    """
    test tests something.

    This is a longer description.
    """
    pass

print("Test 1: Standard Python docstring (content on first line)")
print("=" * 60)
docstring1 = test_function_standard.__doc__
print("Original docstring:")
print(repr(docstring1))
print()
try:
    trimmed1 = trim_docstring(docstring1)
    print("Trimmed docstring:")
    print(repr(trimmed1))
    print()

    # Try to parse it with parse_rst
    try:
        result = parse_rst(trimmed1, 'view')
        print("parse_rst succeeded!")
        print(result)
    except Exception as e:
        print(f"parse_rst failed with error: {e}")
except Exception as e:
    print(f"trim_docstring failed with error: {e}")

print()
print("Test 2: Django-style docstring (empty first line)")
print("=" * 60)
docstring2 = test_function_django.__doc__
print("Original docstring:")
print(repr(docstring2))
print()
try:
    trimmed2 = trim_docstring(docstring2)
    print("Trimmed docstring:")
    print(repr(trimmed2))
    print()

    # Try to parse it with parse_rst
    try:
        result = parse_rst(trimmed2, 'view')
        print("parse_rst succeeded!")
        print(result[:200])
    except Exception as e:
        print(f"parse_rst failed with error: {e}")
except Exception as e:
    print(f"trim_docstring failed with error: {e}")
