# Django

## Overview

Django is a high‑level Python web framework that encourages rapid development and clean, pragmatic design. It provides a batteries‑included set of components for building robust, secure, and scalable web applications, including an ORM, templating engine, routing, authentication, admin interface, and more.

The source code lives in the `django/` Python package. Core sub‑packages include:

- **django.apps** – Application registry and configuration utilities.
- **django.conf** – Settings handling and global defaults.
- **django.__main__** – Entry point for the `python -m django` command.

For detailed documentation, see the `docs/` directory or the online docs at https://docs.djangoproject.com/en/stable/.

---

## Installation

Django is distributed on PyPI and can be installed with `pip`:

```bash
python -m pip install Django
```

You can also install the latest development version directly from the repository:

```bash
git clone https://github.com/django/django.git
cd django
python -m pip install -e .
```

> **Note**: The editable install (`-e`) points the installed package to the checkout, allowing you to modify the code and immediately see the changes.

---

## Quick Start / Usage

Below is a minimal example that demonstrates how to create a new Django project and run the development server.

1. **Create a project**
   ```bash
   django-admin startproject mysite
   cd mysite
   ```

2. **Apply migrations** (sets up the default database tables)
   ```bash
   python manage.py migrate
   ```

3. **Start the development server**
   ```bash
   python manage.py runserver
   ```

   Visit `http://127.0.0.1:8000/` in your browser to see the default welcome page.

### Running Django as a module

The repository includes a `__main__.py` that enables the following command, useful for debugging or tooling:

```bash
python -m django --version
```

This prints the currently installed Django version.

---

## Contributing

We welcome contributions! Please read the following resources before getting started:

- **Contributing guide** – https://docs.djangoproject.com/en/dev/internals/contributing/
- **Code of conduct** – https://www.djangoproject.com/community/committers/
- **Development documentation** – located under `docs/` (see `docs/internals/` for architecture details).

### Typical workflow

1. Fork the repository and clone your fork.
2. Create a virtual environment and install the development dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -e .[test]
   ```
3. Run the test suite to ensure everything works:
   ```bash
   ./runtests.py
   ```
4. Make your changes, add tests, and ensure all tests pass.
5. Submit a pull request targeting the `main` branch.

### Reporting issues

If you encounter a bug in the documentation or the code, please open a ticket at https://code.djangoproject.com/newticket.

---

## Community & Support

- **Discord** – https://chat.djangoproject.com
- **Forum** – https://forum.djangoproject.com/
- **Mailing lists** – https://www.djangoproject.com/community/#mailing-lists

---

## License

Django is released under the BSD license. See the `LICENSE` file for full details.
