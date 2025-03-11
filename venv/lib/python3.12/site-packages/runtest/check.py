from .exceptions import FilterKeywordError, FailedTestError, BadFilterError
from .extract import extract_numbers
from .filter_api import recognized_kw
from .filter_constructor import get_filter
from .scissors import cut_sections
from .tuple_comparison import tuple_matches
import os


def check(filter_list, out_name, ref_name, log_dir, verbose=False):
    """
    Compares output with reference applying all filters tasks from the list of
    filters.

    Input:
        - filter_list -- list of filters
        - out_name -- actual output file name
        - ref_name -- reference output file name
        - log_dir -- directory which will hold logs
        - verbose  -- give verbose output upon failure

    Returns:
        - nothing

    Generates the following files in log_dir:
        - out_name.filtered  -- numbers extracted from output
        - out_name.reference -- numbers extracted from reference
        - out_name.diff      -- difference between the two above

    Raises:
        - FailedTestError
    """

    def _tuple_matches(t):
        if f.tolerance_is_relative:
            error_definition = "relative"
        else:
            error_definition = "absolute"
        return tuple_matches(
            t,
            tolerance=f.tolerance,
            error_definition=error_definition,
            ignore_sign=f.ignore_sign,
            skip_below=f.skip_below,
            skip_above=f.skip_above,
        )

    name_out = os.path.join(log_dir, out_name + ".filtered")
    name_ref = os.path.join(log_dir, out_name + ".reference")
    name_diff = os.path.join(log_dir, out_name + ".diff")

    with open(name_out, "w") as log_out:
        with open(name_ref, "w") as log_ref:
            with open(name_diff, "w") as log_diff:
                for f in filter_list:
                    out_filtered = cut_sections(
                        open(out_name).readlines(),
                        from_string=f.from_string,
                        from_is_re=f.from_is_re,
                        to_string=f.to_string,
                        to_is_re=f.to_is_re,
                        num_lines=f.num_lines,
                    )
                    if out_filtered == []:
                        if f.num_lines > 0:
                            r = '[%i lines from "%s"]' % (f.num_lines, f.from_string)
                        else:
                            r = '["%s" ... "%s"]' % (f.from_string, f.to_string)
                        message = (
                            "ERROR: filter %s did not extract anything from file %s\n"
                            % (r, out_name)
                        )
                        raise BadFilterError(message)

                    log_out.write("".join(out_filtered))
                    out_numbers, out_locations = extract_numbers(out_filtered, f.mask)
                    if f.mask is not None and out_numbers == []:
                        raise FilterKeywordError(
                            "ERROR: mask %s did not extract any numbers\n" % f.mask
                        )

                    ref_filtered = cut_sections(
                        open(ref_name).readlines(),
                        from_string=f.from_string,
                        from_is_re=f.from_is_re,
                        to_string=f.to_string,
                        to_is_re=f.to_is_re,
                        num_lines=f.num_lines,
                    )
                    if ref_filtered == []:
                        if f.num_lines > 0:
                            r = '[%i lines from "%s"]' % (f.num_lines, f.from_string)
                        else:
                            r = '["%s" ... "%s"]' % (f.from_string, f.to_string)
                        message = (
                            "ERROR: filter %s did not extract anything from file %s\n"
                            % (r, ref_name)
                        )
                        raise BadFilterError(message)

                    log_ref.write("".join(ref_filtered))
                    ref_numbers, _ = extract_numbers(ref_filtered, f.mask)
                    if f.mask is not None and ref_numbers == []:
                        raise FilterKeywordError(
                            "ERROR: mask %s did not extract any numbers\n" % f.mask
                        )

                    if f.ignore_sign:
                        out_numbers = list(map(abs, out_numbers))
                        ref_numbers = list(map(abs, ref_numbers))

                    if f.ignore_order:
                        out_numbers = sorted(out_numbers)
                        ref_numbers = sorted(ref_numbers)

                    if out_numbers == [] and ref_numbers == []:
                        # no numbers are extracted
                        if out_filtered != ref_filtered:
                            log_diff.write("ERROR: extracted strings do not match\n")
                            log_diff.write("own gave:\n")
                            log_diff.write("".join(out_filtered) + "\n")
                            log_diff.write("reference gave:\n")
                            log_diff.write("".join(ref_filtered) + "\n")

                    # we need to check for len(out_numbers) > 0
                    # for pure strings len(out_numbers) is 0
                    # TODO need to consider what to do with pure strings in future versions
                    if len(out_numbers) == len(ref_numbers) and len(out_numbers) > 0:
                        if not f.tolerance_is_set and (
                            any(map(lambda x: isinstance(x, float), out_numbers))
                            or any(map(lambda x: isinstance(x, float), ref_numbers))
                        ):
                            raise FilterKeywordError(
                                "ERROR: for floats you have to specify either rel_tolerance or abs_tolerance\n"
                            )
                        l = map(_tuple_matches, zip(out_numbers, ref_numbers))
                        matching, errors = zip(*l)  # unzip tuples to two lists
                        if not all(matching):
                            log_diff.write("\n")
                            for k, line in enumerate(out_filtered):
                                log_diff.write(".       %s" % line)
                                for i, _ in enumerate(out_numbers):
                                    (line_num, start_char, length) = out_locations[i]
                                    if line_num == k:
                                        if errors[i]:
                                            log_diff.write(
                                                "ERROR   %s%s %s\n"
                                                % (
                                                    " " * start_char,
                                                    "#" * length,
                                                    errors[i],
                                                )
                                            )

                    if len(out_numbers) != len(ref_numbers):
                        log_diff.write("ERROR: extracted sizes do not match\n")
                        log_diff.write("own gave %i numbers:\n" % len(out_numbers))
                        log_diff.write("".join(out_filtered) + "\n")
                        log_diff.write(
                            "reference gave %i numbers:\n" % len(ref_numbers)
                        )
                        log_diff.write("".join(ref_filtered) + "\n")

    if os.path.getsize("%s.diff" % out_name) > 0:
        log_diff = open("%s.diff" % out_name, "r")
        diff = ""
        for line in log_diff.readlines():
            diff += line
        log_diff.close()
        message = "ERROR: test %s failed\n" % out_name
        if verbose:
            message += diff
        raise FailedTestError(message)


def _test_setup(folder, filters):
    _here = os.path.abspath(os.path.dirname(__file__))
    test_dir = os.path.join(_here, "test", folder)
    out_name = os.path.join(test_dir, "out.txt")
    ref_name = os.path.join(test_dir, "ref.txt")
    log_dir = test_dir
    check(
        filter_list=filters,
        out_name=out_name,
        ref_name=ref_name,
        log_dir=log_dir,
        verbose=False,
    )


def test_check():
    import pytest

    _here = os.path.abspath(os.path.dirname(__file__))
    test_dir = os.path.join(_here, "test", "generic")
    out_name = os.path.join(test_dir, "out.txt")
    ref_name = os.path.join(test_dir, "ref.txt")
    log_dir = test_dir

    _test_setup(folder="generic", filters=[get_filter(abs_tolerance=0.1)])

    filters = [get_filter()]
    with pytest.raises(FilterKeywordError) as e:
        _test_setup(folder="generic", filters=[get_filter()])
    assert (
        "ERROR: for floats you have to specify either rel_tolerance or abs_tolerance\n"
        in str(e.value)
    )

    with pytest.raises(FailedTestError) as e:
        _test_setup(folder="generic", filters=[get_filter(rel_tolerance=0.01)])
    assert "ERROR: test %s failed\n" % out_name in str(e.value)
    with open(os.path.join(test_dir, "out.txt.diff"), "r") as f:
        assert (
            f.read()
            == """
.       1.0 2.0 3.0
ERROR           ### expected: 3.05 (rel diff: 1.64e-02)\n"""
        )

    with pytest.raises(FailedTestError) as e:
        _test_setup(folder="generic", filters=[get_filter(abs_tolerance=0.01)])
    assert "ERROR: test %s failed\n" % out_name in str(e.value)
    with open(os.path.join(test_dir, "out.txt.diff"), "r") as f:
        assert (
            f.read()
            == """
.       1.0 2.0 3.0
ERROR           ### expected: 3.05 (abs diff: 5.00e-02)\n"""
        )

    with pytest.raises(FailedTestError) as e:
        _test_setup(
            folder="generic", filters=[get_filter(abs_tolerance=0.01, ignore_sign=True)]
        )
    assert "ERROR: test %s failed\n" % out_name in str(e.value)
    with open(os.path.join(test_dir, "out.txt.diff"), "r") as f:
        assert (
            f.read()
            == """
.       1.0 2.0 3.0
ERROR           ### expected: 3.05 (abs diff: 5.00e-02 ignoring signs)\n"""
        )


def test_check_bad_filter():
    import pytest

    _here = os.path.abspath(os.path.dirname(__file__))
    test_dir = os.path.join(_here, "test", "generic")
    out_name = os.path.join(test_dir, "out.txt")

    with pytest.raises(BadFilterError) as e:
        _test_setup(
            folder="generic",
            filters=[get_filter(from_string="does not exist", num_lines=4)],
        )
    assert (
        'ERROR: filter [4 lines from "does not exist"] did not extract anything from file %s\n'
        % out_name
        in str(e.value)
    )

    with pytest.raises(BadFilterError) as e:
        _test_setup(
            folder="generic",
            filters=[get_filter(from_string="does not exist", to_string="either")],
        )
    assert (
        'ERROR: filter ["does not exist" ... "either"] did not extract anything from file %s\n'
        % out_name
        in str(e.value)
    )


def test_check_different_length():
    import pytest

    _here = os.path.abspath(os.path.dirname(__file__))
    test_dir = os.path.join(_here, "test", "different_length")
    out_name = os.path.join(test_dir, "out.txt")

    with pytest.raises(FailedTestError) as e:
        _test_setup(folder="different_length", filters=[get_filter(abs_tolerance=0.1)])
    assert "ERROR: test %s failed\n" % out_name in str(e.value)
    with open(os.path.join(test_dir, "out.txt.diff"), "r") as f:
        assert (
            f.read()
            == """ERROR: extracted sizes do not match
own gave 4 numbers:
1.0 2.0 3.0 4.0

reference gave 3 numbers:
1.0 2.0 3.05
\n"""
        )


def test_check_ignore_order():
    import pytest

    _here = os.path.abspath(os.path.dirname(__file__))
    test_dir = os.path.join(_here, "test", "ignore_order")
    out_name = os.path.join(test_dir, "out.txt")

    with pytest.raises(FailedTestError) as e:
        _test_setup(folder="ignore_order", filters=[get_filter(abs_tolerance=0.1)])
    assert "ERROR: test %s failed\n" % out_name in str(e.value)

    _test_setup(
        folder="ignore_order",
        filters=[get_filter(abs_tolerance=0.1, ignore_order=True)],
    )


def test_check_ignore_order_and_sign():
    import pytest

    _here = os.path.abspath(os.path.dirname(__file__))
    test_dir = os.path.join(_here, "test", "ignore_order_and_sign")
    out_name = os.path.join(test_dir, "out.txt")

    with pytest.raises(FailedTestError) as e:
        _test_setup(
            folder="ignore_order_and_sign", filters=[get_filter(abs_tolerance=0.1)]
        )
    assert "ERROR: test %s failed\n" % out_name in str(e.value)

    _test_setup(
        folder="ignore_order_and_sign",
        filters=[get_filter(abs_tolerance=0.1, ignore_order=True, ignore_sign=True)],
    )


def test_bad_keywords():
    import pytest

    with pytest.raises(FilterKeywordError) as e:
        _ = get_filter(raboof=0, foo=1)
    exception = """ERROR: keyword(s) (foo, raboof) not recognized
       available keywords: ({0})\n""".format(
        ", ".join(recognized_kw)
    )
    assert exception in str(e.value)

    with pytest.raises(FilterKeywordError) as e:
        _ = get_filter(from_string="foo", from_re="foo", to_string="foo", to_re="foo")
    assert (
        "ERROR: incompatible keyword pairs: [('from_re', 'from_string'), ('to_re', 'to_string')]\n"
        in str(e.value)
    )


def test_only_string():
    import pytest

    _here = os.path.abspath(os.path.dirname(__file__))
    test_dir = os.path.join(_here, "test", "only_string")
    out_name = os.path.join(test_dir, "out.txt")

    _test_setup(folder="only_string", filters=[get_filter(string="raboof")])

    with pytest.raises(BadFilterError) as e:
        _test_setup(folder="only_string", filters=[get_filter(string="foo")])
    assert (
        'ERROR: filter [1 lines from "foo"] did not extract anything from file %s\n'
        % out_name
        in str(e.value)
    )


def test_check_integers():
    import pytest

    _here = os.path.abspath(os.path.dirname(__file__))
    test_dir = os.path.join(_here, "test", "integers")
    out_name = os.path.join(test_dir, "out.txt")

    # both integer and float input should work here
    _test_setup(folder="integers", filters=[get_filter(abs_tolerance=2)])
    _test_setup(folder="integers", filters=[get_filter(abs_tolerance=2.0)])

    with pytest.raises(FailedTestError) as e:
        _test_setup(folder="integers", filters=[get_filter(abs_tolerance=1)])
    assert "ERROR: test %s failed\n" % out_name in str(e.value)

    _test_setup(folder="integers", filters=[get_filter(rel_tolerance=1.0)])
