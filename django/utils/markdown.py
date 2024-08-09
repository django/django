def find_closing_markdown_bracket(text, start):
    """
    Find the closing bracket corresponding to the opening bracket.
    """
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            if depth == 0:
                return i
            depth -= 1
        i += 1
    return -1


def has_markdown_link(text):
    """
    Check if the given text contains any Markdown links.
    """

    def is_valid_url(start, end):
        """
        Check if the URL is valid.
        """
        url = text[start:end].strip()
        return (
            url.startswith("http://")
            or url.startswith("https://")
            or any(c.isalnum() for c in url)
        )

    i = 0
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "[":
            close_bracket = find_closing_markdown_bracket(text, i + 1)
            if (
                close_bracket != -1
                and close_bracket + 1 < len(text)
                and text[close_bracket + 1] == "("
            ):
                j = close_bracket + 2
                paren_depth = 1
                while j < len(text):
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text[j] == "(":
                        paren_depth += 1
                    elif text[j] == ")":
                        paren_depth -= 1
                        if paren_depth == 0:
                            if is_valid_url(close_bracket + 2, j):
                                return True
                            break
                    j += 1
            i = close_bracket + 1 if close_bracket != -1 else i + 1
        else:
            i += 1
    return False
