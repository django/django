==============
 Introduction
==============

This library provides an :mod:`asyncio`-based implementation of a server for
:rfc:`5321` -
Simple Mail Transfer Protocol (SMTP) and
:rfc:`2033` -
Local Mail Transfer Protocol (LMTP).  It is derived from
`Python 3.5's smtpd.py <https://hg.python.org/cpython/file/3.5/Lib/smtpd.py>`__
standard library module, and provides both a command line interface and an API
for use in testing applications that send email.

Inspiration for this library comes from several other packages:

* `lazr.smtptest <http://bazaar.launchpad.net/~lazr-developers/lazr.smtptest/devel/files>`__
* `benjamin-bader/aiosmtp <https://github.com/benjamin-bader/aiosmtp>`__
* `Mailman 3's LMTP server <https://gitlab.com/mailman/mailman/blob/master/src/mailman/runners/lmtp.py#L138>`__

``aiosmtpd`` takes the best of these and consolidates them in one place.


Relevant RFCs
=============

* :rfc:`5321` - Simple Mail Transfer Protocol (SMTP)
* :rfc:`2033` - Local Mail Transfer Protocol (LMTP)
* :rfc:`2034` - SMTP Service Extension for Returning Enhanced Error Codes
* :rfc:`6531` - SMTP Extension for Internationalized Email
* :rfc:`4954` - SMTP Service Extension for Authentication
* :rfc:`5322` - Internet Message Format
* :rfc:`3696` - Application Techniques for Checking and Transformation of Names
* :rfc:`2034` - SMTP Service Extension for Returning Enhanced Error Codes
* :rfc:`1870` - SMTP Service Extension for Message Size Declaration

Other references
================

* `Wikipedia page on SMTP <https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol>`__
* `asyncio module documentation <https://docs.python.org/3/library/asyncio.html>`__
* `Developing with asyncio <https://docs.python.org/3/library/asyncio-dev.html#asyncio-dev>`__
* `Python issue #25008 <http://bugs.python.org/issue25008>`__ which started
  the whole thing.
