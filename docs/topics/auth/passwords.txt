=============================
Password management in Django
=============================

Password management is something that should generally not be reinvented
unnecessarily, and Django endeavors to provide a secure and flexible set of
tools for managing user passwords. This document describes how Django stores
passwords, how the storage hashing can be configured, and some utilities to
work with hashed passwords.

.. _auth_password_storage:

How Django stores passwords
===========================

.. versionadded:: 1.4
   Django 1.4 introduces a new flexible password storage system and uses
   PBKDF2 by default. Previous versions of Django used SHA1, and other
   algorithms couldn't be chosen.

The :attr:`~django.contrib.auth.models.User.password` attribute of a
:class:`~django.contrib.auth.models.User` object is a string in this format::

    <algorithm>$<iterations>$<salt>$<hash>

Those are the components used for storing a User's password, separated by the
dollar-sign character and consist of: the hashing algorithm, the number of
algorithm iterations (work factor), the random salt, and the resulting password
hash.  The algorithm is one of a number of one-way hashing or password storage
algorithms Django can use; see below. Iterations describe the number of times
the algorithm is run over the hash. Salt is the random seed used and the hash
is the result of the one-way function.

By default, Django uses the PBKDF2_ algorithm with a SHA256 hash, a
password stretching mechanism recommended by NIST_. This should be
sufficient for most users: it's quite secure, requiring massive
amounts of computing time to break.

However, depending on your requirements, you may choose a different
algorithm, or even use a custom algorithm to match your specific
security situation. Again, most users shouldn't need to do this -- if
you're not sure, you probably don't.  If you do, please read on:

Django chooses the algorithm to use by consulting the
:setting:`PASSWORD_HASHERS` setting. This is a list of hashing algorithm
classes that this Django installation supports. The first entry in this list
(that is, ``settings.PASSWORD_HASHERS[0]``) will be used to store passwords,
and all the other entries are valid hashers that can be used to check existing
passwords.  This means that if you want to use a different algorithm, you'll
need to modify :setting:`PASSWORD_HASHERS` to list your preferred algorithm
first in the list.

The default for :setting:`PASSWORD_HASHERS` is::

    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
        'django.contrib.auth.hashers.BCryptPasswordHasher',
        'django.contrib.auth.hashers.SHA1PasswordHasher',
        'django.contrib.auth.hashers.MD5PasswordHasher',
        'django.contrib.auth.hashers.CryptPasswordHasher',
    )

This means that Django will use PBKDF2_ to store all passwords, but will support
checking passwords stored with PBKDF2SHA1, bcrypt_, SHA1_, etc. The next few
sections describe a couple of common ways advanced users may want to modify this
setting.

.. _bcrypt_usage:

Using bcrypt with Django
------------------------

Bcrypt_ is a popular password storage algorithm that's specifically designed
for long-term password storage. It's not the default used by Django since it
requires the use of third-party libraries, but since many people may want to
use it Django supports bcrypt with minimal effort.

To use Bcrypt as your default storage algorithm, do the following:

1. Install the `py-bcrypt`_ library (probably by running ``sudo pip install
   py-bcrypt``, or downloading the library and installing it with ``python
   setup.py install``).

2. Modify :setting:`PASSWORD_HASHERS` to list ``BCryptPasswordHasher``
   first. That is, in your settings file, you'd put::

        PASSWORD_HASHERS = (
            'django.contrib.auth.hashers.BCryptPasswordHasher',
            'django.contrib.auth.hashers.PBKDF2PasswordHasher',
            'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
            'django.contrib.auth.hashers.SHA1PasswordHasher',
            'django.contrib.auth.hashers.MD5PasswordHasher',
            'django.contrib.auth.hashers.CryptPasswordHasher',
        )

   (You need to keep the other entries in this list, or else Django won't
   be able to upgrade passwords; see below).

That's it -- now your Django install will use Bcrypt as the default storage
algorithm.

.. admonition:: Other bcrypt implementations

   There are several other implementations that allow bcrypt to be
   used with Django. Django's bcrypt support is NOT directly
   compatible with these. To upgrade, you will need to modify the
   hashes in your database to be in the form `bcrypt$(raw bcrypt
   output)`. For example:
   `bcrypt$$2a$12$NT0I31Sa7ihGEWpka9ASYrEFkhuTNeBQ2xfZskIiiJeyFXhRgS.Sy`.

Increasing the work factor
--------------------------

The PBKDF2 and bcrypt algorithms use a number of iterations or rounds of
hashing. This deliberately slows down attackers, making attacks against hashed
passwords harder. However, as computing power increases, the number of
iterations needs to be increased. We've chosen a reasonable default (and will
increase it with each release of Django), but you may wish to tune it up or
down, depending on your security needs and available processing power. To do so,
you'll subclass the appropriate algorithm and override the ``iterations``
parameters. For example, to increase the number of iterations used by the
default PBKDF2 algorithm:

1. Create a subclass of ``django.contrib.auth.hashers.PBKDF2PasswordHasher``::

        from django.contrib.auth.hashers import PBKDF2PasswordHasher

        class MyPBKDF2PasswordHasher(PBKDF2PasswordHasher):
            """
            A subclass of PBKDF2PasswordHasher that uses 100 times more iterations.
            """
            iterations = PBKDF2PasswordHasher.iterations * 100

   Save this somewhere in your project. For example, you might put this in
   a file like ``myproject/hashers.py``.

2. Add your new hasher as the first entry in :setting:`PASSWORD_HASHERS`::

        PASSWORD_HASHERS = (
            'myproject.hashers.MyPBKDF2PasswordHasher',
            'django.contrib.auth.hashers.PBKDF2PasswordHasher',
            'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
            'django.contrib.auth.hashers.BCryptPasswordHasher',
            'django.contrib.auth.hashers.SHA1PasswordHasher',
            'django.contrib.auth.hashers.MD5PasswordHasher',
            'django.contrib.auth.hashers.CryptPasswordHasher',
        )


That's it -- now your Django install will use more iterations when it
stores passwords using PBKDF2.

Password upgrading
------------------

When users log in, if their passwords are stored with anything other than
the preferred algorithm, Django will automatically upgrade the algorithm
to the preferred one. This means that old installs of Django will get
automatically more secure as users log in, and it also means that you
can switch to new (and better) storage algorithms as they get invented.

However, Django can only upgrade passwords that use algorithms mentioned in
:setting:`PASSWORD_HASHERS`, so as you upgrade to new systems you should make
sure never to *remove* entries from this list. If you do, users using un-
mentioned algorithms won't be able to upgrade.

.. _sha1: http://en.wikipedia.org/wiki/SHA1
.. _pbkdf2: http://en.wikipedia.org/wiki/PBKDF2
.. _nist: http://csrc.nist.gov/publications/nistpubs/800-132/nist-sp800-132.pdf
.. _bcrypt: http://en.wikipedia.org/wiki/Bcrypt
.. _py-bcrypt: http://pypi.python.org/pypi/py-bcrypt/


Manually managing a user's password
===================================

.. module:: django.contrib.auth.hashers

.. versionadded:: 1.4
    The :mod:`django.contrib.auth.hashers` module provides a set of functions
    to create and validate hashed password. You can use them independently
    from the ``User`` model.

.. function:: check_password(password, encoded)

    .. versionadded:: 1.4

    If you'd like to manually authenticate a user by comparing a plain-text
    password to the hashed password in the database, use the convenience
    function :func:`check_password`. It takes two arguments: the plain-text
    password to check, and the full value of a user's ``password`` field in the
    database to check against, and returns ``True`` if they match, ``False``
    otherwise.

.. function:: make_password(password[, salt, hashers])

    .. versionadded:: 1.4

    Creates a hashed password in the format used by this application. It takes
    one mandatory argument: the password in plain-text. Optionally, you can
    provide a salt and a hashing algorithm to use, if you don't want to use the
    defaults (first entry of ``PASSWORD_HASHERS`` setting).
    Currently supported algorithms are: ``'pbkdf2_sha256'``, ``'pbkdf2_sha1'``,
    ``'bcrypt'`` (see :ref:`bcrypt_usage`), ``'sha1'``, ``'md5'``,
    ``'unsalted_md5'`` (only for backward compatibility) and ``'crypt'``
    if you have the ``crypt`` library installed. If the password argument is
    ``None``, an unusable password is returned (a one that will be never
    accepted by :func:`check_password`).

.. function:: is_password_usable(encoded_password)

   .. versionadded:: 1.4

   Checks if the given string is a hashed password that has a chance
   of being verified against :func:`check_password`.
