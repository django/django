import builtins
import reprlib


class DjangoRepr(reprlib.Repr):

    def config(self, limit):
        """Sets maximum print length for all data structures using the given value"""
        self.limit = limit
        for attr in dir(self):
            if attr.startswith("max") and attr != "maxlevel":
                setattr(self, attr, limit)

    def repr_str(self, x, level):
        return "'%s'" % (x[: self.maxstring] + self.gen_trim_msg(len(x)))

    def repr_instance(self, x, level):
        s = builtins.repr(x)
        if len(s) > self.maxother:
            return s[: self.maxother] + self.gen_trim_msg(len(s))
        return s

    def gen_trim_msg(self, length):
        if length <= self.limit:
            return ""
        return "...<trimmed %d bytes string>" % (length - self.limit)
