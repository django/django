=====================
Writing documentation
=====================

We place a high importance on consistency and readability of documentation.
After all, Django was created in a journalism environment! So we treat our
documentation like we treat our code: we aim to improve it as often as
possible.

Documentation changes generally come in two forms:

* General improvements: typo corrections, error fixes and better
  explanations through clearer writing and more examples.

* New features: documentation of features that have been added to the
  framework since the last release.

This section explains how writers can craft their documentation changes
in the most useful and least error-prone ways.

Getting the raw documentation
=============================

Though Django's documentation is intended to be read as HTML at
https://docs.djangoproject.com/, we edit it as a collection of text files for
maximum flexibility. These files live in the top-level ``docs/`` directory of a
Django release.

If you'd like to start contributing to our docs, get the development version of
Django from the source code repository
(see :ref:`installing-development-version`). The development version has the
latest-and-greatest documentation, just as it has latest-and-greatest code.
We also backport documentation fixes and improvements, at the discretion of the
committer, to the last release branch. That's because it's highly advantageous
to have the docs for the last release be up-to-date and correct (see
:ref:`differences-between-doc-versions`).

Getting started with Sphinx
===========================

Django's documentation uses the Sphinx__ documentation system, which in turn
is based on docutils__. The basic idea is that lightly-formatted plain-text
documentation is transformed into HTML, PDF, and any other output format.

__ http://sphinx-doc.org/
__ http://docutils.sourceforge.net/

To actually build the documentation locally, you'll currently need to install
Sphinx -- ``pip install Sphinx`` should do the trick.

Then, building the HTML is easy; just ``make html`` (or ``make.bat html`` on
Windows) from the ``docs`` directory.

To get started contributing, you'll want to read the :ref:`reStructuredText
Primer <sphinx:rst-primer>`. After that, you'll want to read about the
:ref:`Sphinx-specific markup <sphinx:sphinxmarkup>` that's used to manage
metadata, indexing, and cross-references.

How the documentation is organized
==================================

The documentation is organized into several categories:

* :doc:`Tutorials </intro/index>` take the reader by the hand through a series
  of steps to create something.

  The important thing in a tutorial is to help the reader achieve something
  useful, preferably as early as possible, in order to give them confidence.

  Explain the nature of the problem we're solving, so that the reader
  understands what we're trying to achieve. Don't feel that you need to begin
  with explanations of how things work - what matters is what the reader does,
  not what you explain. It can be helpful to refer back to what you've done and
  explain afterwards.

* :doc:`Topic guides </topics/index>` aim to explain a concept or subject at a
  fairly high level.

  Link to reference material rather than repeat it. Use examples and don't be
  reluctant to explain things that seem very basic to you - it might be the
  explanation someone else needs.

  Providing background context helps a newcomer connect the topic to things
  that they already know.

* :doc:`Reference guides </ref/index>` contain technical reference for APIs.
  They describe the functioning of Django's internal machinery and instruct in
  its use.

  Keep reference material tightly focused on the subject. Assume that the
  reader already understands the basic concepts involved but needs to know or
  be reminded of how Django does it.

  Reference guides aren't the place for general explanation. If you find
  yourself explaining basic concepts, you may want to move that material to a
  topic guide.

* :doc:`How-to guides </howto/index>` are recipes that take the reader through
  steps in key subjects.

  What matters most in a how-to guide is what a user wants to achieve.
  A how-to should always be result-oriented rather than focused on internal
  details of how Django implements whatever is being discussed.

  These guides are more advanced than tutorials and assume some knowledge about
  how Django works. Assume that the reader has followed the tutorials and don't
  hesitate to refer the reader back to the appropriate tutorial rather than
  repeat the same material.

Writing style
=============

When using pronouns in reference to a hypothetical person, such as "a user with
a session cookie", gender neutral pronouns (they/their/them) should be used.
Instead of:

* he or she... use they.
* him or her... use them.
* his or her... use their.
* his or hers... use theirs.
* himself or herself... use themselves.

Commonly used terms
===================

Here are some style guidelines on commonly used terms throughout the
documentation:

* **Django** -- when referring to the framework, capitalize Django. It is
  lowercase only in Python code and in the djangoproject.com logo.

* **email** -- no hyphen.

* **MySQL**, **PostgreSQL**, **SQLite**

* **SQL** -- when referring to SQL, the expected pronunciation should be
  "Ess Queue Ell" and not "sequel". Thus in a phrase like "Returns an
  SQL expression", "SQL" should be preceded by "an" and not "a".

* **Python** -- when referring to the language, capitalize Python.

* **realize**, **customize**, **initialize**, etc. -- use the American
  "ize" suffix, not "ise."

* **subclass** -- it's a single word without a hyphen, both as a verb
  ("subclass that model") and as a noun ("create a subclass").

* **Web**, **World Wide Web**, **the Web** -- note Web is always
  capitalized when referring to the World Wide Web.

* **website** -- use one word, without capitalization.

Django-specific terminology
===========================

* **model** -- it's not capitalized.

* **template** -- it's not capitalized.

* **URLconf** -- use three capitalized letters, with no space before
  "conf."

* **view** -- it's not capitalized.

Guidelines for reStructuredText files
=====================================

These guidelines regulate the format of our reST (reStructuredText)
documentation:

* In section titles, capitalize only initial words and proper nouns.

* Wrap the documentation at 80 characters wide, unless a code example
  is significantly less readable when split over two lines, or for another
  good reason.

* The main thing to keep in mind as you write and edit docs is that the
  more semantic markup you can add the better. So::

      Add ``django.contrib.auth`` to your ``INSTALLED_APPS``...

  Isn't nearly as helpful as::

      Add :mod:`django.contrib.auth` to your :setting:`INSTALLED_APPS`...

  This is because Sphinx will generate proper links for the latter, which
  greatly helps readers.

  You can prefix the target with a ``~`` (that's a tilde) to get just the
  "last bit" of that path. So ``:mod:`~django.contrib.auth``` will just
  display a link with the title "auth".

* Use :mod:`~sphinx.ext.intersphinx` to reference Python's and Sphinx'
  documentation.

* Add ``.. code-block:: <lang>`` to literal blocks so that they get
  highlighted. Prefer relying on automatic highlighting simply using ``::``
  (two colons). This has the benefit that if the code contains some invalid
  syntax, it won't be highlighted. Adding ``.. code-block:: python``, for
  example, will force highlighting despite invalid syntax.

* Use these heading styles::

    ===
    One
    ===

    Two
    ===

    Three
    -----

    Four
    ~~~~

    Five
    ^^^^

Django-specific markup
======================

Besides the :ref:`Sphinx built-in markup <sphinx:sphinxmarkup>`, Django's
docs defines some extra description units:

* Settings::

        .. setting:: INSTALLED_APPS

  To link to a setting, use ``:setting:`INSTALLED_APPS```.

* Template tags::

        .. templatetag:: regroup

  To link, use ``:ttag:`regroup```.

* Template filters::

        .. templatefilter:: linebreaksbr

  To link, use ``:tfilter:`linebreaksbr```.

* Field lookups (i.e. ``Foo.objects.filter(bar__exact=whatever)``)::

        .. fieldlookup:: exact

  To link, use ``:lookup:`exact```.

* ``django-admin`` commands::

        .. django-admin:: migrate

  To link, use ``:djadmin:`migrate```.

* ``django-admin`` command-line options::

        .. django-admin-option:: --traceback

  To link, use ``:option:`command_name --traceback``` (or omit ``command_name``
  for the options shared by all commands like ``--verbosity``).

* Links to Trac tickets (typically reserved for patch release notes)::

        :ticket:`12345`

.. _documenting-new-features:

Documenting new features
========================

Our policy for new features is:

    All documentation of new features should be written in a way that
    clearly designates the features are only available in the Django
    development version. Assume documentation readers are using the latest
    release, not the development version.

Our preferred way for marking new features is by prefacing the features'
documentation with: "``.. versionadded:: X.Y``", followed by a mandatory
blank line and an optional description (indented).

General improvements, or other changes to the APIs that should be emphasized
should use the "``.. versionchanged:: X.Y``" directive (with the same format
as the ``versionadded`` mentioned above.

These ``versionadded`` and ``versionchanged`` blocks should be "self-contained."
In other words, since we only keep these annotations around for two releases,
it's nice to be able to remove the annotation and its contents without having
to reflow, reindent, or edit the surrounding text. For example, instead of
putting the entire description of a new or changed feature in a block, do
something like this::

    .. class:: Author(first_name, last_name, middle_name=None)

        A person who writes books.

        ``first_name`` is ...

        ...

        ``middle_name`` is ...

        .. versionchanged:: A.B

            The ``middle_name`` argument was added.

Put the changed annotation notes at the bottom of a section, not the top.

Also, avoid referring to a specific version of Django outside a
``versionadded`` or ``versionchanged`` block. Even inside a block, it's often
redundant to do so as these annotations render as "New in Django A.B:" and
"Changed in Django A.B", respectively.

If a function, attribute, etc. is added, it's also okay to use a
``versionadded`` annotation like this::

    .. attribute:: Author.middle_name

        .. versionadded:: A.B

        An author's middle name.

We can simply remove the ``.. versionadded:: A.B`` annotation without any
indentation changes when the time comes.

Minimizing images
=================

Optimize image compression where possible. For PNG files, use OptiPNG and
AdvanceCOMP's ``advpng``:

.. code-block:: console

   $ cd docs/
   $ optipng -o7 -zm1-9 -i0 -strip all `find . -type f -not -path "./_build/*" -name "*.png"`
   $ advpng -z4 `find . -type f -not -path "./_build/*" -name "*.png"`

This is based on OptiPNG version 0.7.5. Older versions may complain about the
``--strip all`` option being lossy.

An example
==========

For a quick example of how it all fits together, consider this hypothetical
example:

* First, the ``ref/settings.txt`` document could have an overall layout
  like this:

  .. code-block:: rst

    ========
    Settings
    ========

    ...

    .. _available-settings:

    Available settings
    ==================

    ...

    .. _deprecated-settings:

    Deprecated settings
    ===================

    ...

* Next, the ``topics/settings.txt`` document could contain something like
  this:

  .. code-block:: rst

    You can access a :ref:`listing of all available settings
    <available-settings>`. For a list of deprecated settings see
    :ref:`deprecated-settings`.

    You can find both in the :doc:`settings reference document
    </ref/settings>`.

  We use the Sphinx :rst:role:`doc` cross reference element when we want to
  link to another document as a whole and the :rst:role:`ref` element when
  we want to link to an arbitrary location in a document.

* Next, notice how the settings are annotated:

  .. code-block:: rst

    .. setting:: ADMINS

    ADMINS
    ======

    Default: ``[]`` (Empty list)

    A list of all the people who get code error notifications. When
    ``DEBUG=False`` and a view raises an exception, Django will email these people
    with the full exception information. Each member of the list should be a tuple
    of (Full name, email address). Example::

        [('John', 'john@example.com'), ('Mary', 'mary@example.com')]

    Note that Django will email *all* of these people whenever an error happens.
    See :doc:`/howto/error-reporting` for more information.

  This marks up the following header as the "canonical" target for the
  setting ``ADMINS``. This means any time I talk about ``ADMINS``,
  I can reference it using ``:setting:`ADMINS```.

That's basically how everything fits together.

.. _documentation-spelling-check:

Spelling check
==============

Before you commit your docs, it's a good idea to run the spelling checker.
You'll need to install a couple packages first:

* `pyenchant <https://pypi.python.org/pypi/pyenchant/>`_ (which requires
  `enchant <http://www.abisource.com/projects/enchant/>`_)

* `sphinxcontrib-spelling
  <https://pypi.python.org/pypi/sphinxcontrib-spelling/>`_

Then from the ``docs`` directory, run ``make spelling``. Wrong words (if any)
along with the file and line number where they occur will be saved to
``_build/spelling/output.txt``.

If you encounter false-positives (error output that actually is correct), do
one of the following:

* Surround inline code or brand/technology names with grave accents (`).
* Find synonyms that the spell checker recognizes.
* If, and only if, you are sure the word you are using is correct - add it
  to ``docs/spelling_wordlist`` (please keep the list in alphabetical order).

Translating documentation
=========================

See :ref:`Localizing the Django documentation <translating-documentation>` if
you'd like to help translate the documentation into another language.

.. _django-admin-manpage:

``django-admin`` man page
=========================

Sphinx can generate a manual page for the
:doc:`django-admin </ref/django-admin>` command. This is configured in
``docs/conf.py``. Unlike other documentation output, this man page should be
included in the Django repository and the releases as
``docs/man/django-admin.1``. There isn't a need to update this file when
updating the documentation, as it's updated once as part of the release process.

To generate an updated version of the man page, run ``make man`` in the
``docs`` directory. The new man page will be written in
``docs/_build/man/django-admin.1``.
