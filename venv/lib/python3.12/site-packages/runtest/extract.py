import re


def extract_numbers(text, mask=None):
    """
    Extracts floats and integers from string text.

    Returns:
        numbers - list of numbers
        locations - locations of each number as list of triples (line, start position, length)
    """
    numeric_const_pattern = r"""
    [-+]? # optional sign
    (?:
        (?: \d* \. \d+ ) # .1 .12 .123 etc 9.1 etc 98.1 etc
        |
        (?: \d+ \.? ) # 1. 12. 123. etc 1 12 123 etc
    )
    # followed by optional exponent part if desired
    (?: [EeDd] [+-]? \d+ ) ?
    """
    pattern_number_and_separator = re.compile(r"^[0-9\.eEdD\+\-]+[,]?$", re.VERBOSE)
    pattern_int = re.compile(r"-?[0-9]+", re.VERBOSE)
    pattern_float = re.compile(numeric_const_pattern, re.VERBOSE)
    pattern_d = re.compile(r"[dD]")

    numbers = []
    locations = []

    for n, line in enumerate(text):
        n_matches = 0
        for w in line.split():
            # do not consider words like TzB1g
            if not re.match(pattern_number_and_separator, w):
                continue

            n_matches += 1
            if mask is not None and n_matches not in mask:
                continue

            is_integer = False
            matched_floats = pattern_float.findall(w)

            if len(matched_floats) > 0:
                is_integer = matched_floats == pattern_int.findall(w)

            # apply floating point regex
            for m in matched_floats:
                index = line.index(m)
                # substitute dD by e
                if is_integer:
                    numbers.append(int(m))
                else:
                    m = pattern_d.sub("e", m)
                    numbers.append(float(m))
                locations.append((n, index, len(m)))

    return numbers, locations


def test_extract_numbers():
    text = """<<A( 3),B( 3)>> - linear response function (real):
-----------------------------------------------------------------------------------------------
   A - Z-Dipole length      B1u  T+
   B - Z-Dipole length      B1u  T+
-----------------------------------------------------------------------------------------------
 Frequency (real)     Real part                                     Convergence
-----------------------------------------------------------------------------------------------
  0.00000000 a.u.   -1.901357604797 a.u.                       3.04E-07   (converged)
-----------------------------------------------------------------------------------------------
----------------------------------------------------------------------------


                         +--------------------------------+
                         ! Electric dipole polarizability !
                         +--------------------------------+


 1 a.u =   0.14818471 angstrom**3


@   Elements of the electric dipole polarizability tensor

@   xx            1.90135760 a.u.   (converged)
@   yy            1.90135760 a.u.   (converged)
@   zz            1.90135760 a.u.   (converged)

@   average       1.90135760 a.u.
@   anisotropy    0.000      a.u.

@   xx            0.28175212 angstrom**3
@   yy            0.28175212 angstrom**3
@   zz            0.28175212 angstrom**3

@   average       0.28175212 angstrom**3
@   anisotropy    0.000      angstrom**3"""

    numbers, locations = extract_numbers(text.splitlines())

    assert numbers == [
        0.0,
        -1.901357604797,
        3.04e-07,
        1,
        0.14818471,
        1.9013576,
        1.9013576,
        1.9013576,
        1.9013576,
        0.0,
        0.28175212,
        0.28175212,
        0.28175212,
        0.28175212,
        0.0,
    ]
    assert locations == [
        (7, 2, 10),
        (7, 20, 15),
        (7, 63, 8),
        (17, 1, 1),
        (17, 11, 10),
        (22, 18, 10),
        (23, 18, 10),
        (24, 18, 10),
        (26, 18, 10),
        (27, 18, 5),
        (29, 18, 10),
        (30, 18, 10),
        (31, 18, 10),
        (33, 18, 10),
        (34, 18, 5),
    ]


def test_extract_numbers_mask():
    text = """1.0 2.0 3.0 4.0
1.0 2.0 3.0 4.0
1.0 2.0 3.0 4.0"""

    numbers, locations = extract_numbers(text.splitlines(), mask=[1, 4])

    assert numbers == [1.0, 4.0, 1.0, 4.0, 1.0, 4.0]
    assert locations == [
        (0, 0, 3),
        (0, 12, 3),
        (1, 0, 3),
        (1, 12, 3),
        (2, 0, 3),
        (2, 12, 3),
    ]


def test_extract_comma_separated_numbers_mask():
    text = """1.0, 2.0, 3.0, 4.0
1.0, 2.0, 3.0, 4.0
12, 22, 32, 42
1.0, 2.0, 3.0, 4.0
12, 22, 32, 42"""

    numbers, locations = extract_numbers(text.splitlines(), mask=[1, 3])

    assert numbers == [1.0, 3.0, 1.0, 3.0, 12, 32, 1.0, 3.0, 12, 32]
    assert locations == [
        (0, 0, 3),
        (0, 10, 3),
        (1, 0, 3),
        (1, 10, 3),
        (2, 0, 2),
        (2, 8, 2),
        (3, 0, 3),
        (3, 10, 3),
        (4, 0, 2),
        (4, 8, 2),
    ]


def test_extract_separated_numbers_mask():
    text = """1.0, 2.0' 3.0, 4.0
1.0, 2.0- 3.0, 4.0
1.0, 2.0? 3.0, 4.0
12, 22' 32, 42
12, 22- 32, 42"""

    numbers, locations = extract_numbers(text.splitlines(), mask=[1, 3])

    assert numbers == [1.0, 4.0, 1.0, 3.0, 1.0, 4.0, 12, 42, 12, 32]
    assert locations == [
        (0, 0, 3),
        (0, 15, 3),
        (1, 0, 3),
        (1, 10, 3),
        (2, 0, 3),
        (2, 15, 3),
        (3, 0, 2),
        (3, 12, 2),
        (4, 0, 2),
        (4, 8, 2),
    ]
