"""Common profiles are defined here to be easily used within a project using --profile {name}"""

from typing import Any, Dict

black = {
    "multi_line_output": 3,
    "include_trailing_comma": True,
    "split_on_trailing_comma": True,
    "force_grid_wrap": 0,
    "use_parentheses": True,
    "ensure_newline_before_comments": True,
    "line_length": 88,
}
django = {
    "combine_as_imports": True,
    "include_trailing_comma": True,
    "multi_line_output": 5,
    "line_length": 79,
}
pycharm = {
    "multi_line_output": 3,
    "force_grid_wrap": 2,
    "lines_after_imports": 2,
}
google = {
    "force_single_line": True,
    "force_sort_within_sections": True,
    "lexicographical": True,
    "line_length": 1000,
    "single_line_exclusions": (
        "collections.abc",
        "six.moves",
        "typing",
        "typing_extensions",
    ),
    "order_by_type": False,
    "group_by_package": True,
}
open_stack = {
    "force_single_line": True,
    "force_sort_within_sections": True,
    "lexicographical": True,
}
plone = black.copy()
plone.update(
    {
        "force_alphabetical_sort": True,
        "force_single_line": True,
        "lines_after_imports": 2,
    }
)
attrs = {
    "atomic": True,
    "force_grid_wrap": 0,
    "include_trailing_comma": True,
    "lines_after_imports": 2,
    "lines_between_types": 1,
    "multi_line_output": 3,
    "use_parentheses": True,
}
hug = {
    "multi_line_output": 3,
    "include_trailing_comma": True,
    "force_grid_wrap": 0,
    "use_parentheses": True,
    "line_length": 100,
}
wemake = {
    "multi_line_output": 3,
    "include_trailing_comma": True,
    "use_parentheses": True,
    "line_length": 80,
}
appnexus = {
    **black,
    "force_sort_within_sections": True,
    "order_by_type": False,
    "case_sensitive": False,
    "reverse_relative": True,
    "sort_relative_in_force_sorted_sections": True,
    "sections": ["FUTURE", "STDLIB", "THIRDPARTY", "FIRSTPARTY", "APPLICATION", "LOCALFOLDER"],
    "no_lines_before": "LOCALFOLDER",
}

profiles: Dict[str, Dict[str, Any]] = {
    "black": black,
    "django": django,
    "pycharm": pycharm,
    "google": google,
    "open_stack": open_stack,
    "plone": plone,
    "attrs": attrs,
    "hug": hug,
    "wemake": wemake,
    "appnexus": appnexus,
}
