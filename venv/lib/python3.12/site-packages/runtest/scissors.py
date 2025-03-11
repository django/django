import re


def cut_sections(
    text,
    from_string=None,
    from_is_re=False,
    to_string=None,
    to_is_re=False,
    num_lines=0,
):
    """
    Cuts out sections of the text between anchors.

    Returns:
        output - list of remaining lines
    """
    output = []

    for i, _ in enumerate(text):
        start_line_matches = False
        if from_is_re:
            start_line_matches = re.match(r".*{0}".format(from_string), text[i])
        else:
            if from_string is None:
                # we are comparing entire file
                return text
            else:
                start_line_matches = from_string in text[i]

        if start_line_matches:
            if num_lines > 0:
                for n in range(i, i + num_lines):
                    output.append(text[n])
            else:
                for j in range(i, len(text)):
                    end_line_matches = False
                    if to_is_re:
                        end_line_matches = re.match(r".*{0}".format(to_string), text[j])
                    else:
                        end_line_matches = to_string in text[j]

                    if end_line_matches:
                        for n in range(i, j + 1):
                            output.append(text[n])
                        break

    return output


def test_cut_sections():
    text = """
1.0 2.0 3.0
1.0 2.0 3.0
1.0 2.0 3.0
1.0 2.0 3.0
1.0 2.0 3.0
1.0 2.0 3.0
1.0 2.0 3.0
raboof 1.0 3.0 7.0
       1.0 3.0 7.0
       1.0 3.0 7.0
       1.0 3.0 7.0
       1.0 3.0 7.0
       1.0 3.0 7.0
       1.0 3.0 7.0
       1.0 3.0 7.0"""

    res = cut_sections(text=text.splitlines(), from_string="raboof", num_lines=5)

    assert res == [
        "raboof 1.0 3.0 7.0",
        "       1.0 3.0 7.0",
        "       1.0 3.0 7.0",
        "       1.0 3.0 7.0",
        "       1.0 3.0 7.0",
    ]


def test_cut_sections_re():
    text = """
1.0
1.0
    raboof
2.0
2.0
    raboof2
3.0
3.0"""

    res = cut_sections(
        text=text.splitlines(),
        from_string="r.*f",
        from_is_re=True,
        to_string="r.*f2",
        to_is_re=True,
    )

    assert res == ["    raboof", "2.0", "2.0", "    raboof2", "    raboof2"]


def test_cut_sections_all():
    text = """first line
1.0 2.0 3.0
1.0 2.0 3.0
1.0 2.0 3.0
last line"""

    res = cut_sections(text=text.splitlines())

    assert res == [
        "first line",
        "1.0 2.0 3.0",
        "1.0 2.0 3.0",
        "1.0 2.0 3.0",
        "last line",
    ]


def test_cut_sections_from_string_to_string_2_matches():
    text = """first line
1.0 2.0 3.0
start
0.1234
end
start
1.2345
end
1.0 2.0 3.0
last line"""

    res = cut_sections(
        text=text.splitlines(),
        from_string="start",
        to_string="end",
    )

    assert res == [
        "start",
        "0.1234",
        "end",
        "start",
        "1.2345",
        "end",
    ]


def test_cut_sections_from_re_to_re_2_matches():
    text = """first line
1.0 2.0 3.0
  raboof
0.1234
    raboof2
   raboof
1.2345
0.2
  raboof2
1.0 2.0 3.0
last line"""

    res = cut_sections(
        text=text.splitlines(),
        from_string="r.*f",
        from_is_re=True,
        to_string="r.*f2",
        to_is_re=True,
    )
    print("Result from cutting:")
    print(res)

    assert res == [
        "  raboof",
        "0.1234",
        "    raboof2",
        "    raboof2",
        "   raboof",
        "1.2345",
        "0.2",
        "  raboof2",
        "  raboof2",
    ]
