from setuptools import setup, find_packages

setup(
    name="Django",
    version="3.2.4",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # List all dependencies
    ],
    entry_points={
        "console_scripts": [
            # List console scripts if any
        ],
    },
)
