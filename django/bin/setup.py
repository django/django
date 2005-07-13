"""
Usage:

python setup.py bdist
python setup.py sdist
"""

from distutils.core import setup
import os

# Whether to include the .py files, rather than just .pyc's. Doesn't do anything yet.
INCLUDE_SOURCE = True

# Determines which apps are bundled with the distribution.
INSTALLED_APPS = ('auth', 'categories', 'comments', 'core', 'media', 'news', 'polls', 'registration', 'search', 'sms', 'staff')

# First, lump together all the generic, core packages that need to be included.
packages = [
    'django',
    'django.core',
    'django.templatetags',
    'django.utils',
    'django.views',
]
for a in INSTALLED_APPS:
    for dirname in ('parts', 'templatetags', 'views'):
        if os.path.exists('django/%s/%s/' % (dirname, a)):
            packages.append('django.%s.%s' % (dirname, a))

# Next, add individual modules.
py_modules = [
    'django.cron.daily_cleanup',
    'django.cron.search_indexer',
]
py_modules += ['django.models.%s' % a for a in INSTALLED_APPS]

setup(
    name = 'django',
    version = '1.0',
    packages = packages,
    py_modules = py_modules,
    url = 'http://www.ljworld.com/',
    author = 'World Online',
    author_email = 'cms-support@ljworld.com',
)
