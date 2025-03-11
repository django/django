import sys
from collections import namedtuple
from .exceptions import FilterKeywordError
from .filter_api import recognized_kw, incompatible_pairs


def get_filter(**kwargs):
    _filter = namedtuple(
        "_filter",
        [
            "from_is_re",
            "from_string",
            "skip_above",
            "skip_below",
            "ignore_sign",
            "ignore_order",
            "mask",
            "num_lines",
            "to_is_re",
            "to_string",
            "tolerance",
            "tolerance_is_relative",
            "tolerance_is_set",
        ],
    )

    unrecoginzed_kw = [kw for kw in kwargs.keys() if kw not in recognized_kw]
    if unrecoginzed_kw != []:
        error = """ERROR: keyword(s) ({unrecognized}) not recognized
       available keywords: ({available})\n""".format(
            unrecognized=(", ").join(sorted(unrecoginzed_kw)),
            available=(", ").join(recognized_kw),
        )
        raise FilterKeywordError(error)

    incompatible_kw = [
        (kw1, kw2)
        for (kw1, kw2) in incompatible_pairs
        if kw1 in kwargs.keys() and kw2 in kwargs.keys()
    ]
    if incompatible_kw != []:
        error = "ERROR: incompatible keyword pairs: {0}\n".format(incompatible_kw)
        raise FilterKeywordError(error)

    # now continue with keywords
    _filter.from_string = kwargs.get("from_string", None)
    _filter.to_string = kwargs.get("to_string", None)
    _filter.ignore_sign = kwargs.get("ignore_sign", False)
    _filter.ignore_order = kwargs.get("ignore_order", False)
    _filter.skip_below = kwargs.get("skip_below", sys.float_info.min)
    _filter.skip_above = kwargs.get("skip_above", sys.float_info.max)
    _filter.num_lines = kwargs.get("num_lines", 0)

    if "rel_tolerance" in kwargs.keys():
        _filter.tolerance = kwargs.get("rel_tolerance")
        _filter.tolerance_is_relative = True
        _filter.tolerance_is_set = True
    elif "abs_tolerance" in kwargs.keys():
        _filter.tolerance = kwargs.get("abs_tolerance")
        _filter.tolerance_is_relative = False
        _filter.tolerance_is_set = True
    else:
        _filter.tolerance_is_set = False

    _filter.mask = kwargs.get("mask", None)

    _filter.from_is_re = False
    from_re = kwargs.get("from_re", "")
    if from_re != "":
        _filter.from_string = from_re
        _filter.from_is_re = True

    _filter.to_is_re = False
    to_re = kwargs.get("to_re", "")
    if to_re != "":
        _filter.to_string = to_re
        _filter.to_is_re = True

    only_string = kwargs.get("string", "")
    if only_string != "":
        _filter.from_string = only_string
        _filter.num_lines = 1

    only_re = kwargs.get("re", "")
    if only_re != "":
        _filter.from_string = only_re
        _filter.num_lines = 1
        _filter.from_is_re = True

    return _filter
