.. _manpage:

==========
 aiosmtpd
==========

Provides an asynchronous, RFC 5321 compliant Simple Mail Transfer Protocol (SMTP) server that supports customizable
extensions.

:Author: |author|
:Date: |today|
:Copyright: |copyright|
:Version: |version|
:Manual section: 1


SYNOPSIS
========

.. autoprogramm:: aiosmtpd.main:_parser()
   :prog: aiosmtpd
   :notitle:
   :nodesc:
   :options_title: Options
   :options_adornment: ~


ENVIRONMENT
===========

.. envvar:: AIOSMTPD_CONTROLLER_TIMEOUT

    | How long the main thread will wait (in seconds) until the SMTP thread is ready.
    | Default: ``1.0``
