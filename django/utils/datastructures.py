class MergeDict:
    """
    A simple class for creating new "virtual" dictionaries that actualy look
    up values in more than one dictionary, passed in the constructor.
    """
    def __init__(self, *dicts):
        self.dicts = dicts

    def __getitem__(self, key):
        for dict in self.dicts:
            try:
                return dict[key]
            except KeyError:
                pass
        raise KeyError

    def get(self, key, default):
        try:
            return self[key]
        except KeyError:
            return default

    def getlist(self, key):
        for dict in self.dicts:
            try:
                return dict.getlist(key)
            except KeyError:
                pass
        raise KeyError

    def items(self):
        item_list = []
        for dict in self.dicts:
            item_list.extend(dict.items())
        return item_list

    def has_key(self, key):
        for dict in self.dicts:
            if dict.has_key(key):
                return True
        return False

class MultiValueDictKeyError(KeyError):
    pass

class MultiValueDict:
    """
    A dictionary-like class customized to deal with multiple values for the same key.

    >>> d = MultiValueDict({'name': ['Adrian', 'Simon'], 'position': ['Developer']})
    >>> d['name']
    'Simon'
    >>> d.getlist('name')
    ['Adrian', 'Simon']
    >>> d.get('lastname', 'nonexistent')
    'nonexistent'
    >>> d.setlist('lastname', ['Holovaty', 'Willison'])

    This class exists to solve the irritating problem raised by cgi.parse_qs,
    which returns a list for every key, even though most Web forms submit
    single name-value pairs.
    """
    def __init__(self, key_to_list_mapping=None):
        self.data = key_to_list_mapping or {}

    def __repr__(self):
        return repr(self.data)

    def __getitem__(self, key):
        "Returns the data value for this key; raises KeyError if not found"
        if self.data.has_key(key):
            try:
                return self.data[key][-1] # in case of duplicates, use last value ([-1])
            except IndexError:
                return []
        raise MultiValueDictKeyError, "Key '%s' not found in MultiValueDict %s" % (key, self.data)

    def __setitem__(self, key, value):
        self.data[key] = [value]

    def __len__(self):
        return len(self.data)

    def __contains__(self, key):
        return self.data.has_key(key)

    def get(self, key, default):
        "Returns the default value if the requested data doesn't exist"
        try:
            val = self[key]
        except (KeyError, IndexError):
            return default
        if val == []:
            return default
        return val

    def getlist(self, key):
        "Returns an empty list if the requested data doesn't exist"
        try:
            return self.data[key]
        except KeyError:
            return []

    def setlist(self, key, list_):
        self.data[key] = list_

    def appendlist(self, key, item):
        "Appends an item to the internal list associated with key"
        try:
            self.data[key].append(item)
        except KeyError:
            self.data[key] = [item]

    def has_key(self, key):
        return self.data.has_key(key)

    def items(self):
        # we don't just return self.data.items() here, because we want to use
        # self.__getitem__() to access the values as *strings*, not lists
        return [(key, self[key]) for key in self.data.keys()]

    def keys(self):
        return self.data.keys()

    def update(self, other_dict):
        if isinstance(other_dict, MultiValueDict):
            for key, value_list in other_dict.data.items():
                self.data.setdefault(key, []).extend(value_list)
        elif type(other_dict) == type({}):
            for key, value in other_dict.items():
                self.data.setdefault(key, []).append(value)
        else:
            raise ValueError, "MultiValueDict.update() takes either a MultiValueDict or dictionary"

    def copy(self):
        "Returns a copy of this object"
        import copy
        cp = copy.deepcopy(self)
        return cp

class DotExpandedDict(dict):
    """
    A special dictionary constructor that takes a dictionary in which the keys
    may contain dots to specify inner dictionaries. It's confusing, but this
    example should make sense.

    >>> d = DotExpandedDict({'person.1.firstname': ['Simon'],
            'person.1.lastname': ['Willison'],
            'person.2.firstname': ['Adrian'],
            'person.2.lastname': ['Holovaty']})
    >>> d
    {'person': {'1': {'lastname': ['Willison'], 'firstname': ['Simon']},
    '2': {'lastname': ['Holovaty'], 'firstname': ['Adrian']}}}
    >>> d['person']
    {'1': {'firstname': ['Simon'], 'lastname': ['Willison'],
    '2': {'firstname': ['Adrian'], 'lastname': ['Holovaty']}
    >>> d['person']['1']
    {'firstname': ['Simon'], 'lastname': ['Willison']}

    # Gotcha: Results are unpredictable if the dots are "uneven":
    >>> DotExpandedDict({'c.1': 2, 'c.2': 3, 'c': 1})
    >>> {'c': 1}
    """
    def __init__(self, key_to_list_mapping):
        for k, v in key_to_list_mapping.items():
            current = self
            bits = k.split('.')
            for bit in bits[:-1]:
                current = current.setdefault(bit, {})
            # Now assign value to current position
            try:
                current[bits[-1]] = v
            except TypeError: # Special-case if current isn't a dict.
                current = {bits[-1]: v}
