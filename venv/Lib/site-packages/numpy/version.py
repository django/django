
"""
Module to expose more detailed version info for the installed `numpy`
"""
version = "2.4.2"
__version__ = version
full_version = version

git_revision = "c81c49f77451340651a751e76bca607d85e4fd55"
release = 'dev' not in version and '+' not in version
short_version = version.split("+")[0]
