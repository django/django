======================================
JavaScript customizations in the admin
======================================

.. _admin-javascript-inline-form-events:

Inline form events
==================

You may want to execute some JavaScript when an inline form is added or removed
in the admin change form. The ``formset:added`` and ``formset:removed`` events
allow this. ``event.detail.formsetName`` is the formset the row belongs to.
For the ``formset:added`` event, ``event.target`` is the newly added row.

In your custom ``change_form.html`` template, extend the
``admin_change_form_document_ready`` block and add the event listener code:

.. code-block:: html+django

    {% extends 'admin/change_form.html' %}
    {% load static %}

    {% block admin_change_form_document_ready %}
    {{ block.super }}
    <script src="{% static 'app/formset_handlers.js' %}"></script>
    {% endblock %}

.. code-block:: javascript
    :caption: ``app/static/app/formset_handlers.js``

    document.addEventListener('formset:added', (event) => {
        if (event.detail.formsetName == 'author_set') {
            // Do something
        }
    });
    document.addEventListener('formset:removed', (event) => {
        // Row removed
    });

Two points to keep in mind:

* The JavaScript code must go in a template block if you are inheriting
  ``admin/change_form.html`` or it won't be rendered in the final HTML.
* ``{{ block.super }}`` is added because Django's
  ``admin_change_form_document_ready`` block contains JavaScript code to handle
  various operations in the change form and we need that to be rendered too.

Supporting versions of Django older than 4.1
--------------------------------------------

If your event listener still has to support older versions of Django you have
to use jQuery to register your event listener. jQuery handles JavaScript events
but the reverse isn't true.

You could check for the presence of ``event.detail.formsetName`` and fall back
to the old listener signature as follows:

.. code-block:: javascript

    function handleFormsetAdded(row, formsetName) {
        // Do something
    }

    $(document).on('formset:added', (event, $row, formsetName) => {
        if (event.detail && event.detail.formsetName) {
            // Django >= 4.1
            handleFormsetAdded(event.target, event.detail.formsetName)
        } else {
            // Django < 4.1, use $row and formsetName
            handleFormsetAdded($row.get(0), formsetName)
        }
    })
