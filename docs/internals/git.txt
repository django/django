=================================
The Django source code repository
=================================

When deploying a Django application into a real production environment, you
will almost always want to use `an official packaged release of Django`_.

However, if you'd like to try out in-development code from an upcoming release
or contribute to the development of Django, you'll need to obtain a clone of
Django's source code repository.

This document covers the way the code repository is laid out and how to work
with and find things in it.

.. _an official packaged release of Django: https://www.djangoproject.com/download/

High-level overview
===================

The Django source code repository uses `Git`_ to track changes to the code
over time, so you'll need a copy of the Git client (a program called ``git``)
on your computer, and you'll want to familiarize yourself with the basics of
how Git works.

Git's website offers downloads for various operating systems. The site also
contains vast amounts of `documentation`_.

The Django Git repository is located online at `github.com/django/django
<https://github.com/django/django>`_. It contains the full source code for all
Django releases, which you can browse online.

The Git repository includes several `branches`_:

* ``master`` contains the main in-development code which will become
  the next packaged release of Django. This is where most development
  activity is focused.

* ``stable/A.B.x`` are the branches where release preparation work happens.
  They are also used for bugfix and security releases which occur as necessary
  after the initial release of a feature version.

* ``soc20XX/<project>`` branches were used by students who worked on Django
  during the 2009 and 2010 Google Summer of Code programs.

* ``attic/<project>`` branches were used to develop major or experimental new
  features without affecting the rest of Django's code.

The Git repository also contains `tags`_. These are the exact revisions from
which packaged Django releases were produced, since version 1.0.

The source code for the `Djangoproject.com <https://www.djangoproject.com/>`_
website can be found at `github.com/django/djangoproject.com
<https://github.com/django/djangoproject.com>`_.

.. _Git: http://git-scm.com/
.. _documentation: http://git-scm.com/documentation
.. _branches: https://github.com/django/django/branches
.. _tags: https://github.com/django/django/tags

The master branch
=================

If you'd like to try out the in-development code for the next release of
Django, or if you'd like to contribute to Django by fixing bugs or developing
new features, you'll want to get the code from the master branch.

Note that this will get *all* of Django: in addition to the top-level
``django`` module containing Python code, you'll also get a copy of Django's
documentation, test suite, packaging scripts and other miscellaneous bits.
Django's code will be present in your clone as a directory named
``django``.

To try out the in-development code with your own applications, simply place
the directory containing your clone on your Python import path. Then
``import`` statements which look for Django will find the ``django`` module
within your clone.

If you're going to be working on Django's code (say, to fix a bug or
develop a new feature), you can probably stop reading here and move
over to :doc:`the documentation for contributing to Django
</internals/contributing/index>`, which covers things like the preferred
coding style and how to generate and submit a patch.

Other branches
==============

Django uses branches to prepare for releases of Django.

In the past when Django was hosted on Subversion, branches were also used for
feature development. Now Django is hosted on Git and feature development is
done on contributor's forks, but the Subversion feature branches remain in Git
for historical reference.

Stable branches
---------------

These branches can be found in the repository as ``stable/A.B.x``
branches and will be created right after the first alpha is tagged.

For example, immediately after *Django 1.5 alpha 1* was tagged, the branch
``stable/1.5.x`` was created and all further work on preparing the code for the
final 1.5 release was done there.

These branches also provide limited bugfix support for the most recent released
version of Django and security support for the two most recently-released
versions of Django.

For example, after the release of Django 1.5, the branch ``stable/1.5.x``
receives only fixes for security and critical stability bugs, which are
eventually released as Django 1.5.1 and so on, ``stable/1.4.x`` receives only
security fixes, and ``stable/1.3.x`` no longer receives any updates.

.. admonition:: Historical information

    This policy for handling ``stable/A.B.x`` branches was adopted starting
    with the Django 1.5 release cycle.

    Previously, these branches weren't created until right after the releases
    and the stabilization work occurred on the main repository branch. Thus,
    no new features development work for the next release of Django could be
    committed until the final release happened.

    For example, shortly after the release of Django 1.3 the branch
    ``stable/1.3.x`` was created. Official support for that release has expired,
    and so it no longer receives direct maintenance from the Django project.
    However, that and all other similarly named branches continue to exist and
    interested community members have occasionally used them to provide
    unofficial support for old Django releases.

Feature-development branches
----------------------------

.. admonition:: Historical information

    Since Django moved to Git in 2012, anyone can clone the repository and
    create their own branches, alleviating the need for official branches in
    the source code repository.

    The following section is mostly useful if you're exploring the repository's
    history, for example if you're trying to understand how some features were
    designed.

Feature-development branches tend by their nature to be temporary. Some
produce successful features which are merged back into Django's master to
become part of an official release, but others do not; in either case there
comes a time when the branch is no longer being actively worked on by any
developer. At this point the branch is considered closed.

Unfortunately, Django used to be maintained with the Subversion revision
control system, that has no standard way of indicating this. As a workaround,
branches of Django which are closed and no longer maintained were moved into
``attic``.

For reference, the following are branches whose code eventually became
part of Django itself, and so are no longer separately maintained:

* ``boulder-oracle-sprint``: Added support for Oracle databases to
  Django's object-relational mapper. This has been part of Django
  since the 1.0 release.

* ``gis``: Added support for geographic/spatial queries to Django's
  object-relational mapper. This has been part of Django since the 1.0
  release, as the bundled application ``django.contrib.gis``.

* ``i18n``: Added :doc:`internationalization support </topics/i18n/index>` to
  Django. This has been part of Django since the 0.90 release.

* ``magic-removal``: A major refactoring of both the internals and
  public APIs of Django's object-relational mapper. This has been part
  of Django since the 0.95 release.

* ``multi-auth``: A refactoring of :doc:`Django's bundled
  authentication framework </topics/auth/index>` which added support for
  :ref:`authentication backends <authentication-backends>`. This has
  been part of Django since the 0.95 release.

* ``new-admin``: A refactoring of :doc:`Django's bundled
  administrative application </ref/contrib/admin/index>`. This became part of
  Django as of the 0.91 release, but was superseded by another
  refactoring (see next listing) prior to the Django 1.0 release.

* ``newforms-admin``: The second refactoring of Django's bundled
  administrative application. This became part of Django as of the 1.0
  release, and is the basis of the current incarnation of
  ``django.contrib.admin``.

* ``queryset-refactor``: A refactoring of the internals of Django's
  object-relational mapper. This became part of Django as of the 1.0
  release.

* ``unicode``: A refactoring of Django's internals to consistently use
  Unicode-based strings in most places within Django and Django
  applications. This became part of Django as of the 1.0 release.

When Django moved from SVN to Git, the information about branch merges wasn't
preserved in the source code repository. This means that the ``master`` branch
of Django doesn't contain merge commits for the above branches.

However, this information is `available as a grafts file`_. You can restore it
by putting the following lines in ``.git/info/grafts`` in your local clone::

  ac64e91a0cadc57f4bc5cd5d66955832320ca7a1 553a20075e6991e7a60baee51ea68c8adc520d9a 0cb8e31823b2e9f05c4ae868c19f5f38e78a5f2e
  79e68c225b926302ebb29c808dda8afa49856f5c d0f57e7c7385a112cb9e19d314352fc5ed5b0747 aa239e3e5405933af6a29dac3cf587b59a099927
  5cf8f684237ab5addaf3549b2347c3adf107c0a7 cb45fd0ae20597306cd1f877efc99d9bd7cbee98 e27211a0deae2f1d402537f0ebb64ad4ccf6a4da
  f69cf70ed813a8cd7e1f963a14ae39103e8d5265 d5dbeaa9be359a4c794885c2e9f1b5a7e5e51fb8 d2fcbcf9d76d5bb8a661ee73dae976c74183098b
  aab3a418ac9293bb4abd7670f65d930cb0426d58 4ea7a11659b8a0ab07b0d2e847975f7324664f10 adf4b9311d5d64a2bdd58da50271c121ea22e397
  ff60c5f9de3e8690d1e86f3e9e3f7248a15397c8 7ef212af149540aa2da577a960d0d87029fd1514 45b4288bb66a3cda401b45901e85b645674c3988
  9dda4abee1225db7a7b195b84c915fdd141a7260 4fe5c9b7ee09dc25921918a6dbb7605edb374bc9 3a7c14b583621272d4ef53061287b619ce3c290d
  a19ed8aea395e8e07164ff7d85bd7dff2f24edca dc375fb0f3b7fbae740e8cfcd791b8bccb8a4e66 42ea7a5ce8aece67d16c6610a49560c1493d4653
  9c52d56f6f8a9cdafb231adf9f4110473099c9b5 c91a30f00fd182faf8ca5c03cd7dbcf8b735b458 4a5c5c78f2ecd4ed8859cd5ac773ff3a01bccf96
  953badbea5a04159adbfa970f5805c0232b6a401 4c958b15b250866b70ded7d82aa532f1e57f96ae 5664a678b29ab04cad425c15b2792f4519f43928
  471596fc1afcb9c6258d317c619eaf5fd394e797 4e89105d64bb9e04c409139a41e9c7aac263df4c 3e9035a9625c8a8a5e88361133e87ce455c4fc13
  9233d0426537615e06b78d28010d17d5a66adf44 6632739e94c6c38b4c5a86cf5c80c48ae50ac49f 18e151bc3f8a85f2766d64262902a9fcad44d937

.. _available as a grafts file: https://github.com/ramiro/django-git-grafts

Additionally, the following branches are closed, but their code was
never merged into Django and the features they aimed to implement
were never finished:

* ``full-history``

* ``generic-auth``

* ``multiple-db-support``

* ``per-object-permissions``

* ``schema-evolution``

* ``schema-evolution-ng``

* ``search-api``

* ``sqlalchemy``

All of the above-mentioned branches now reside in ``attic``.

Finally, the repository contains ``soc2009/xxx`` and ``soc2010/xxx`` feature
branches, used for Google Summer of Code projects.

Tags
====

Each Django release is tagged and signed by a :ref:`releaser
<releasers-list>`.

The tags can be found on GitHub's `tags`_ page.

.. _tags: https://github.com/django/django/tags
