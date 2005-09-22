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
    package_data = {
        'django.conf': ['admin_templates/*.html', 'admin_templates/doc/*.html',
                        'admin_templates/registration/*.html',
                        'admin_media/css/*.css', 'admin_media/img/admin/*.gif',
                        'admin_media/img/admin/*.png', 'admin_media/js/*.js',
                        'admin_media/js/admin/*js'],
    },
    scripts = ['django/bin/django-admin.py'],
    zip_safe = False,
)
