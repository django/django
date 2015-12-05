.. _configuration-chapter:

===============
Configuring csp
===============

Content-Security-Policy_ is a complicated header. There are many values
you may need to tweak here.

.. note::
   Note when a setting requires a tuple or list. Since Python strings
   are iterable, you may get very strange policies and errors.

It's worth reading the latest CSP spec and making sure you understand it
before configuring csp.


Policy Settings
===============

These settings affect the policy in the header. The defaults are in
*italics*.

.. note::
   The "special" source values of ``'self'``, ``'unsafe-inline'``,
   ``'unsafe-eval'``, and ``'none'`` must be quoted! e.g.:
   ``CSP_DEFAULT_SRC = ("'self'",)``. Without quotes they will not work
   as intended.

``CSP_DEFAULT_SRC``
    Set the ``default-src`` directive. A tuple or list of
    values, e.g. ``("'self'", 'cdn.example.net')``. *'self'*
``CSP_SCRIPT_SRC``
    Set the ``script-src`` directive. A tuple or list. *None*
``CSP_IMG_SRC``
    Set the ``img-src`` directive. A tuple or list. *None*
``CSP_OBJECT_SRC``
    Set the ``object-src`` directive. A tuple or list. *None*
``CSP_MEDIA_SRC``
    Set the ``media-src`` directive. A tuple or list. *None*
``CSP_FRAME_SRC``
    Set the ``frame-src`` directive. A tuple or list. *None*
``CSP_FONT_SRC``
    Set the ``font-src`` directive. A tuple or list. *None*
``CSP_CONNECT_SRC``
    Set the ``connect-src`` directive. A tuple or list. *None*
``CSP_STYLE_SRC``
    Set the ``style-src`` directive. A tuple or list. *None*
``CSP_SANDBOX``
    Set the ``sandbox`` directive. A tuple or list. *None*
``CSP_REPORT_URI``
    Set the ``report-uri`` directive. A **string** with a full or
    relative URI.


Changing the Policy
-------------------

The policy can be changed on a per-view (or even per-request) basis. See
the :ref:`decorator documentation <decorator-chapter>` for more details.


Other Settings
==============

These settings control the behavior of csp. Defaults are in *italics*.

``CSP_REPORT_ONLY``
    Send "report-only" headers instead of real headers. See the spec_
    and the chapter on :ref:`reports <reports-chapter>` for more info. A
    boolean. *False*
``CSP_EXCLUDE_URL_PREFIXES``
    A **tuple** of URL prefixes. URLs beginning with any of these will
    not get the CSP headers. *('/admin',)*

.. warning::

   Excluding any path on your site will eliminate the benefits of CSP
   everywhere on your site. The typical browser security model for
   JavaScript considers all paths alike. A Cross-Site Scripting flaw
   on, e.g., `admin/` can therefore be leveraged to access everything
   on the same origin.

.. _Content-Security-Policy: http://www.w3.org/TR/CSP/
.. _spec: Content-Security-Policy_
