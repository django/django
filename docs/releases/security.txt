.. _security-releases:

==========================
Archive of security issues
==========================

Django's development team is strongly committed to responsible
reporting and disclosure of security-related issues, as outlined in
:doc:`Django's security policies </internals/security>`.

As part of that commitment, we maintain the following historical list
of issues which have been fixed and disclosed. For each issue, the
list below includes the date, a brief description, the `CVE identifier
<http://en.wikipedia.org/wiki/Common_Vulnerabilities_and_Exposures>`_
if applicable, a list of affected versions, a link to the full
disclosure and links to the appropriate patch(es).

Some important caveats apply to this information:

* Lists of affected versions include only those versions of Django
  which had stable, security-supported releases at the time of
  disclosure. This means older versions (whose security support had
  expired) and versions which were in pre-release (alpha/beta/RC)
  states at the time of disclosure may have been affected, but are not
  listed.

* The Django project has on occasion issued security advisories,
  pointing out potential security problems which can arise from
  improper configuration or from other issues outside of Django
  itself. Some of these advisories have received CVEs; when that is
  the case, they are listed here, but as they have no accompanying
  patches or releases, only the description, disclosure and CVE will
  be listed.


Issues prior to Django's security process
=========================================

Some security issues were handled before Django had a formalized
security process in use. For these, new releases may not have been
issued at the time and CVEs may not have been assigned.


August 16, 2006 - CVE-2007-0404
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2007-0404 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2007-0404&cid=3>`_: Filename validation issue in translation framework. `Full description <https://www.djangoproject.com/weblog/2006/aug/16/compilemessages/>`__

Versions affected
-----------------

* Django 0.90 `(patch) <https://github.com/django/django/commit/518d406e53>`__

* Django 0.91 `(patch) <https://github.com/django/django/commit/518d406e53>`__

* Django 0.95 `(patch) <https://github.com/django/django/commit/a132d411c6>`__ (released January 21 2007)

January 21, 2007 - CVE-2007-0405
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2007-0405 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2007-0405&cid=3>`_: Apparent "caching" of authenticated user. `Full description <https://www.djangoproject.com/weblog/2007/jan/21/0951/>`__

Versions affected
-----------------

* Django 0.95 `(patch) <https://github.com/django/django/commit/e89f0a6558>`__

Issues under Django's security process
======================================

All other security issues have been handled under versions of Django's
security process. These are listed below.

October 26, 2007 - CVE-2007-5712
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2007-5712 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2007-5712&cid=3>`_: Denial-of-service via arbitrarily-large ``Accept-Language`` header. `Full description <https://www.djangoproject.com/weblog/2007/oct/26/security-fix/>`__

Versions affected
-----------------

* Django 0.91 `(patch) <https://github.com/django/django/commit/8bc36e726c9e8c75c681d3ad232df8e882aaac81>`__

* Django 0.95 `(patch) <https://github.com/django/django/commit/412ed22502e11c50dbfee854627594f0e7e2c234>`__

* Django 0.96 `(patch) <https://github.com/django/django/commit/7dd2dd08a79e388732ce00e2b5514f15bd6d0f6f>`__


May 14, 2008 - CVE-2008-2302
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2008-2302 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2008-2302&cid=3>`_: XSS via admin login redirect. `Full description <https://www.djangoproject.com/weblog/2008/may/14/security/>`__

Versions affected
-----------------

* Django 0.91 `(patch) <https://github.com/django/django/commit/50ce7fb57d>`__

* Django 0.95 `(patch) <https://github.com/django/django/commit/50ce7fb57d>`__

* Django 0.96 `(patch) <https://github.com/django/django/commit/7791e5c050>`__


September 2, 2008 - CVE-2008-3909
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2008-3909 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2008-3909&cid=3>`_: CSRF via preservation of POST data during admin login. `Full description <https://www.djangoproject.com/weblog/2008/sep/02/security/>`__

Versions affected
-----------------

* Django 0.91 `(patch) <https://github.com/django/django/commit/44debfeaa4473bd28872c735dd3d9afde6886752>`__

* Django 0.95 `(patch) <https://github.com/django/django/commit/aee48854a164382c655acb9f18b3c06c3d238e81>`__

* Django 0.96 `(patch) <https://github.com/django/django/commit/7e0972bded362bc4b851c109df2c8a6548481a8e>`__

July 28, 2009 - CVE-2009-2659
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2009-2659 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2009-2659&cid=3>`_: Directory-traversal in development server media handler. `Full description <https://www.djangoproject.com/weblog/2009/jul/28/security/>`__

Versions affected
-----------------

* Django 0.96 `(patch) <https://github.com/django/django/commit/da85d76fd6>`__

* Django 1.0 `(patch) <https://github.com/django/django/commit/df7f917b7f>`__

October 9, 2009 - CVE-2009-3965
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2009-3965 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2009-3695&cid=3>`_: Denial-of-service via pathological regular expression performance. `Full description <https://www.djangoproject.com/weblog/2009/oct/09/security/>`__

Versions affected
-----------------

* Django 1.0 `(patch) <https://github.com/django/django/commit/594a28a904>`__

* Django 1.1 `(patch) <https://github.com/django/django/commit/e3e992e18b>`__

September 8, 2010 - CVE-2010-3082
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2010-3082 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2010-3082&cid=3>`_: XSS via trusting unsafe cookie value. `Full description <https://www.djangoproject.com/weblog/2010/sep/08/security-release/>`__

Versions affected
-----------------

* Django 1.2 `(patch) <https://github.com/django/django/commit/7f84657b6b>`__


December 22, 2010 - CVE-2010-4534
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2010-4534 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2010-4534&cid=3>`_: Information leakage in administrative interface. `Full description <https://www.djangoproject.com/weblog/2010/dec/22/security/>`__

Versions affected
-----------------

* Django 1.1 `(patch) <https://github.com/django/django/commit/17084839fd>`__

* Django 1.2 `(patch) <https://github.com/django/django/commit/85207a245b>`__

December 22, 2010 - CVE-2010-4535
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2010-4535 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2010-4535&cid=2>`_: Denial-of-service in password-reset mechanism. `Full description <https://www.djangoproject.com/weblog/2010/dec/22/security/>`__

Versions affected
-----------------

* Django 1.1 `(patch) <https://github.com/django/django/commit/7f8dd9cbac>`__

* Django 1.2 `(patch) <https://github.com/django/django/commit/d5d8942a16>`__


February 8, 2011 - CVE-2011-0696
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2011-0696 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2011-0696&cid=2>`_: CSRF via forged HTTP headers. `Full description <https://www.djangoproject.com/weblog/2011/feb/08/security/>`__

Versions affected
-----------------

* Django 1.1 `(patch) <https://github.com/django/django/commit/408c5c873c>`__

* Django 1.2 `(patch) <https://github.com/django/django/commit/818e70344e>`__


February 8, 2011 - CVE-2011-0697
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2011-0697 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2011-0697&cid=2>`_: XSS via unsanitized names of uploaded files. `Full description <https://www.djangoproject.com/weblog/2011/feb/08/security/>`__

Versions affected
-----------------

* Django 1.1 `(patch) <https://github.com/django/django/commit/1966786d2d>`__

* Django 1.2 `(patch) <https://github.com/django/django/commit/1f814a9547>`__

February 8, 2011 - CVE-2011-0698
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2011-0698 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2011-0698&cid=2>`_: Directory-traversal on Windows via incorrect path-separator handling. `Full description <https://www.djangoproject.com/weblog/2011/feb/08/security/>`__

Versions affected
-----------------

* Django 1.1 `(patch) <https://github.com/django/django/commit/570a32a047>`__

* Django 1.2 `(patch) <https://github.com/django/django/commit/194566480b>`__


September 9, 2011 - CVE-2011-4136
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2011-4136 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2011-4136&cid=2>`_: Session manipulation when using memory-cache-backed session. `Full description <https://www.djangoproject.com/weblog/2011/sep/09/security-releases-issued/>`__

Versions affected
-----------------

* Django 1.2 `(patch) <https://github.com/django/django/commit/ac7c3a110f>`__

* Django 1.3 `(patch) <https://github.com/django/django/commit/fbe2eead2f>`__

September 9, 2011 - CVE-2011-4137
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2011-4137 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2011-4137&cid=2>`_: Denial-of-service via via ``URLField.verify_exists``. `Full description <https://www.djangoproject.com/weblog/2011/sep/09/security-releases-issued/>`__

Versions affected
-----------------

* Django 1.2 `(patch) <https://github.com/django/django/commit/7268f8af86>`__

* Django 1.3 `(patch) <https://github.com/django/django/commit/1a76dbefdf>`__

September 9, 2011 - CVE-2011-4138
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2011-4138 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2011-4138&cid=2>`_: Information leakage/arbitrary request issuance via ``URLField.verify_exists``. `Full description <https://www.djangoproject.com/weblog/2011/sep/09/security-releases-issued/>`__

Versions affected
-----------------

* Django 1.2: `(patch) <https://github.com/django/django/commit/7268f8af86>`__

* Django 1.3: `(patch) <https://github.com/django/django/commit/1a76dbefdf>`__

September 9, 2011 - CVE-2011-4139
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2011-4139 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2011-4139&cid=2>`_: ``Host`` header cache poisoning. `Full description <https://www.djangoproject.com/weblog/2011/sep/09/security-releases-issued/>`__

Versions affected
-----------------

* Django 1.2 `(patch) <https://github.com/django/django/commit/c613af4d64>`__

* Django 1.3 `(patch) <https://github.com/django/django/commit/2f7fadc38e>`__

September 9, 2011 - CVE-2011-4140
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2011-4140 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2011-4140&cid=2>`_: Potential CSRF via ``Host`` header.  `Full description <https://www.djangoproject.com/weblog/2011/sep/09/security-releases-issued/>`__

Versions affected
-----------------

This notification was an advisory only, so no patches were issued.

* Django 1.2

* Django 1.3


July 30, 2012 - CVE-2012-3442
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2012-3442 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2012-3442&cid=2>`_: XSS via failure to validate redirect scheme. `Full description <https://www.djangoproject.com/weblog/2012/jul/30/security-releases-issued/>`__

Versions affected
-----------------

* Django 1.3: `(patch) <https://github.com/django/django/commit/4dea4883e6c50d75f215a6b9bcbd95273f57c72d>`__

* Django 1.4: `(patch) <https://github.com/django/django/commit/e34685034b60be1112160e76091e5aee60149fa1>`__


July 30, 2012 - CVE-2012-3443
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2012-3443 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2012-3443&cid=2>`_: Denial-of-service via compressed image files. `Full description <https://www.djangoproject.com/weblog/2012/jul/30/security-releases-issued/>`__

Versions affected
-----------------

* Django 1.3: `(patch) <https://github.com/django/django/commit/b2eb4787a0fff9c9993b78be5c698e85108f3446>`__

* Django 1.4: `(patch) <https://github.com/django/django/commit/c14f325c4eef628bc7bfd8873c3a72aeb0219141>`__


July 30, 2012 - CVE-2012-3444
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2012-3444 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2012-3444&cid=2>`_: Denial-of-service via large image files. `Full description <https://www.djangoproject.com/weblog/2012/jul/30/security-releases-issued/>`__

Versions affected
-----------------

* Django 1.3 `(patch) <https://github.com/django/django/commit/9ca0ff6268eeff92d0d0ac2c315d4b6a8e229155>`__

* Django 1.4 `(patch) <https://github.com/django/django/commit/da33d67181b53fe6cc737ac1220153814a1509f6>`__


October 17, 2012 - CVE-2012-4520
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2012-4520 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2012-4520&cid=2>`_: ``Host`` header poisoning. `Full description <https://www.djangoproject.com/weblog/2012/oct/17/security/>`__

Versions affected
-----------------

* Django 1.3 `(patch) <https://github.com/django/django/commit/b45c377f8f488955e0c7069cad3f3dd21910b071>`__

* Django 1.4 `(patch) <https://github.com/django/django/commit/92d3430f12171f16f566c9050c40feefb830a4a3>`__


December 10, 2012 - No CVE 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Additional hardening of ``Host`` header handling. `Full description <https://www.djangoproject.com/weblog/2012/dec/10/security/>`__

Versions affected
-----------------

* Django 1.3 `(patch) <https://github.com/django/django/commit/2da4ace0bc1bc1d79bf43b368cb857f6f0cd6b1b>`__

* Django 1.4 `(patch) <https://github.com/django/django/commit/319627c184e71ae267d6b7f000e293168c7b6e09>`__


December 10, 2012 - No CVE 2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Additional hardening of redirect validation. `Full description <https://www.djangoproject.com/weblog/2012/dec/10/security/>`__

Versions affected
-----------------

    * Django 1.3: `(patch) <https://github.com/django/django/commit/1515eb46daa0897ba5ad5f0a2db8969255f1b343>`__

    * Django 1.4: `(patch) <https://github.com/django/django/commit/b2ae0a63aeec741f1e51bac9a95a27fd635f9652>`__

February 19, 2013 - No CVE
~~~~~~~~~~~~~~~~~~~~~~~~~~

Additional hardening of ``Host`` header handling. `Full description <https://www.djangoproject.com/weblog/2013/feb/19/security/>`__

Versions affected
-----------------

* Django 1.3 `(patch) <https://github.com/django/django/commit/27cd872e6e36a81d0bb6f5b8765a1705fecfc253>`__

* Django 1.4 `(patch) <https://github.com/django/django/commit/9936fdb11d0bbf0bd242f259bfb97bbf849d16f8>`__

February 19, 2013 - CVE-2013-1664/1665
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2013-1664 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2013-1664&cid=2>`_ and `CVE-2013-1665 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2013-1665&cid=2>`_: Entity-based attacks against Python XML libraries. `Full description <https://www.djangoproject.com/weblog/2013/feb/19/security/>`__

Versions affected
-----------------

* Django 1.3 `(patch) <https://github.com/django/django/commit/d19a27066b2247102e65412aa66917aff0091112>`__

* Django 1.4 `(patch) <https://github.com/django/django/commit/1c60d07ba23e0350351c278ad28d0bd5aa410b40>`__

February 19, 2013 - CVE-2013-0305
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2013-0305 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2013-0305&cid=2>`_: Information leakage via admin history log.  `Full description <https://www.djangoproject.com/weblog/2013/feb/19/security/>`__

Versions affected
-----------------

* Django 1.3 `(patch) <https://github.com/django/django/commit/d3a45e10c8ac8268899999129daa27652ec0da35>`__

* Django 1.4 `(patch) <https://github.com/django/django/commit/0e7861aec73702f7933ce2a93056f7983939f0d6>`__


February 19, 2013 - CVE-2013-0306
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2013-0306 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2013-0306&cid=2>`_: Denial-of-service via formset ``max_num`` bypass. `Full description <https://www.djangoproject.com/weblog/2013/feb/19/security/>`__

Versions affected
-----------------

* Django 1.3 `(patch) <https://github.com/django/django/commit/d7094bbce8cb838f3b40f504f198c098ff1cf727>`__

* Django 1.4 `(patch) <https://github.com/django/django/commit/0cc350a896f70ace18280410eb616a9197d862b0>`__

August 13, 2013 - Awaiting CVE 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(CVE not yet issued): XSS via admin trusting ``URLField`` values. `Full description <https://www.djangoproject.com/weblog/2013/aug/13/security-releases-issued/>`__

Versions affected
-----------------

* Django 1.5 `(patch) <https://github.com/django/django/commit/90363e388c61874add3f3557ee654a996ec75d78>`__

August 13, 2013 - Awaiting CVE 2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(CVE not yet issued): Possible XSS via unvalidated URL redirect schemes. `Full description <https://www.djangoproject.com/weblog/2013/aug/13/security-releases-issued/>`__

Versions affected
-----------------

* Django 1.4 `(patch) <https://github.com/django/django/commit/ec67af0bd609c412b76eaa4cc89968a2a8e5ad6a>`__

* Django 1.5 `(patch) <https://github.com/django/django/commit/1a274ccd6bc1afbdac80344c9b6e5810c1162b5f>`__

September 10, 2013 - CVE-2013-4315
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`CVE-2013-4315 <http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2013-4315&cid=2>`_ Directory-traversal via ``ssi`` template tag. `Full description <https://www.djangoproject.com/weblog/2013/sep/10/security-releases-issued/>`__

Versions affected
-----------------

* Django 1.4 `(patch) <https://github.com/django/django/commit/87d2750b39f6f2d54b7047225521a44dcd37e896>`__

* Django 1.5 `(patch) <https://github.com/django/django/commit/988b61c550d798f9a66d17ee0511fb7a9a7f33ca>`__


September 14, 2013 - CVE-2013-1443
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CVE-2013-1443: Denial-of-service via large passwords. `Full description <https://www.djangoproject.com/weblog/2013/sep/15/security/>`__

Versions affected
-----------------

* Django 1.4 `(patch <https://github.com/django/django/commit/3f3d887a6844ec2db743fee64c9e53e04d39a368>`__ and `Python compatibility fix) <https://github.com/django/django/commit/6903d1690a92aa040adfb0c8eb37cf62e4206714>`__

* Django 1.5 `(patch) <https://github.com/django/django/commit/22b74fa09d7ccbc8c52270d648a0da7f3f0fa2bc>`__
