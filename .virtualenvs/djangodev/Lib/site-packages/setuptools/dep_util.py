from ._distutils import _modified
from .warnings import SetuptoolsDeprecationWarning


def __getattr__(name):
    if name not in ['newer_group', 'newer_pairwise_group']:
        raise AttributeError(name)
    SetuptoolsDeprecationWarning.emit(
        "dep_util is Deprecated. Use functions from setuptools.modified instead.",
        "Please use `setuptools.modified` instead of `setuptools.dep_util`.",
        see_url="https://github.com/pypa/setuptools/pull/4069",
        due_date=(2024, 5, 21),
        # Warning added in v69.0.0 on 2023/11/20,
        # See https://github.com/pypa/setuptools/discussions/4128
    )
    return getattr(_modified, name)
