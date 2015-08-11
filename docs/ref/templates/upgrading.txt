=================================
Upgrading templates to Django 1.8
=================================

Django's template system was overhauled in Django 1.8 when it gained support
for multiple template engines. This document complements the :doc:`release
notes </releases/1.8>` with detailed upgrade instructions on some topics.

The :setting:`TEMPLATES` settings
=================================

A new setting was introduced in Django 1.8: :setting:`TEMPLATES`. All existing
template-related settings were deprecated.

During the deprecation period, Django will create a backwards-compatible
:setting:`TEMPLATES` based on the ``TEMPLATE_*`` settings if you don't define
it yourself.

Here's how to define :setting:`TEMPLATES` in your settings module.

If you're using the default value of ``TEMPLATE_LOADERS``, that is, if it
isn't defined in your settings file or if it's set to::

    ['django.template.loaders.filesystem.Loader',
     'django.template.loaders.app_directories.Loader']

then you should define :setting:`TEMPLATES` as follows::

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [
                # insert your TEMPLATE_DIRS here
            ],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                    # list if you haven't customized them:
                    'django.contrib.auth.context_processors.auth',
                    'django.template.context_processors.debug',
                    'django.template.context_processors.i18n',
                    'django.template.context_processors.media',
                    'django.template.context_processors.static',
                    'django.template.context_processors.tz',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        },
    ]

If you aren't using the default value of ``TEMPLATE_LOADERS``, then you should
define :setting:`TEMPLATES` as follows::

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [
                # insert your TEMPLATE_DIRS here
            ],
            'OPTIONS': {
                'context_processors': [
                    # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                    # list if you haven't customized them:
                    'django.contrib.auth.context_processors.auth',
                    'django.template.context_processors.debug',
                    'django.template.context_processors.i18n',
                    'django.template.context_processors.media',
                    'django.template.context_processors.static',
                    'django.template.context_processors.tz',
                    'django.contrib.messages.context_processors.messages',
                ],
                'loaders': [
                    # insert your TEMPLATE_LOADERS here
                ]
            },
        },
    ]

Furthermore you should replace ``django.core.context_processors`` with
``django.template.context_processors`` in the names of context processors.

If your settings module defines ``ALLOWED_INCLUDE_ROOTS`` or
``TEMPLATE_STRING_IF_INVALID``, include their values under the
``'allowed_include_roots'`` and ``'string_if_invalid'`` keys in the
``'OPTIONS'`` dictionary.

If it sets ``TEMPLATE_DEBUG`` to a value that differs from :setting:`DEBUG`,
include that value under the ``'debug'`` key in ``'OPTIONS'``.

Once you have defined :setting:`TEMPLATES`, you can safely remove
``ALLOWED_INCLUDE_ROOTS``, ``TEMPLATE_CONTEXT_PROCESSORS``,
``TEMPLATE_DEBUG``, ``TEMPLATE_DIRS``, ``TEMPLATE_LOADERS``, and
``TEMPLATE_STRING_IF_INVALID``.

If you are overriding some of these settings in tests, you should override the
entire :setting:`TEMPLATES` setting instead.

:mod:`django.template.loader`
=============================

.. _get_template-upgrade-django-18:

:func:`~django.template.loader.get_template` and :func:`~django.template.loader.select_template`
------------------------------------------------------------------------------------------------

In Django 1.8 :func:`~django.template.loader.get_template` and
:func:`~django.template.loader.select_template` return a backend-dependent
``Template`` instead of a :class:`django.template.Template`.

For example, if :func:`~django.template.loader.get_template` loads a template
with a :class:`~django.template.backends.django.DjangoTemplates` backend, then
it returns a ``django.template.backends.django.Template``.

``Template`` objects must provide a
:meth:`~django.template.backends.base.Template.render` method whose signature
differs slightly from the Django template language's
:meth:`~django.template.Template.render`.

Instead of::

    from django.template import Context
    from django.template.loader import get_template

    template = get_template('hello.html')
    html = template.render(Context({'name': 'world'}))

You should write::

    from django.template.loader import get_template

    template = get_template('hello.html')
    html = template.render({'name': 'world'})

And instead of::

    from django.template import RequestContext
    from django.template.loader import get_template

    template = get_template('hello.html')
    html = template.render(RequestContext(request, {'name': 'world'}))

You should write::

    from django.template.loader import get_template

    template = get_template('hello.html')
    html = template.render({'name': 'world'}, request)

Passing a :class:`~django.template.Context` or a
:class:`~django.template.RequestContext` is still possible when the template
is loaded by a :class:`~django.template.backends.django.DjangoTemplates`
backend but it's deprecated and won't be supported in Django 1.10.

If you're loading a template while you're rendering another template with the
Django template language and you have access to the current context, for
instance in the ``render()`` method of a template tag, you can use the current
:class:`~django.template.Engine` directly. Instead of::

    from django.template.loader import get_template
    template = get_template('included.html')

You can write::

    template = context.template.engine.get_template('included.html')

This will load the template with the current engine without triggering the
multiple template engines machinery, which is usually the desired behavior.
Unlike previous solutions, this returns a :class:`django.template.Template`,
like :func:`~django.template.loader.get_template` used to in Django 1.7 and
earlier, avoiding all backwards-compatibility problems.

``get_template_from_string()``
------------------------------

Private API ``get_template_from_string(template_code)`` was removed in Django
1.8 because it had no way to choose an engine to compile the template.

Three alternatives are available.

If you control the project's setting, you can use one of the configured
engines::

    from django.template import engines

    template = engines['django'].from_string(template_code)

This returns a backend-dependent ``Template`` object.

For trivial templates that don't need context processors nor anything else,
you can create a bare-bones engine and use its ``from_string()`` method::

    from django.template import Engine

    template = Engine().from_string(template_code)

This returns a :class:`django.template.Template` because
:class:`~django.template.Engine` is part of the Django template language's
APIs. The multiple template engines machinery isn't involved here.

Finally, if you have access to the current context, you can use the same trick
as above::

    template = context.template.engine.from_string(template_code)

``Template()``
==============

To a lesser extent, instantiating a template with ``Template(template_code)``
suffers from the same issue as ``get_template_from_string()``.

It still works when the :setting:`TEMPLATES` setting defines exactly one
:class:`~django.template.backends.django.DjangoTemplates` backend, but
pluggable applications can't control this requirement.

The last two solutions described in the previous section are recommended in
that case.
