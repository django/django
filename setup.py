from setuptools import find_packages, setup

setup(
    name='django-channels',
    version="0.1",
    url='http://github.com/andrewgodwin/django-channels',
    author='Andrew Godwin',
    author_email='andrew@aeracode.org',
    description="Brings event-driven capabilities to Django with a channel system. Django 1.8 and up only.",
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
)
