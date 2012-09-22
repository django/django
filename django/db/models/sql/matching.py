import re


def _exact(model, instance_value, value):
    return instance_value == value


def _iexact(model, instance_value, value):
    return instance_value.lower() == value.lower()


def _contains(model, instance_value, value):
    return value in instance_value


def _icontains(model, instance_value, value):
    return value.lower() in instance_value.lower()


def _gt(model, instance_value, value):
    return instance_value > value


def _gte(model, instance_value, value):
    return instance_value >= value


def _lt(model, instance_value, value):
    return instance_value < value


def _lte(model, instance_value, value):
    return instance_value <= value


def _startswith(model, instance_value, value):
    return instance_value.startswith(value)


def _istartswith(model, instance_value, value):
    return instance_value.lower().startswith(value.lower())


def _endswith(model, instance_value, value):
    return instance_value.endswith(value)


def _iendswith(model, instance_value, value):
    return instance_value.lower().endswith(value.lower())


def _in(model, instance_value, value):
    return instance_value in value


def _range(model, instance_value, value):
    # TODO could be more between like
    return value[0] < instance_value < value[1]


def _year(model, instance_value, value):
    return instance_value.year == value


def _month(model, instance_value, value):
    return instance_value.month == value


def _day(model, instance_value, value):
    return instance_value.day == value


def _week_day(model, instance_value, value):
    return instance_value.weekday() == value


def _isnull(model, instance_value, value):
    if value:
        return instance_value is None
    else:
        return instance_value is not None

# This is a special attr/flag to designate that when None is the instance_value
# due to an inability to follow a set of relationships, True should be returned
# for the match, as in most cases, the match would be considered False
_isnull.none_is_true = True


def _search(model, instance_value, value):
    return model._contains(instance_value, instance_value)


def _regex(model, instance_value, value):
    """
    Note that for queries - this can be DB specific syntax
    here we just use Python
    """
    return bool(re.search(value, instance_value))


def _iregex(model, instance_value, value):
    return bool(re.search(value, instance_value, flags=re.I))


match_functions = {
    'exact': _exact,
    'iexact': _iexact,
    'contains': _contains,
    'icontains': _icontains,
    'gt': _gt,
    'gte': _gte,
    'lt': _lt,
    'lte': _lte,
    'in': _in,
    'startswith': _startswith,
    'istartswith': _istartswith,
    'endswith': _endswith,
    'iendswith': _iendswith,
    'range': _range,
    'year': _year,
    'month': _month,
    'day': _day,
    'week_day': _week_day,
    'isnull': _isnull,
    'search': _search,
    'regex': _regex,
    'iregex': _iregex,
    }
