from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES
import os
import sys

def fullsplit(path, result=None):
    """
    Split a pathname into components (the opposite of os.path.join) in a
    platform-neutral way.
    """
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return fullsplit(head, [tail] + result)

# Tell distutils to put the data_files in platform-specific installation
# locations. See here for an explanation:
# http://groups.google.com/group/comp.lang.python/browse_thread/thread/35ec7b2fed36eaec/2105ee4d9e8042cb
for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

# Compile the list of packages available, because distutils doesn't have
# an easy way to do this.
packages, data_files = [], []
root_dir = os.path.dirname(__file__)
django_dir = os.path.join(root_dir, 'django')
pieces = fullsplit(root_dir)
if pieces[-1] == '':
    len_root_dir = len(pieces)- 1
else:
    len_root_dir = len(pieces)

for dirpath, dirnames, filenames in os.walk(django_dir):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'): del dirnames[i]
    if '__init__.py' in filenames:
        packages.append('.'.join(fullsplit(dirpath)[len_root_dir:]))
    elif filenames:
        data_files.append([dirpath, [os.path.join(dirpath, f) for f in filenames]])

# Dynamically calculate the version based on django.VERSION.
version_tuple = __import__('django').VERSION
if version_tuple[2] is not None:
    version = "%d.%d_%s" % version_tuple
else:
    version = "%d.%d" % version_tuple[:2]

setup(
    name = "Django",
    version = version,
    url = 'http://www.djangoproject.com/',
    author = 'Lawrence Journal-World',
    author_email = 'holovaty@gmail.com',
    description = 'A high-level Python Web framework that encourages rapid development and clean, pragmatic design.',
    packages = packages,
    data_files = data_files,
    scripts = ['django/bin/django-admin.py'],
)
