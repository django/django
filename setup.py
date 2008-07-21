from distutils.core import setup
from distutils.command.install_data import install_data
from distutils.command.install import INSTALL_SCHEMES
import os
import sys

class osx_install_data(install_data):
    # On MacOS the plattform specific lib dir is /System/Library/Framework/Python/.../
    # which is wrong. Python 2.5 supplied with MacOS 10.5 has an Aplle specific fix
    # for this in distutils.command.install_data#306 It fixes install_lib but not
    # install_data, which is why we roll our own install_data class.

    def finalize_options (self):
        # By the time finalize_options is called install.install_lib is set to the
        # fixed directory. so we set the installdir for to install_lib, the
        # install_data class uses ('install_data', 'install_dir') instead.
        self.set_undefined_options('install', ('install_lib', 'install_dir'))
        install_data.finalize_options(self)

if sys.platform == "darwin": 
    cmdclasses = {'install_data': osx_install_data } 
else: 
    cmdclasses = {'install_data': install_data } 

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
if root_dir != '':
    os.chdir(root_dir)
django_dir = 'django'

for dirpath, dirnames, filenames in os.walk(django_dir):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'): del dirnames[i]
    if '__init__.py' in filenames:
        packages.append('.'.join(fullsplit(dirpath)))
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
    author = 'Django Software Foundation',
    author_email = 'foundation@djangoproject.com',
    description = 'A high-level Python Web framework that encourages rapid development and clean, pragmatic design.',
    packages = packages,
    cmdclass = cmdclasses,
    data_files = data_files,
    scripts = ['django/bin/django-admin.py'],
)
