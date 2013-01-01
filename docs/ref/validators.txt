==========
Validators
==========

.. module:: django.core.validators
    :synopsis: Validation utilities and base classes

Writing validators
==================

A validator is a callable that takes a value and raises a
:exc:`~django.core.exceptions.ValidationError` if it doesn't meet some
criteria. Validators can be useful for re-using validation logic between
different types of fields.

For example, here's a validator that only allows even numbers::

    from django.core.exceptions import ValidationError

    def validate_even(value):
        if value % 2 != 0:
            raise ValidationError(u'%s is not an even number' % value)

You can add this to a model field via the field's :attr:`~django.db.models.Field.validators`
argument::

    from django.db import models

    class MyModel(models.Model):
        even_field = models.IntegerField(validators=[validate_even])

Because values are converted to Python before validators are run, you can even
use the same validator with forms::

    from django import forms

    class MyForm(forms.Form):
        even_field = forms.IntegerField(validators=[validate_even])

How validators are run
======================

See the :doc:`form validation </ref/forms/validation>` for more information on
how validators are run in forms, and :ref:`Validating objects
<validating-objects>` for how they're run in models. Note that validators will
not be run automatically when you save a model, but if you are using a
:class:`~django.forms.ModelForm`, it will run your validators on any fields
that are included in your form. See the
:doc:`ModelForm documentation </topics/forms/modelforms>` for information on
how model validation interacts with forms.

Built-in validators
===================

The :mod:`django.core.validators` module contains a collection of callable
validators for use with model and form fields. They're used internally but
are available for use with your own fields, too. They can be used in addition
to, or in lieu of custom ``field.clean()`` methods.

``RegexValidator``
------------------
.. class:: RegexValidator([regex=None, message=None, code=None])

    :param regex: If not ``None``, overrides :attr:`regex`. Can be a regular
        expression string or a pre-compiled regular expression.
    :param message: If not ``None``, overrides :attr:`.message`.
    :param code: If not ``None``, overrides :attr:`code`.

    .. attribute:: regex

        The regular expression pattern to search for the provided ``value``,
        or a pre-compiled regular expression. Raises a
        :exc:`~django.core.exceptions.ValidationError` with :attr:`message`
        and :attr:`code` if no match is found. By default, matches any string
        (including an empty string).

    .. attribute:: message

        The error message used by
        :exc:`~django.core.exceptions.ValidationError` if validation fails.
        Defaults to ``"Enter a valid value"``.

    .. attribute:: code

        The error code used by :exc:`~django.core.exceptions.ValidationError`
        if validation fails. Defaults to ``"invalid"``.

``URLValidator``
----------------
.. class:: URLValidator()

    A :class:`RegexValidator` that ensures a value looks like a URL, and raises
    an error code of ``'invalid'`` if it doesn't.

``validate_email``
------------------
.. data:: validate_email

    A :class:`RegexValidator` instance that ensures a value looks like an
    email address.

``validate_slug``
-----------------
.. data:: validate_slug

    A :class:`RegexValidator` instance that ensures a value consists of only
    letters, numbers, underscores or hyphens.

``validate_ipv4_address``
-------------------------
.. data:: validate_ipv4_address

    A :class:`RegexValidator` instance that ensures a value looks like an IPv4
    address.

``validate_ipv6_address``
-------------------------
.. versionadded:: 1.4

.. data:: validate_ipv6_address

    Uses ``django.utils.ipv6`` to check the validity of an IPv6 address.

``validate_ipv46_address``
--------------------------
.. versionadded:: 1.4

.. data:: validate_ipv46_address

    Uses both ``validate_ipv4_address`` and ``validate_ipv6_address`` to
    ensure a value is either a valid IPv4 or IPv6 address.

``validate_comma_separated_integer_list``
-----------------------------------------
.. data:: validate_comma_separated_integer_list

    A :class:`RegexValidator` instance that ensures a value is a
    comma-separated list of integers.

``MaxValueValidator``
---------------------
.. class:: MaxValueValidator(max_value)

    Raises a :exc:`~django.core.exceptions.ValidationError` with a code of
    ``'max_value'`` if ``value`` is greater than ``max_value``.

``MinValueValidator``
---------------------
.. class:: MinValueValidator(min_value)

    Raises a :exc:`~django.core.exceptions.ValidationError` with a code of
    ``'min_value'`` if ``value`` is less than ``min_value``.

``MaxLengthValidator``
----------------------
.. class:: MaxLengthValidator(max_length)

    Raises a :exc:`~django.core.exceptions.ValidationError` with a code of
    ``'max_length'`` if the length of ``value`` is greater than ``max_length``.

``MinLengthValidator``
----------------------
.. class:: MinLengthValidator(min_length)

    Raises a :exc:`~django.core.exceptions.ValidationError` with a code of
    ``'min_length'`` if the length of ``value`` is less than ``min_length``.
