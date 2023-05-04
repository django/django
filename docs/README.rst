The documentation in this tree is in plain text files and can be viewed using
any text file viewer.

It uses `ReST`_ (reStructuredText), and the `Sphinx`_ documentation system.
This allows it to be built into other forms for easier viewing and browsing.

To create an HTML version of the docs:

* From the project root directory, run
  ``python -m pip install -r docs/requirements.txt``. [1]_

* Then type ``make html`` (or ``make.bat html`` on Windows) at a shell prompt.

The documentation in ``_build/html/index.html`` can then be viewed in a web
browser.

.. _ReST: https://docutils.sourceforge.io/rst.html
.. _Sphinx: https://www.sphinx-doc.org/

.. [1] This command must be run (from the project root) because, due to
   Sphinx's viewcode extension, the docs are dependent on Django itself.
   ``docs/requirements.txt`` installs Django from the directory in which the
   command is run.
