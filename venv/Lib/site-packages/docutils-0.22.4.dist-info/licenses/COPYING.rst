.. include:: docs/header0.rst

==================
 Copying Docutils
==================

:Author: David Goodger
:Contact: goodger@python.org
:Date: $Date: 2024-11-10 00:36:49 +0100 (So, 10. Nov 2024) $
:Web site: https://docutils.sourceforge.io/
:Copyright: This document has been placed in the public domain.

Most of the files included in this project have been placed in the
public domain, and therefore have no license requirements and no
restrictions on copying or usage; see the `Public Domain Dedication`_
below.  There are exceptions_, listed below.
Files in the Sandbox_ are not distributed with Docutils releases and
may have different license terms.


Public Domain Dedication
========================

The persons who have associated their work with this project (the
"Dedicator": David Goodger and the many contributors to the Docutils
project) hereby dedicate the entire copyright, less the exceptions_
listed below, in the work of authorship known as "Docutils" identified
below (the "Work") to the public domain.

The primary repository for the Work is the Internet World Wide Web
site <https://docutils.sourceforge.io/>.  The Work consists of the
files within the "docutils" module of the Docutils project Subversion
repository (http://svn.code.sf.net/p/docutils/code/),
whose Internet web interface is located at
<https://sourceforge.net/p/docutils/code>.  Files dedicated to the
public domain may be identified by the inclusion, near the beginning
of each file, of a declaration of the form::

    Copyright: This document/module/DTD/stylesheet/file/etc. has been
               placed in the public domain.

Dedicator makes this dedication for the benefit of the public at large
and to the detriment of Dedicator's heirs and successors.  Dedicator
intends this dedication to be an overt act of relinquishment in
perpetuity of all present and future rights under copyright law,
whether vested or contingent, in the Work.  Dedicator understands that
such relinquishment of all rights includes the relinquishment of all
rights to enforce (by lawsuit or otherwise) those copyrights in the
Work.

Dedicator recognizes that, once placed in the public domain, the Work
may be freely reproduced, distributed, transmitted, used, modified,
built upon, or otherwise exploited by anyone for any purpose,
commercial or non-commercial, and in any way, including by methods
that have not yet been invented or conceived.

(This dedication is derived from the text of the `Creative Commons
Public Domain Dedication`. [#]_)

.. [#] Creative Commons has `retired this legal tool`__ and does not
   recommend that it be applied to works: This tool is based on United
   States law and may not be applicable outside the US. For dedicating new
   works to the public domain, Creative Commons recommend the replacement
   Public Domain Dedication CC0_ (CC zero, "No Rights Reserved"). So does
   the Free Software Foundation in its license-list_.

   __  http://creativecommons.org/retiredlicenses
   .. _CC0: http://creativecommons.org/about/cc0

Exceptions
==========

The exceptions to the `Public Domain Dedication`_ above are:

* docutils/utils/smartquotes.py

  Copyright © 2011 Günter Milde,
  based on `SmartyPants`_ © 2003 John Gruber
  (released under a "revised" `BSD 3-Clause License`_ included in the file)
  and smartypants.py © 2004, 2007 Chad Miller.
  Released under the terms of the `BSD 2-Clause License`_
  (`local copy <licenses/BSD-2-Clause.rst>`__).

  .. _SmartyPants: http://daringfireball.net/projects/smartypants/

* docutils/utils/math/latex2mathml.py

  Copyright © Jens Jørgen Mortensen, Günter Milde.
  Released under the terms of the `BSD 2-Clause License`_
  (`local copy <licenses/BSD-2-Clause.rst>`__).

* | docutils/utils/math/math2html.py,
  | docutils/writers/html5_polyglot/math.css

  Copyright © 2009,2010 Alex Fernández; 2021 Günter Milde

  These files were part of eLyXer_, released under the `GNU
  General Public License`_ version 3 or later. The author relicensed
  them for Docutils under the terms of the `BSD 2-Clause License`_
  (`local copy <licenses/BSD-2-Clause.rst>`__).

  .. _eLyXer: https://github.com/alexfernandez/elyxer

* | docutils/__main__.py,
  | docutils/parsers/commonmark_wrapper.py,
  | docutils/parsers/recommonmark_wrapper.py,
  | docutils/utils/error_reporting.py,
  | docutils/utils/math/__init__.py,
  | docutils/utils/math/latex2mathml.py,
  | docutils/utils/math/tex2mathml_extern.py,
  | docutils/utils/punctuation_chars.py,
  | docutils/utils/smartquotes.py,
  | docutils/writers/html5_polyglot/__init__.py,
  | docutils/writers/html5_polyglot/\*.css,
  | docutils/writers/latex2e/docutils.sty,
  | docutils/writers/xetex/__init__.py,
  | test/test_parsers/test_recommonmark/\*.py,
  | test/test_parsers/test_rst/test_directives/test__init__.py,
  | test/test_parsers/test_rst/test_directives/test_code_parsing.py,
  | test/test_parsers/test_rst/test_line_length_limit_default.py,
  | test/test_parsers/test_rst/test_line_length_limit.py,
  | test/test_writers/test_latex2e_misc.py,
  | test/transforms/test_smartquotes.py,
  | tools/docutils-cli.py,
  | tools/rst2html5.py

  Copyright © Günter Milde.
  Released under the terms of the `BSD 2-Clause License`_
  (`local copy <licenses/BSD-2-Clause.rst>`__).

* tools/editors/emacs/rst.el

  copyright by Free Software Foundation, Inc.,
  released under the `GNU General Public License`_ version 3 or later
  (`local copy`__).

  __ licenses/gpl-3-0.rst

All used licenses are OSI-approved_ and GPL-compatible_.

Plaintext versions of all the linked-to licenses are provided in the
licenses_ directory.

.. _sandbox: https://docutils.sourceforge.io/sandbox/README.html
.. _licenses: licenses/
.. _GNU General Public License: https://www.gnu.org/copyleft/gpl.html
.. _BSD 2-Clause License: http://opensource.org/licenses/BSD-2-Clause
.. _BSD 3-Clause License: https://opensource.org/licenses/BSD-3-Clause
.. _OSI-approved: http://opensource.org/licenses/
.. _license-list:
.. _GPL-compatible: https://www.gnu.org/licenses/license-list.html
