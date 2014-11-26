import glob
import os
import subprocess
import sys

from setuptools import Command, setup, find_packages
from setuptools.command.sdist import sdist as _sdist
from distutils import log
from distutils.sysconfig import get_python_lib


class CompileMessagesCommand(Command):
    """
    Ensure all .po files are properly compiled into .mo files.
    """
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        log.info("Checking that .po files are compiled...")
        locale_dirs = [os.path.join('django', 'conf', 'locale')] + glob.glob('django/contrib/*/locale')
        for locale_dir in locale_dirs:
            po_files = glob.glob('%s/*/LC_MESSAGES/*.po' % locale_dir)
            for po_file in po_files:
                mo_file = '%s.mo' % po_file[:-3]
                subprocess.check_call(["msgfmt", "-o", mo_file, po_file])


class sdist(_sdist):
    sub_commands = _sdist.sub_commands + [('build_mo', None)]


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
    },
    cmdclass={
        'build_mo': CompileMessagesCommand,
        'sdist': sdist,
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
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
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
