.. _testing:

=========
 Testing
=========

Testing (which includes unit testing, integration testing, and regression testing)
is very important for quality code;
extremely so if the code is a library that will be used in other software.


Test Framework: ``pytest``
==========================

``aiosmtpd`` uses the |pytest|_ testing framework.
Advanced features of pytest are widely used throughout.

.. _`pytest`: https://docs.pytest.org/en/stable/contents.html
.. |pytest| replace:: ``pytest``


Plugins
-------

The one **required** plugin is |pytest-mock|_;
it is used extensively throughout the test suite.

Other plugins that are used, to various degrees, in the ``aiosmtpd`` test suite are:

* |pytest-cov|_ to integrate with |coverage-py|_
* |pytest-sugar|_ to provide better ux
* |pytest-print|_ to give some progress indicator and to assist test troubleshooting
* |pytest-profiling|_ to implement ``*-profile`` testenv,
  although to be honest this is not really useful as the profiling gets 'muddied' by
  pytest runner.

.. _`pytest-mock`: https://pypi.org/project/pytest-mock/
.. |pytest-mock| replace:: ``pytest-mock``
.. _`pytest-cov`: https://pypi.org/project/pytest-cov/
.. |pytest-cov| replace:: ``pytest-cov``
.. _`coverage-py`: https://pypi.org/project/coverage/
.. |coverage-py| replace:: ``coverage-py``
.. _`pytest-sugar`: https://pypi.org/project/pytest-sugar/
.. |pytest-sugar| replace:: ``pytest-sugar``
.. _`pytest-print`: https://pypi.org/project/pytest-print/
.. |pytest-print| replace:: ``pytest-print``
.. _`pytest-profiling`: https://pypi.org/project/pytest-profiling/
.. |pytest-profiling| replace:: ``pytest-profiling``


Fixtures
--------

Below is a list of fixtures defined throught the test suite,
in alphabetical order:

.. autofixture:: aiosmtpd.tests.conftest.client

.. autofixture:: aiosmtpd.tests.conftest.get_controller

    :param class\_: The class of the controller to be instantiated.
        If given, overrides ``class_`` arg of :func:`controller_data`.
        If not specified and no ``class_`` from ``controller_data``,
        defaults to :class:`ExposingController`.
    :return: an instance of :class:`Controller` (or a subclass of)

    In addition to explicitly-specified parameters, ``get_controller`` also
    fetches all ``*args`` and ``**kwargs`` parameters from :func:`controller_data` marker.

.. autofixture:: aiosmtpd.tests.conftest.get_handler

    :param class\_: The class of the handler to be instantiated.
        If given, overrides ``class_`` arg of :func:`handler_data`.
        If not specified and no ``class_`` from ``handler_data``,
        defaults to :class:`Sink`.
    :return: an instance of the handler class.

    In addition to explicitly-specified parameters, ``get_handler`` also
    fetches all ``*args`` and ``**kwargs`` parameters from :func:`handler_data` marker.

.. autofixture:: aiosmtpd.tests.conftest.nodecode_controller

    This is actually identical to using :fixture:`plain_controller`
    with marker ``@controller_data(decode_data=False)``.
    But because this is used in a lot of test cases,
    it's tidier to just make this into a dedicated fixture.

.. autofixture:: aiosmtpd.tests.conftest.plain_controller

.. autofixture:: aiosmtpd.tests.conftest.silence_event_loop_closed

.. autofixture:: aiosmtpd.tests.conftest.ssl_context_client

.. autofixture:: aiosmtpd.tests.conftest.ssl_context_server

.. important::

    As long as you create your test module(s) inside the ``aiosmtpd/tests`` directory,
    you do not need to import the above fixtures;
    they will automatically be available for use as they are defined in the ``conftest.py`` file.

.. note::

    Individual test modules may define their own module-specific fixtures;
    please refer to their respective docstrings for description / usage guide.


Markers
-------

.. decorator:: client_data(...)

    Provides parameters to the :fixture:`~aiosmtpd.tests.conftest.client` fixture.

    :param connect_to: Address to connect to. Defaults to ``Global.SrvAddr``
    :type connect_to: :class:`HostPort`

.. decorator:: controller_data(...)

    Provides parameters to the :fixture:`~aiosmtpd.tests.conftest.get_controller` fixture.

    :param class\_: The class to be instantiated by ``get_controller``.
        Will be overridden if ``get_controller`` is invoked with
        the ``class_`` argument.
    :param host_port: The "host:port" to bound to
    :type host_port: str
    :param \*\*kwargs: Keyworded arguments given to the marker.


.. decorator:: handler_data(...)

    Provides parameters to the :fixture:`~aiosmtpd.tests.conftest.get_handler` fixture.

    :param args\_: A tuple containing values that will be passed as positional arguments
        to the controller constructor
    :param class\_: The class to be instantiated by ``get_controller``
    :param \*args: Positional arguments given to the marker.
        Will override the ``args_`` keyword argument
    :param \*\*kwargs: Keyworded arguments given to the marker.

