from typing import List, Optional, Tuple


def parse(line: str) -> Tuple[str, str]:
    """Parses import lines for comments and returns back the
    import statement and the associated comment.
    """
    comment_start = line.find("#")
    if comment_start != -1:
        return (line[:comment_start], line[comment_start + 1 :].strip())

    return (line, "")


def add_to_line(
    comments: Optional[List[str]],
    original_string: str = "",
    removed: bool = False,
    comment_prefix: str = "",
) -> str:
    """Returns a string with comments added if removed is not set."""
    if removed:
        return parse(original_string)[0]

    if not comments:
        return original_string

    unique_comments: List[str] = []
    for comment in comments:
        if comment not in unique_comments:
            unique_comments.append(comment)
    return f"{parse(original_string)[0]}{comment_prefix} {'; '.join(unique_comments)}"
