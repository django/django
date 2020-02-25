Contributing to Channels
========================

As an open source project, Channels welcomes contributions of many forms. By participating in this project, you
agree to abide by the Django `code of conduct <https://www.djangoproject.com/conduct/>`_.

Examples of contributions include:

* Code patches
* Documentation improvements
* Bug reports and patch reviews

For more information, please see our `contribution guide <https://channels.readthedocs.io/en/latest/contributing.html>`_.

Quick Setup
-----------

Fork, then clone the repo:

.. code-block:: sh

    git clone git@github.com:your-username/channels.git

Make sure the tests pass:

.. code-block:: sh

    python -m pip install -e .[tests]
    pytest

Make your change. Add tests for your change. Make the tests pass:

.. code-block:: sh

    pytest

Make sure your code conforms to the coding style:

.. code-block:: sh

    black ./channels ./tests
    isort --check-only --diff --recursive ./channels ./tests

Push to your fork and `submit a pull request <https://github.com/django/channels/compare/>`_.
