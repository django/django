import reprlib


class DjangoRepr(reprlib.Repr):

    def config(self, limit):
        """Sets maximum print length for all data structures using the given value"""
        for attr in dir(self):
            if attr.startswith("max") and attr != "maxlevel":
                setattr(self, attr, limit)

    def repr_str(self, x, level):
        return x[: self.maxstring]
