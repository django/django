#!/usr/bin/env python
"""Test script to reproduce the trim_docstring issue."""

# Copy the current trim_docstring function
def trim_docstring_old(docstring):
    """
    Uniformly trim leading/trailing whitespace from docstrings.

    Based on https://www.python.org/dev/peps/pep-0257/#handling-docstring-indentation
    """
    if not docstring or not docstring.strip():
        return ''
    # Convert tabs to spaces and split into lines
    lines = docstring.expandtabs().splitlines()
    indent = min(len(line) - len(line.lstrip()) for line in lines if line.lstrip())
    trimmed = [lines[0].lstrip()] + [line[indent:].rstrip() for line in lines[1:]]
    return "\n".join(trimmed).strip()

# Fixed version
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

# Test case 1: Standard Python docstring (content on first line)
docstring1 = '''test tests something.

    This is a longer description.
    With more content.
    '''

print("Test 1: Standard Python docstring (content on first line)")
print("=" * 60)
print("Original docstring:")
print(repr(docstring1))
print()
print("Old trim_docstring output:")
try:
    result_old = trim_docstring_old(docstring1)
    print(repr(result_old))
except ValueError as e:
    print(f"ERROR: {e}")
print()
print("New trim_docstring output:")
result_new = trim_docstring_new(docstring1)
print(repr(result_new))

print()
print()

# Test case 2: Django-style docstring (empty first line)
docstring2 = '''
    test tests something.

    This is a longer description.
    With more content.
    '''

print("Test 2: Django-style docstring (empty first line)")
print("=" * 60)
print("Original docstring:")
print(repr(docstring2))
print()
print("Old trim_docstring output:")
result_old2 = trim_docstring_old(docstring2)
print(repr(result_old2))
print()
print("New trim_docstring output:")
result_new2 = trim_docstring_new(docstring2)
print(repr(result_new2))

print()
print()
print("Both outputs should be identical for test 2:")
print("Match:", result_old2 == result_new2)
