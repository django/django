The documentation in this tree is in plain text files and can be viewed using
any text file viewer.

It uses `ReST`_ (reStructuredText), and the `Sphinx`_ documentation system.
This allows it to be built into other forms for easier viewing and browsing.

To create an HTML version of the docs:

* Install Sphinx (using ``python -m pip install Sphinx`` or some other method).
* WARNING: When you install Sphinx a message could appear showing:  The scripts 
  sphinx-apidoc.exe, sphinx-autogen.exe, sphinx-build.exe and 
  sphinx-quickstart.exe are installed in ``'C:\Users\...\Scripts'`` which is not 
  on PATH. You should open the folder ``Scripts`` and move all the data to the 
  docs/ directory before continuing.
* In this docs/ directory, type ``make html`` (or ``make.bat html`` on
  Windows) at a shell prompt.

The documentation in ``_build/html/index.html`` can then be viewed in a web
browser.

.. _ReST: https://docutils.sourceforge.io/rst.html
.. _Sphinx: https://www.sphinx-doc.org/
