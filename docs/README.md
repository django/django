The documentation in this tree is in plain text files and can be viewed using
any text file viewer.

It uses ReST (reStructuredText) [1], and the Sphinx documentation system [2].
This allows it to be built into other forms for easier viewing and browsing.

To create an HTML version of the docs:

* Install Sphinx (using ``python -m pip install Sphinx`` or some other method).

* In this docs/ directory, type ``make html`` (or ``make.bat html`` on
  Windows) at a shell prompt.

The documentation in _build/html/index.html can then be viewed in a web browser.

[1] http://docutils.sourceforge.net/rst.html
[2] http://sphinx-doc.org/
