from setuptools import find_packages, setup
from channels import __version__

setup(
    name='channels',
    version=__version__,
    url='http://github.com/django/channels',
    author='Django Software Foundation',
    author_email='foundation@djangoproject.com',
    description="Brings async, event-driven capabilities to Django. Django 1.11 and up only.",
    license='BSD',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=[
        'Django>=1.11',
        'asgiref~=2.1',
        'daphne~=2.0',
    ],
    extras_require={
        'tests': [
            'pytest~=3.3',
            "pytest-django~=3.1",
            "pytest-asyncio~=0.8",
            "async_generator~=1.8",
            "async-timeout~=2.0",
            'coverage~=4.4',
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
