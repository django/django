#!/usr/bin/env python
"""Test edge cases for trim_docstring."""

def trim_docstring_new(docstring):
    """
    Uniformly trim leading/trailing whitespace from docstrings.

    Based on https://www.python.org/dev/peps/pep-0257/#handling-docstring-indentation
    """
    if not docstring or not docstring.strip():
        return ''
    # Convert tabs to spaces and split into lines
    lines = docstring.expandtabs().splitlines()
    # Skip the first line when computing indentation
    indent = min(len(line) - len(line.lstrip()) for line in lines[1:] if line.lstrip())
    trimmed = [lines[0].lstrip()] + [line[indent:].rstrip() for line in lines[1:]]
    return "\n".join(trimmed).strip()

# Edge case 1: Single line docstring
print("Test 1: Single line docstring")
print("=" * 60)
docstring1 = "test tests something."
try:
    result1 = trim_docstring_new(docstring1)
    print(f"Success: {repr(result1)}")
except ValueError as e:
    print(f"ERROR: {e}")
    print("This happens because min() receives an empty sequence")

print()

# Edge case 2: Two lines, second line empty
print("Test 2: Two lines, second line empty")
print("=" * 60)
docstring2 = '''test tests something.
'''
try:
    result2 = trim_docstring_new(docstring2)
    print(f"Success: {repr(result2)}")
except ValueError as e:
    print(f"ERROR: {e}")

print()

# Edge case 3: Two lines, second line with only whitespace
print("Test 3: Two lines, second line with only whitespace")
print("=" * 60)
docstring3 = '''test tests something.
    '''
try:
    result3 = trim_docstring_new(docstring3)
    print(f"Success: {repr(result3)}")
except ValueError as e:
    print(f"ERROR: {e}")
