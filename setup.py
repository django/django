import os
import sys
from distutils.sysconfig import get_python_lib

from setuptools import find_packages, setup

# Warn if we are installing over top of an existing installation. This can
# cause issues where files that were deleted from a more recent Django are
# still present in site-packages. See #18115.
overlay_warning = False
if "install" in sys.argv:
    lib_paths = [get_python_lib()]
    if lib_paths[0].startswith("/usr/lib/"):
        # We have to try also with an explicit prefix of /usr/local in order to
        # catch Debian's custom user site-packages directory.
        lib_paths.append(get_python_lib(prefix="/usr/local"))
    for lib_path in lib_paths:
        existing_path = os.path.abspath(os.path.join(lib_path, "django"))
        if os.path.exists(existing_path):
            # We note the need for the warning here, but present it after the
            # command is run, so it's more likely to be seen.
            overlay_warning = True
            break


EXCLUDE_FROM_PACKAGES = ['django.conf.project_template',
                         'django.conf.app_template',
                         'django.bin']


# Dynamically calculate the version based on django.VERSION.
version = __import__('django').get_version()


setup(
    name='Django',
    version=version,
    url='http://www.djangoproject.com/',
    author='Django Software Foundation',
    author_email='foundation@djangoproject.com',
    description=('A high-level Python Web framework that encourages '
                 'rapid development and clean, pragmatic design.'),
    license='BSD',
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    include_package_data=True,
    scripts=['django/bin/django-admin.py'],
    entry_points={'console_scripts': [
        'django-admin = django.core.management:execute_from_command_line',
    ]},
    extras_require={
        "bcrypt": ["bcrypt"],
        "argon2": ["argon2-cffi >= 16.1.0"],
    },
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)


if overlay_warning:
    sys.stderr.write("""

========
WARNING!
========

You have just installed Django over top of an existing
installation, without removing it first. Because of this,
your install may now include extraneous files from a
previous version that have since been removed from
Django. This is known to cause a variety of problems. You
should manually remove the

%(existing_path)s

directory and re-install Django.

""" % {"existing_path": existing_path})
