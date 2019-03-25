
class Among(object):
    def __init__(self, s, substring_i, result, method=None):
        """
        @ivar s_size search string size
        @ivar s search string
        @ivar substring index to longest matching substring
        @ivar result of the lookup
        @ivar method method to use if substring matches
        """
        self.s_size = len(s)
        self.s = s
        self.substring_i = substring_i
        self.result = result
        self.method = method
