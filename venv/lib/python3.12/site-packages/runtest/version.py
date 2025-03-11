from collections import namedtuple

__version__ = "2.3.4"

version_info = namedtuple("version_info", ["major", "minor", "micro", "releaselevel"])

major_minor_micro = __version__.split("-")[0]

s = major_minor_micro.split(".")

version_info.major = int(s[0])
version_info.minor = int(s[1])
version_info.micro = int(s[2])

version_info.releaselevel = __version__[len(major_minor_micro) + 1 :]
