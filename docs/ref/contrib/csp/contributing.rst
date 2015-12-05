.. _contributing-chapter:

============
Contributing
============

Patches are more than welcome! You can find the issue tracker `on GitHub
<https://github.com/mozilla/django-csp/issues>`_ and we'd love pull
requests.


Style
=====

Patches should follow PEP8_ and should not introduce any new violations
as detected by the flake8_ tool.


Tests
=====

Patches fixing bugs should include regression tests (ideally tests that
fail without the rest of the patch). Patches adding new features should
test those features thoroughly.

To run the tests, install the requirements from ``requirements.txt``
(probably into a virtualenv_)::

    pip install -r requirements.txt

Then just use the test-running shell script::

    ./run.sh test


.. _PEP8: http://www.python.org/dev/peps/pep-0008/
.. _flake8: https://pypi.python.org/pypi/flake8
.. _virtualenv: http://www.virtualenv.org/
