import ez_setup # From http://peak.telecommunity.com/DevCenter/setuptools
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(
    name = "Django",
    version = "0.95",
    url = 'http://www.djangoproject.com/',
    author = 'Lawrence Journal-World',
    author_email = 'holovaty@gmail.com',
    description = 'A high-level Python Web framework that encourages rapid development and clean, pragmatic design.',
    license = 'BSD',
    packages = find_packages(exclude=['examples', 'examples.*']),
    package_data = {
        '': ['*.TXT'],
        'django.conf': ['locale/*/LC_MESSAGES/*'],
        'django.contrib.admin': ['templates/admin/*.html',
                                 'templates/admin_doc/*.html',
                                 'templates/registration/*.html',
                                 'templates/widget/*.html',
                                 'media/css/*.css',
                                 'media/img/admin/*.gif',
                                 'media/img/admin/*.png',
                                 'media/js/*.js',
                                 'media/js/admin/*js'],
        'django.contrib.comments': ['templates/comments/*.html'],
    },
    scripts = ['django/bin/django-admin.py'],
    zip_safe = False,
)
