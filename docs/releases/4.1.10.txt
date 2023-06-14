===========================
Django 4.1.10 release notes
===========================

*July 3, 2023*

Django 4.1.10 fixes a security issue with severity "moderate" in 4.1.9.

CVE-2023-36053: Potential regular expression denial of service vulnerability in ``EmailValidator``/``URLValidator``
===================================================================================================================

``EmailValidator`` and ``URLValidator`` were subject to potential regular
expression denial of service attack via a very large number of domain name
labels of emails and URLs.
