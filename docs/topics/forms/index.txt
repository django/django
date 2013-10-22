==================
Working with forms
==================

.. admonition:: About this document

    This document provides an introduction to Django's form handling features.
    For a more detailed look at specific areas of the forms API, see
    :doc:`/ref/forms/api`, :doc:`/ref/forms/fields`, and
    :doc:`/ref/forms/validation`.

.. highlightlang:: html+django

``django.forms`` is Django's form-handling library.

While it is possible to process form submissions just using Django's
:class:`~django.http.HttpRequest` class, using the form library takes care of a
number of common form-related tasks. Using it, you can:

1. Display an HTML form with automatically generated form widgets.
2. Check submitted data against a set of validation rules.
3. Redisplay a form in the case of validation errors.
4. Convert submitted form data to the relevant Python data types.

Overview
========

The library deals with these concepts:

.. glossary::

    Widget
        A class that corresponds to an HTML form widget, e.g.
        ``<input type="text">`` or ``<textarea>``. This handles rendering of the
        widget as HTML.

    Field
        A class that is responsible for doing validation, e.g.
        an ``EmailField`` that makes sure its data is a valid email address.

    Form
        A collection of fields that knows how to validate itself and
        display itself as HTML.

    Form Assets (the ``Media`` class)
        The CSS and JavaScript resources that are required to render a form.

The library is decoupled from the other Django components, such as the database
layer, views and templates. It relies only on Django settings, a couple of
``django.utils`` helper functions and Django's internationalization hooks (but
you're not required to be using internationalization features to use this
library).

Form objects
============

A Form object encapsulates a sequence of form fields and a collection of
validation rules that must be fulfilled in order for the form to be accepted.
Form classes are created as subclasses of ``django.forms.Form`` and
make use of a declarative style that you'll be familiar with if you've used
Django's database models.

For example, consider a form used to implement "contact me" functionality on a
personal Web site:

.. code-block:: python

    from django import forms

    class ContactForm(forms.Form):
        subject = forms.CharField(max_length=100)
        message = forms.CharField()
        sender = forms.EmailField()
        cc_myself = forms.BooleanField(required=False)

A form is composed of ``Field`` objects. In this case, our form has four
fields: ``subject``, ``message``, ``sender`` and ``cc_myself``. ``CharField``,
``EmailField`` and ``BooleanField`` are just three of the available field types;
a full list can be found in :doc:`/ref/forms/fields`.

If your form is going to be used to directly add or edit a Django model, you can
use a :doc:`ModelForm </topics/forms/modelforms>` to avoid duplicating your model
description.

.. _using-a-form-in-a-view:

Using a form in a view
----------------------

The standard pattern for processing a form in a view looks like this:

.. code-block:: python

   from django.shortcuts import render
   from django.http import HttpResponseRedirect

   def contact(request):
       if request.method == 'POST': # If the form has been submitted...
           form = ContactForm(request.POST) # A form bound to the POST data
           if form.is_valid(): # All validation rules pass
               # Process the data in form.cleaned_data
               # ...
               return HttpResponseRedirect('/thanks/') # Redirect after POST
       else:
           form = ContactForm() # An unbound form

       return render(request, 'contact.html', {
           'form': form,
       })


There are three possible code paths here:

+------------------+---------------+-----------------------------------------+
| Form submitted?  | Data?         | What occurs                             |
+==================+===============+=========================================+
| Unsubmitted      | None yet      | Template gets passed unbound instance   |
|                  |               | of ContactForm.                         |
+------------------+---------------+-----------------------------------------+
| Submitted        | Invalid data  | Template gets passed bound instance     |
|                  |               | of ContactForm.                         |
+------------------+---------------+-----------------------------------------+
| Submitted        | Valid data    | Valid data is processed. Redirect to a  |
|                  |               | "thanks" page.                          |
+------------------+---------------+-----------------------------------------+

The distinction between :ref:`ref-forms-api-bound-unbound` is important:

* An unbound form has no data associated with it. When rendered to the user,
  it will be empty or will contain default values.

* A bound form has submitted data, and hence can be used to tell if that data
  is valid. If an invalid bound form is rendered, it can include inline error
  messages telling the user what data to correct.

Handling file uploads with a form
---------------------------------

To see how to handle file uploads with your form, see
:ref:`binding-uploaded-files`.

Processing the data from a form
-------------------------------

Once ``is_valid()`` returns ``True``, the successfully validated form data
will be in the ``form.cleaned_data`` dictionary. This data will have been
converted nicely into Python types for you.

.. note::

   You can still access the unvalidated data directly from ``request.POST`` at
   this point, but the validated data is better.

In the above example, ``cc_myself`` will be a boolean value. Likewise, fields
such as ``IntegerField`` and ``FloatField`` convert values to a Python int and
float respectively.

Read-only fields are not available in ``form.cleaned_data`` (and setting
a value in a custom ``clean()`` method won't have any effect). These
fields are displayed as text rather than as input elements, and thus are not
posted back to the server.

Extending the earlier example, here's how the form data could be processed:

.. code-block:: python

    if form.is_valid():
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']
        sender = form.cleaned_data['sender']
        cc_myself = form.cleaned_data['cc_myself']

        recipients = ['info@example.com']
        if cc_myself:
            recipients.append(sender)

        from django.core.mail import send_mail
        send_mail(subject, message, sender, recipients)
        return HttpResponseRedirect('/thanks/') # Redirect after POST

.. tip::

   For more on sending email from Django, see :doc:`/topics/email`.

Displaying a form using a template
----------------------------------

Forms are designed to work with the Django template language. In the above
example, we passed our ``ContactForm`` instance to the template using the
context variable ``form``. Here's a simple example template::

    <form action="/contact/" method="post">{% csrf_token %}
    {{ form.as_p }}
    <input type="submit" value="Submit" />
    </form>

The form only outputs its own fields; it is up to you to provide the surrounding
``<form>`` tags and the submit button.

If your form includes uploaded files, be sure to include
``enctype="multipart/form-data"`` in the ``form`` element. If you wish to write
a generic template that will work whether or not the form has files, you can
use the :meth:`~django.forms.Form.is_multipart` attribute on the form::

    <form action="/contact/" method="post"
        {% if form.is_multipart %}enctype="multipart/form-data"{% endif %}>

.. admonition:: Forms and Cross Site Request Forgery protection

   Django ships with an easy-to-use :doc:`protection against Cross Site Request
   Forgeries </ref/contrib/csrf>`. When submitting a form via POST with
   CSRF protection enabled you must use the :ttag:`csrf_token` template tag
   as in the preceding example. However, since CSRF protection is not
   directly tied to forms in templates, this tag is omitted from the
   following examples in this document.

``form.as_p`` will output the form with each form field and accompanying label
wrapped in a paragraph. Here's the output for our example template::

   <form action="/contact/" method="post">
   <p><label for="id_subject">Subject:</label>
       <input id="id_subject" type="text" name="subject" maxlength="100" /></p>
   <p><label for="id_message">Message:</label>
       <input type="text" name="message" id="id_message" /></p>
   <p><label for="id_sender">Sender:</label>
       <input type="email" name="sender" id="id_sender" /></p>
   <p><label for="id_cc_myself">Cc myself:</label>
       <input type="checkbox" name="cc_myself" id="id_cc_myself" /></p>
   <input type="submit" value="Submit" />
   </form>

Note that each form field has an ID attribute set to ``id_<field-name>``, which
is referenced by the accompanying label tag. This is important for ensuring
forms are accessible to assistive technology such as screen reader software. You
can also :ref:`customize the way in which labels and ids are generated
<ref-forms-api-configuring-label>`.

You can also use ``form.as_table`` to output table rows (you'll need to provide
your own ``<table>`` tags) and ``form.as_ul`` to output list items.

Customizing the form template
-----------------------------

If the default generated HTML is not to your taste, you can completely customize
the way a form is presented using the Django template language. Extending the
above example::

    <form action="/contact/" method="post">
        {{ form.non_field_errors }}
        <div class="fieldWrapper">
            {{ form.subject.errors }}
            <label for="id_subject">Email subject:</label>
            {{ form.subject }}
        </div>
        <div class="fieldWrapper">
            {{ form.message.errors }}
            <label for="id_message">Your message:</label>
            {{ form.message }}
        </div>
        <div class="fieldWrapper">
            {{ form.sender.errors }}
            <label for="id_sender">Your email address:</label>
            {{ form.sender }}
        </div>
        <div class="fieldWrapper">
            {{ form.cc_myself.errors }}
            <label for="id_cc_myself">CC yourself?</label>
            {{ form.cc_myself }}
        </div>
        <p><input type="submit" value="Send message" /></p>
    </form>

Each named form-field can be output to the template using
``{{ form.name_of_field }}``, which will produce the HTML needed to display the
form widget. Using ``{{ form.name_of_field.errors }}`` displays a list of form
errors, rendered as an unordered list. This might look like::

   <ul class="errorlist">
       <li>Sender is required.</li>
   </ul>

The list has a CSS class of ``errorlist`` to allow you to style its appearance.
If you wish to further customize the display of errors you can do so by looping
over them::

    {% if form.subject.errors %}
        <ol>
        {% for error in form.subject.errors %}
            <li><strong>{{ error|escape }}</strong></li>
        {% endfor %}
        </ol>
    {% endif %}

Looping over the form's fields
------------------------------

If you're using the same HTML for each of your form fields, you can reduce
duplicate code by looping through each field in turn using a ``{% for %}``
loop::

    <form action="/contact/" method="post">
        {% for field in form %}
            <div class="fieldWrapper">
                {{ field.errors }}
                {{ field.label_tag }} {{ field }}
            </div>
        {% endfor %}
        <p><input type="submit" value="Send message" /></p>
    </form>

Within this loop, ``{{ field }}`` is an instance of
:class:`~django.forms.BoundField`. ``BoundField`` also has the following
attributes, which can be useful in your templates:

``{{ field.label }}``
    The label of the field, e.g. ``Email address``.

``{{ field.label_tag }}``
    The field's label wrapped in the appropriate HTML ``<label>`` tag.

    .. versionchanged:: 1.6

        This includes the form's :attr:`~django.forms.Form.label_suffix`. For
        example, the default ``label_suffix`` is a colon::

            <label for="id_email">Email address:</label>

``{{ field.id_for_label }}``
    The ID that will be used for this field (``id_email`` in the example
    above). You may want to use this in lieu of ``label_tag`` if you are
    constructing the label manually. It's also useful, for example, if you have
    some inline JavaScript and want to avoid hardcoding the field's ID.

``{{ field.value }}``
    The value of the field. e.g ``someone@example.com``

``{{ field.html_name }}``
    The name of the field that will be used in the input element's name
    field. This takes the form prefix into account, if it has been set.

``{{ field.help_text }}``
    Any help text that has been associated with the field.

``{{ field.errors }}``
    Outputs a ``<ul class="errorlist">`` containing any validation errors
    corresponding to this field. You can customize the presentation of
    the errors with a ``{% for error in field.errors %}`` loop. In this
    case, each object in the loop is a simple string containing the error
    message.

``{{ field.is_hidden }}``
    This attribute is ``True`` if the form field is a hidden field and
    ``False`` otherwise. It's not particularly useful as a template
    variable, but could be useful in conditional tests such as::

        {% if field.is_hidden %}
           {# Do something special #}
        {% endif %}

``{{ field.field }}``
    The :class:`~django.forms.Field` instance from the form class that
    this :class:`~django.forms.BoundField` wraps. You can use it to access
    :class:`~django.forms.Field` attributes , e.g.
    ``{{ char_field.field.max_length }}``.

Looping over hidden and visible fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're manually laying out a form in a template, as opposed to relying on
Django's default form layout, you might want to treat ``<input type="hidden">``
fields differently than non-hidden fields. For example, because hidden fields
don't display anything, putting error messages "next to" the field could cause
confusion for your users -- so errors for those fields should be handled
differently.

Django provides two methods on a form that allow you to loop over the hidden
and visible fields independently: ``hidden_fields()`` and
``visible_fields()``. Here's a modification of an earlier example that uses
these two methods::

    <form action="/contact/" method="post">
        {# Include the hidden fields #}
        {% for hidden in form.hidden_fields %}
        {{ hidden }}
        {% endfor %}
        {# Include the visible fields #}
        {% for field in form.visible_fields %}
            <div class="fieldWrapper">
                {{ field.errors }}
                {{ field.label_tag }} {{ field }}
            </div>
        {% endfor %}
        <p><input type="submit" value="Send message" /></p>
    </form>

This example does not handle any errors in the hidden fields. Usually, an
error in a hidden field is a sign of form tampering, since normal form
interaction won't alter them. However, you could easily insert some error
displays for those form errors, as well.

Reusable form templates
-----------------------

If your site uses the same rendering logic for forms in multiple places, you
can reduce duplication by saving the form's loop in a standalone template and
using the :ttag:`include` tag to reuse it in other templates::

    <form action="/contact/" method="post">
        {% include "form_snippet.html" %}
        <p><input type="submit" value="Send message" /></p>
    </form>

    # In form_snippet.html:

    {% for field in form %}
        <div class="fieldWrapper">
            {{ field.errors }}
            {{ field.label_tag }} {{ field }}
        </div>
    {% endfor %}

If the form object passed to a template has a different name within the
context, you can alias it using the ``with`` argument of the :ttag:`include`
tag::

    <form action="/comments/add/" method="post">
        {% include "form_snippet.html" with form=comment_form %}
        <p><input type="submit" value="Submit comment" /></p>
    </form>

If you find yourself doing this often, you might consider creating a custom
:ref:`inclusion tag<howto-custom-template-tags-inclusion-tags>`.

Further topics
==============

This covers the basics, but forms can do a whole lot more:

.. toctree::
   :maxdepth: 2

   formsets
   modelforms
   media

.. seealso::

    :doc:`The Forms Reference </ref/forms/index>`
        Covers the full API reference, including form fields, form widgets,
        and form and field validation.
