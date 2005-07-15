import ez_setup # From http://peak.telecommunity.com/DevCenter/setuptools
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(
    name = "django",
    version = "1.0.0",
    url = 'http://www.djangoproject.com/',
    author = 'Lawrence Journal-World',
    author_email = 'holovaty@gmail.com',
    description = 'A high-level Python Web framework that encourages rapid development and clean, pragmatic design.',
    license = 'BSD',
    packages = find_packages(),
    scripts = ['django/bin/django-admin.py'],
)
