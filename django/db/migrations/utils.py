import re

COMPILED_REGEX_TYPE = type(re.compile(''))


class RegexObject(object):
    def __init__(self, obj):
        self.pattern = obj.pattern
        self.flags = obj.flags

    def __eq__(self, other):
        return self.pattern == other.pattern and self.flags == other.flags
