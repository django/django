====================
Django Contact App
====================

The ``contact`` app is a simple Django contrib application that provides a basic
contact form functionality for collecting user inquiries.

Quick start
-----------

1. Add "django.contrib.contact" to your INSTALLED_APPS setting::

    INSTALLED_APPS = [
        ...
        'django.contrib.contact',
    ]

2. Include the contact URLconf in your project's urls.py::

    from django.urls import include, path

    urlpatterns = [
        ...
        path('contact/', include('django.contrib.contact.urls')),
    ]

3. Run migrations to create the contact models::

    python manage.py migrate

4. Visit http://127.0.0.1:8000/contact/ to access the contact form.

Features
--------

* Simple contact form with name, email, and message fields
* Form validation for all required fields
* Email field validation
* Thank you page after successful submission
* Admin interface to view submitted messages (read-only)
* Messages are stored in the database with timestamp
* Full i18n/l10n support

Models
------

ContactMessage
~~~~~~~~~~~~~~

Stores contact form submissions with the following fields:

* ``name`` - CharField (max 200 characters)
* ``email`` - EmailField
* ``message`` - TextField
* ``created_at`` - DateTimeField (auto-populated)

URLs
----

The app provides two URL patterns:

* ``/`` - Contact form (name: ``contact:contact``)
* ``/thank-you/`` - Thank you page (name: ``contact:thank_you``)

Templates
---------

The app includes basic HTML templates that can be overridden:

* ``contact/contact_form.html`` - The contact form page
* ``contact/thank_you.html`` - The thank you page

To customize these templates, create your own templates in your project's
template directory with the same path structure.

Admin Interface
---------------

Contact messages can be viewed through the Django admin interface.
The admin is configured as read-only - messages cannot be added or edited
through the admin, only viewed and deleted.

Testing
-------

Run the contact app tests with::

    python tests/runtests.py contact_tests
