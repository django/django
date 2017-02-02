==========
Validators
==========

.. module:: django.contrib.postgres.validators

``KeysValidator``
=================

.. class:: KeysValidator(keys, strict=False, messages=None)

    Validates that the given keys are contained in the value. If ``strict`` is
    ``True``, then it also checks that there are no other keys present.

    The ``messages`` passed should be a dict containing the keys
    ``missing_keys`` and/or ``extra_keys``.

    .. note::
        Note that this checks only for the existence of a given key, not that
        the value of a key is non-empty.

Range validators
================

``RangeMaxValueValidator``
--------------------------

.. class:: RangeMaxValueValidator(limit_value, message=None)

    Validates that the upper bound of the range is not greater than
    ``limit_value``.

``RangeMinValueValidator``
--------------------------

.. class:: RangeMinValueValidator(limit_value, message=None)

    Validates that the lower bound of the range is not less than the
    ``limit_value``.
