======
Django
======

Django is a high-level Python web framework that encourages rapid development
and clean, pragmatic design. Thanks for checking it out.

All documentation is in the "``docs``" directory and online at
https://docs.djangoproject.com/en/stable/. If you're just getting started,
here's how we recommend you read the docs:

* First, read ``docs/intro/install.txt`` for instructions on installing Django.

* Next, work through the tutorials in order (``docs/intro/tutorial01.txt``,
  ``docs/intro/tutorial02.txt``, etc.).

* If you want to set up an actual deployment server, read
  ``docs/howto/deployment/index.txt`` for instructions.

* You'll probably want to read through the topical guides (in ``docs/topics``)
  next; from there you can jump to the HOWTOs (in ``docs/howto``) for specific
  problems, and check out the reference (``docs/ref``) for gory details.

* See ``docs/README`` for instructions on building an HTML version of the docs.

Docs are updated rigorously. If you find any problems in the docs, or think
they should be clarified in any way, please take 30 seconds to fill out a
ticket here: https://code.djangoproject.com/newticket

To get more help:

* Join the ``#django`` channel on ``irc.libera.chat``. Lots of helpful people
  hang out there. `Webchat is available <https://web.libera.chat/#django>`_.

* Join the django-users mailing list, or read the archives, at
  https://groups.google.com/group/django-users.

* Join the `Django Discord community <https://discord.gg/xcRH6mN4fa>`_.

* Join the community on the `Django Forum <https://forum.djangoproject.com/>`_.

To contribute to Django:

* Check out https://docs.djangoproject.com/en/dev/internals/contributing/ for
  information about getting involved.

To run Django's test suite:

* Follow the instructions in the "Unit tests" section of
  ``docs/internals/contributing/writing-code/unit-tests.txt``, published online at
  https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/#running-the-unit-tests

Supporting the Development of Django
====================================

Django's development depends on your contributions.

If you depend on Django, remember to support the Django Software Foundation: https://www.djangoproject.com/fundraising/

Setting up Django on Ubuntu
===========================

Setting up Django on Ubuntu is a straightforward process. Here are the steps to set up Django on a fresh Ubuntu system:

1. Update and Upgrade Ubuntu
   --------------------------

   Open a terminal and make sure your system is up to date by running the following commands:

   .. code-block:: bash

      sudo apt update
      sudo apt upgrade

2. Install Python
   --------------

   Django is a Python web framework, so make sure Python is installed. Most Ubuntu versions come with Python pre-installed. You can check the installed version with:

   .. code-block:: bash

      python3 --version

   If it's not installed, you can install it using:

   .. code-block:: bash

      sudo apt install python3

3. Install pip (Python Package Manager)
   -------------------------------------

   Pip is a package manager for Python. You'll need it to install Django and other Python packages. Install pip using:

   .. code-block:: bash

      sudo apt install python3-pip

4. Install Virtual Environment (Optional but Recommended)
   -----------------------------------------------------

   Using a virtual environment is a good practice to isolate your project's dependencies. You can install the `virtualenv` package with pip:

   .. code-block:: bash

      pip install virtualenv

5. Create a Django Project Directory
   ---------------------------------

   Choose a location for your Django project and create a directory for it. You can do this using the `mkdir` command. For example:

   .. code-block:: bash

      mkdir ~/my_django_project

6. Create a Virtual Environment (Optional but Recommended)
   -------------------------------------------------------

   Inside your project directory, create a virtual environment using `virtualenv`. Navigate to your project directory and run:

   .. code-block:: bash

      cd ~/my_django_project
      virtualenv venv

7. Activate the Virtual Environment (Optional but Recommended)
   ----------------------------------------------------------

   To activate the virtual environment, run the following command:

   .. code-block:: bash

      source venv/bin/activate

   Your terminal prompt should now change to indicate that the virtual environment is active.

8. Install Django
   ---------------

   With your virtual environment active, you can now install Django using pip:

   .. code-block:: bash

      pip install django

9. Create a Django Project
   ------------------------

   Use the following command to create a new Django project. Replace `projectname` with your desired project name:

   .. code-block:: bash

      django-admin startproject projectname

10. Run the Development Server
    ---------------------------

    Change to your project's directory and run the development server using the following commands:

    .. code-block:: bash

      cd projectname
      python manage.py runserver

    Your Django development server should now be running at http://127.0.0.1:8000/. You can access it using a web browser.

11. Access the Django Admin Panel (Optional)
    ----------------------------------------

    You can access the Django admin panel by creating an admin superuser. Run the following command, and follow the prompts to create an admin user:

    .. code-block:: bash

        python manage.py createsuperuser

    You can then access the admin panel at http://127.0.0.1:8000/admin/.

12. Start Building Your Django Project
    -----------------------------------

    You've successfully set up Django on your Ubuntu system. You can now start building your web application by defining models, views, templates, and URL patterns within your Django project.

Remember to deactivate the virtual environment when you're done working on your project by running:

.. code-block:: bash

   deactivate

That's it! You now have Django installed and ready to use on your Ubuntu system.
