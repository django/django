import time as time_provider


class Restriction:
    JSON_SEPARATOR = "@"

    def __init__(self, name):
        self.type = name

    def is_expired(self):
        """
        indicates whether given message should be removed
        """
        raise NotImplementedError()

    def on_display(self):
        """
        called when iterated - does nothing by default
        """
        pass

    def to_json(self):
        """
        returns json representation of restriction
        """
        raise NotImplementedError

    @classmethod
    def from_json_param(cls, *args):
        """
        returns restriction on the basis of data encoded in json
        """
        raise NotImplementedError

    def __cmp__(self, other):
        if self.__eq__(other):
            return 0
        return -1


class TimeRestriction(Restriction):
    JSON_TYPE_CODE = "t"

    def __init__(self, seconds):
        """
        seconds - expiration time since now
        """
        Restriction.__init__(self, "time")
        created = time_provider.time()
        self.expires = created + int(seconds)

    def set_expirity_time(self, expiration_time):
        """
        Sets expilcity expiration time
        """
        self.expires = int(expiration_time)

    def is_expired(self):
        return self.expires < time_provider.time()

    def __eq__(self, other):
        return self.type == other.type and not bool(self.expires ^ other.expires)

    def __hash__(self):
        return self.expires

    def to_json(self):
        return "%s%s%s" % (self.JSON_TYPE_CODE, self.JSON_SEPARATOR, self.expires)

    @classmethod
    def from_json_param(cls, expirity_time):
        ret = TimeRestriction(0)
        ret.set_expirity_time(expirity_time)
        return ret


class AmountRestriction(Restriction):
    JSON_TYPE_CODE = "a"

    def __init__(self, amount):
        assert int(amount) >= 0
        Restriction.__init__(self, "amount")
        self.can_be_shown = int(amount)

    def on_display(self):
        self.can_be_shown -= 1

    def is_expired(self):
        return int(self.can_be_shown) <= 0

    def __eq__(self, other):
        return self.type == other.type and not bool(
            self.can_be_shown ^ other.can_be_shown
        )

    def __hash__(self):
        return self.can_be_shown

    def __repr__(self):
        return self.to_json()

    def to_json(self):
        return "%s%s%s" % (self.JSON_TYPE_CODE, self.JSON_SEPARATOR, self.can_be_shown)

    @classmethod
    def from_json_param(cls, amount):
        return AmountRestriction(amount)
