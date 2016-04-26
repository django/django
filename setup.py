from setuptools import find_packages, setup
from channels import __version__

setup(
    name='channels',
    version=__version__,
    url='http://github.com/andrewgodwin/channels',
    author='Andrew Godwin',
    author_email='andrew@aeracode.org',
    description="Brings event-driven capabilities to Django with a channel system. Django 1.8 and up only.",
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Django>=1.8',
        'asgiref>=0.10',
        'daphne>=0.11',
    ]
)
