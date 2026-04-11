Metadata-Version: 2.4
Name: pycparser
Version: 3.0
Summary: C parser in Python
Author-email: Eli Bendersky <eliben@gmail.com>
Maintainer-email: Eli Bendersky <eliben@gmail.com>
License-Expression: BSD-3-Clause
Project-URL: Homepage, https://github.com/eliben/pycparser
Classifier: Development Status :: 5 - Production/Stable
Classifier: Programming Language :: Python :: 3
Classifier: Programming Language :: Python :: 3.10
Classifier: Programming Language :: Python :: 3.11
Classifier: Programming Language :: Python :: 3.12
Classifier: Programming Language :: Python :: 3.13
Classifier: Programming Language :: Python :: 3.14
Requires-Python: >=3.10
Description-Content-Type: text/x-rst
License-File: LICENSE
Dynamic: license-file

===============
pycparser v3.00
===============


.. image:: https://github.com/eliben/pycparser/workflows/pycparser-tests/badge.svg
  :align: center
  :target: https://github.com/eliben/pycparser/actions

----

.. contents::
    :backlinks: none

.. sectnum::

Introduction
============

What is pycparser?
------------------

**pycparser** is a parser for the C language, written in pure Python. It is a
module designed to be easily integrated into applications that need to parse
C source code.

What is it good for?
--------------------

Anything that needs C code to be parsed. The following are some uses for
**pycparser**, taken from real user reports:

* C code obfuscator
* Front-end for various specialized C compilers
* Static code checker
* Automatic unit-test discovery
* Adding specialized extensions to the C language

One of the most popular uses of **pycparser** is in the `cffi
<https://cffi.readthedocs.io/en/latest/>`_ library, which uses it to parse the
declarations of C functions and types in order to auto-generate FFIs.

**pycparser** is unique in the sense that it's written in pure Python - a very
high level language that's easy to experiment with and tweak. To people familiar
with Lex and Yacc, **pycparser**'s code will be simple to understand. It also
has no external dependencies (except for a Python interpreter), making it very
simple to install and deploy.

Which version of C does pycparser support?
------------------------------------------

**pycparser** aims to support the full C99 language (according to the standard
ISO/IEC 9899). Some features from C11 are also supported, and patches to support
more are welcome.

**pycparser** supports very few GCC extensions, but it's fairly easy to set
things up so that it parses code with a lot of GCC-isms successfully. See the
`FAQ <https://github.com/eliben/pycparser/wiki/FAQ>`_ for more details.

What grammar does pycparser follow?
-----------------------------------

**pycparser** very closely follows the C grammar provided in Annex A of the C99
standard (ISO/IEC 9899).

How is pycparser licensed?
--------------------------

`BSD license <https://github.com/eliben/pycparser/blob/master/LICENSE>`_.

Contact details
---------------

For reporting problems with **pycparser** or submitting feature requests, please
open an `issue <https://github.com/eliben/pycparser/issues>`_, or submit a
pull request.


Installing
==========

Prerequisites
-------------

**pycparser** is being tested with modern versions of Python on
Linux, macOS and Windows. See `the CI dashboard <https://github.com/eliben/pycparser/actions/workflows/ci.yml>`__
for details.

**pycparser** has no external dependencies.

Installation process
--------------------

The recommended way to install **pycparser** is with ``pip``::

    > pip install pycparser

Using
=====

Interaction with the C preprocessor
-----------------------------------

In order to be compilable, C code must be preprocessed by the C preprocessor -
``cpp``. A compatible ``cpp`` handles preprocessing directives like ``#include`` and
``#define``, removes comments, and performs other minor tasks that prepare the C
code for compilation.

For all but the most trivial snippets of C code **pycparser**, like a C
compiler, must receive preprocessed C code in order to function correctly. If
you import the top-level ``parse_file`` function from the **pycparser** package,
it will interact with ``cpp`` for you, as long as it's in your PATH, or you
provide a path to it.

Note also that you can use ``gcc -E`` or ``clang -E`` instead of ``cpp``. See
the ``using_gcc_E_libc.py`` example for more details. Windows users can download
and install a binary build of Clang for Windows `from this website
<http://llvm.org/releases/download.html>`_.

What about the standard C library headers?
------------------------------------------

C code almost always ``#include``\s various header files from the standard C
library, like ``stdio.h``. While (with some effort) **pycparser** can be made to
parse the standard headers from any C compiler, it's much simpler to use the
provided "fake" standard includes for C11 in ``utils/fake_libc_include``. These
are standard C header files that contain only the bare necessities to allow
valid parsing of the files that use them. As a bonus, since they're minimal, it
can significantly improve the performance of parsing large C files.

The key point to understand here is that **pycparser** doesn't really care about
the semantics of types. It only needs to know whether some token encountered in
the source is a previously defined type. This is essential in order to be able
to parse C correctly.

See `this blog post
<https://eli.thegreenplace.net/2015/on-parsing-c-type-declarations-and-fake-headers>`_
for more details.

Note that the fake headers are not included in the ``pip`` package nor installed
via the package build (`#224 <https://github.com/eliben/pycparser/issues/224>`_).

Basic usage
-----------

Take a look at the |examples|_ directory of the distribution for a few examples
of using **pycparser**. These should be enough to get you started. Please note
that most realistic C code samples would require running the C preprocessor
before passing the code to **pycparser**; see the previous sections for more
details.

.. |examples| replace:: ``examples``
.. _examples: examples


Advanced usage
--------------

The public interface of **pycparser** is well documented with comments in
``pycparser/c_parser.py``. For a detailed overview of the various AST nodes
created by the parser, see ``pycparser/_c_ast.cfg``.

There's also a `FAQ available here <https://github.com/eliben/pycparser/wiki/FAQ>`_.
In any case, you can always drop me an `email <eliben@gmail.com>`_ for help.


Modifying
=========

There are a few points to keep in mind when modifying **pycparser**:

* The code for **pycparser**'s AST nodes is automatically generated from a
  configuration file - ``_c_ast.cfg``, by ``_ast_gen.py``. If you modify the AST
  configuration, make sure to re-generate the code. This can be done by running
  the ``_ast_gen.py`` script (from the repository root or the
  ``pycparser`` directory).
* Read the docstring in the constructor of the ``CParser`` class for details
  on configuration and compatibility arguments.


Package contents
================

Once you unzip the ``pycparser`` package, you'll see the following files and
directories:

README.rst:
  This README file.

LICENSE:
  The pycparser license

setup.py:
  Legacy installation script (build metadata lives in ``pyproject.toml``).

pyproject.toml:
  Package metadata and build configuration.

examples/:
  A directory with some examples of using **pycparser**

pycparser/:
  The **pycparser** module source code.

tests/:
  Unit tests.

utils/fake_libc_include:
  Minimal standard C library include files that should allow to parse any C code.
  Note that these headers now include C11 code, so they may not work when the
  preprocessor is configured to an earlier C standard (like ``-std=c99``).

utils/internal/:
  Internal utilities for my own use. You probably don't need them.


Contributors
============

Some people have contributed to **pycparser** by opening issues on bugs they've
found and/or submitting patches. The list of contributors is in the CONTRIBUTORS
file in the source distribution. After **pycparser** moved to Github I stopped
updating this list because Github does a much better job at tracking
contributions.
