====================
Model Form Functions
====================

.. module:: django.forms.models
   :synopsis: Django's functions for building model forms and formsets.

.. function:: modelform_factory(model, form=ModelForm, fields=None, exclude=None, formfield_callback=None,  widgets=None)

    Returns a :class:`~django.forms.ModelForm` class for the given ``model``.
    You can optionally pass a ``form`` argument to use as a starting point for
    constructing the ``ModelForm``.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned fields.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned fields, even if they are listed
    in the ``fields`` argument.

    ``widgets`` is a dictionary of model field names mapped to a widget.

    ``formfield_callback`` is a callable that takes a model field and returns
    a form field.

    See :ref:`modelforms-factory` for example usage.

.. function:: modelformset_factory(model, form=ModelForm, formfield_callback=None, formset=BaseModelFormSet, extra=1, can_delete=False, can_order=False, max_num=None, fields=None, exclude=None)

    Returns a ``FormSet`` class for the given ``model`` class.

    Arguments ``model``, ``form``, ``fields``, ``exclude``, and
    ``formfield_callback`` are all passed through to
    :func:`~django.forms.models.modelform_factory`.

    Arguments ``formset``, ``extra``, ``max_num``, ``can_order``, and
    ``can_delete`` are passed through to ``formset_factory``. See
    :ref:`formsets` for details.

    See :ref:`model-formsets` for example usage.

.. function:: inlineformset_factory(parent_model, model, form=ModelForm, formset=BaseInlineFormSet, fk_name=None, fields=None, exclude=None, extra=3, can_order=False, can_delete=True, max_num=None, formfield_callback=None)

    Returns an ``InlineFormSet`` using :func:`modelformset_factory` with
    defaults of ``formset=BaseInlineFormSet``, ``can_delete=True``, and
    ``extra=3``.

    If your model has more than one :class:`~django.db.models.ForeignKey` to
    the ``parent_model``, you must specify a ``fk_name``.

    See :ref:`inline-formsets` for example usage.
