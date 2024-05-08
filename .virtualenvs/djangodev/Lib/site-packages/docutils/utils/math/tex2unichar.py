#!/usr/bin/env python3

# LaTeX math to Unicode symbols translation dictionaries.
# Generated with ``write_tex2unichar.py`` from the data in
# http://milde.users.sourceforge.net/LUCR/Math/

# Includes commands from:
#   standard LaTeX
#   amssymb
#   amsmath
#   amsxtra
#   bbold
#   esint
#   mathabx
#   mathdots
#   txfonts
#   stmaryrd
#   wasysym

mathaccent = {
    'acute': '\u0301',  #  ́ COMBINING ACUTE ACCENT
    'bar': '\u0304',  #  ̄ COMBINING MACRON
    'breve': '\u0306',  #  ̆ COMBINING BREVE
    'check': '\u030c',  #  ̌ COMBINING CARON
    'ddddot': '\u20dc',  #  ⃜ COMBINING FOUR DOTS ABOVE
    'dddot': '\u20db',  #  ⃛ COMBINING THREE DOTS ABOVE
    'ddot': '\u0308',  #  ̈ COMBINING DIAERESIS
    'dot': '\u0307',  #  ̇ COMBINING DOT ABOVE
    'grave': '\u0300',  #  ̀ COMBINING GRAVE ACCENT
    'hat': '\u0302',  #  ̂ COMBINING CIRCUMFLEX ACCENT
    'mathring': '\u030a',  #  ̊ COMBINING RING ABOVE
    'not': '\u0338',  #  ̸ COMBINING LONG SOLIDUS OVERLAY
    'overleftrightarrow': '\u20e1',  #  ⃡ COMBINING LEFT RIGHT ARROW ABOVE
    'overline': '\u0305',  #  ̅ COMBINING OVERLINE
    'tilde': '\u0303',  #  ̃ COMBINING TILDE
    'underbar': '\u0331',  #  ̱ COMBINING MACRON BELOW
    'underleftarrow': '\u20ee',  #  ⃮ COMBINING LEFT ARROW BELOW
    'underline': '\u0332',  #  ̲ COMBINING LOW LINE
    'underrightarrow': '\u20ef',  #  ⃯ COMBINING RIGHT ARROW BELOW
    'vec': '\u20d7',  #  ⃗ COMBINING RIGHT ARROW ABOVE
    }

mathalpha = {
    'Bbbk': '\U0001d55c',  # 𝕜 MATHEMATICAL DOUBLE-STRUCK SMALL K
    'Delta': '\u0394',  # Δ GREEK CAPITAL LETTER DELTA
    'Gamma': '\u0393',  # Γ GREEK CAPITAL LETTER GAMMA
    'Im': '\u2111',  # ℑ BLACK-LETTER CAPITAL I
    'Lambda': '\u039b',  # Λ GREEK CAPITAL LETTER LAMDA
    'Omega': '\u03a9',  # Ω GREEK CAPITAL LETTER OMEGA
    'Phi': '\u03a6',  # Φ GREEK CAPITAL LETTER PHI
    'Pi': '\u03a0',  # Π GREEK CAPITAL LETTER PI
    'Psi': '\u03a8',  # Ψ GREEK CAPITAL LETTER PSI
    'Re': '\u211c',  # ℜ BLACK-LETTER CAPITAL R
    'Sigma': '\u03a3',  # Σ GREEK CAPITAL LETTER SIGMA
    'Theta': '\u0398',  # Θ GREEK CAPITAL LETTER THETA
    'Upsilon': '\u03a5',  # Υ GREEK CAPITAL LETTER UPSILON
    'Xi': '\u039e',  # Ξ GREEK CAPITAL LETTER XI
    'aleph': '\u2135',  # ℵ ALEF SYMBOL
    'alpha': '\u03b1',  # α GREEK SMALL LETTER ALPHA
    'beta': '\u03b2',  # β GREEK SMALL LETTER BETA
    'beth': '\u2136',  # ℶ BET SYMBOL
    'chi': '\u03c7',  # χ GREEK SMALL LETTER CHI
    'daleth': '\u2138',  # ℸ DALET SYMBOL
    'delta': '\u03b4',  # δ GREEK SMALL LETTER DELTA
    'digamma': '\u03dd',  # ϝ GREEK SMALL LETTER DIGAMMA
    'ell': '\u2113',  # ℓ SCRIPT SMALL L
    'epsilon': '\u03f5',  # ϵ GREEK LUNATE EPSILON SYMBOL
    'eta': '\u03b7',  # η GREEK SMALL LETTER ETA
    'eth': '\xf0',  # ð LATIN SMALL LETTER ETH
    'gamma': '\u03b3',  # γ GREEK SMALL LETTER GAMMA
    'gimel': '\u2137',  # ℷ GIMEL SYMBOL
    'imath': '\u0131',  # ı LATIN SMALL LETTER DOTLESS I
    'iota': '\u03b9',  # ι GREEK SMALL LETTER IOTA
    'jmath': '\u0237',  # ȷ LATIN SMALL LETTER DOTLESS J
    'kappa': '\u03ba',  # κ GREEK SMALL LETTER KAPPA
    'lambda': '\u03bb',  # λ GREEK SMALL LETTER LAMDA
    'mu': '\u03bc',  # μ GREEK SMALL LETTER MU
    'nu': '\u03bd',  # ν GREEK SMALL LETTER NU
    'omega': '\u03c9',  # ω GREEK SMALL LETTER OMEGA
    'phi': '\u03d5',  # ϕ GREEK PHI SYMBOL
    'pi': '\u03c0',  # π GREEK SMALL LETTER PI
    'psi': '\u03c8',  # ψ GREEK SMALL LETTER PSI
    'rho': '\u03c1',  # ρ GREEK SMALL LETTER RHO
    'sigma': '\u03c3',  # σ GREEK SMALL LETTER SIGMA
    'tau': '\u03c4',  # τ GREEK SMALL LETTER TAU
    'theta': '\u03b8',  # θ GREEK SMALL LETTER THETA
    'upsilon': '\u03c5',  # υ GREEK SMALL LETTER UPSILON
    'varDelta': '\U0001d6e5',  # 𝛥 MATHEMATICAL ITALIC CAPITAL DELTA
    'varGamma': '\U0001d6e4',  # 𝛤 MATHEMATICAL ITALIC CAPITAL GAMMA
    'varLambda': '\U0001d6ec',  # 𝛬 MATHEMATICAL ITALIC CAPITAL LAMDA
    'varOmega': '\U0001d6fa',  # 𝛺 MATHEMATICAL ITALIC CAPITAL OMEGA
    'varPhi': '\U0001d6f7',  # 𝛷 MATHEMATICAL ITALIC CAPITAL PHI
    'varPi': '\U0001d6f1',  # 𝛱 MATHEMATICAL ITALIC CAPITAL PI
    'varPsi': '\U0001d6f9',  # 𝛹 MATHEMATICAL ITALIC CAPITAL PSI
    'varSigma': '\U0001d6f4',  # 𝛴 MATHEMATICAL ITALIC CAPITAL SIGMA
    'varTheta': '\U0001d6e9',  # 𝛩 MATHEMATICAL ITALIC CAPITAL THETA
    'varUpsilon': '\U0001d6f6',  # 𝛶 MATHEMATICAL ITALIC CAPITAL UPSILON
    'varXi': '\U0001d6ef',  # 𝛯 MATHEMATICAL ITALIC CAPITAL XI
    'varepsilon': '\u03b5',  # ε GREEK SMALL LETTER EPSILON
    'varkappa': '\u03f0',  # ϰ GREEK KAPPA SYMBOL
    'varphi': '\u03c6',  # φ GREEK SMALL LETTER PHI
    'varpi': '\u03d6',  # ϖ GREEK PI SYMBOL
    'varrho': '\u03f1',  # ϱ GREEK RHO SYMBOL
    'varsigma': '\u03c2',  # ς GREEK SMALL LETTER FINAL SIGMA
    'vartheta': '\u03d1',  # ϑ GREEK THETA SYMBOL
    'wp': '\u2118',  # ℘ SCRIPT CAPITAL P
    'xi': '\u03be',  # ξ GREEK SMALL LETTER XI
    'zeta': '\u03b6',  # ζ GREEK SMALL LETTER ZETA
    }

mathbin = {
    'Cap': '\u22d2',  # ⋒ DOUBLE INTERSECTION
    'Circle': '\u25cb',  # ○ WHITE CIRCLE
    'Cup': '\u22d3',  # ⋓ DOUBLE UNION
    'LHD': '\u25c0',  # ◀ BLACK LEFT-POINTING TRIANGLE
    'RHD': '\u25b6',  # ▶ BLACK RIGHT-POINTING TRIANGLE
    'amalg': '\u2a3f',  # ⨿ AMALGAMATION OR COPRODUCT
    'ast': '\u2217',  # ∗ ASTERISK OPERATOR
    'barwedge': '\u22bc',  # ⊼ NAND
    'bigcirc': '\u25ef',  # ◯ LARGE CIRCLE
    'bigtriangledown': '\u25bd',  # ▽ WHITE DOWN-POINTING TRIANGLE
    'bigtriangleup': '\u25b3',  # △ WHITE UP-POINTING TRIANGLE
    'bindnasrepma': '\u214b',  # ⅋ TURNED AMPERSAND
    'blacklozenge': '\u29eb',  # ⧫ BLACK LOZENGE
    'boxast': '\u29c6',  # ⧆ SQUARED ASTERISK
    'boxbar': '\u25eb',  # ◫ WHITE SQUARE WITH VERTICAL BISECTING LINE
    'boxbox': '\u29c8',  # ⧈ SQUARED SQUARE
    'boxbslash': '\u29c5',  # ⧅ SQUARED FALLING DIAGONAL SLASH
    'boxcircle': '\u29c7',  # ⧇ SQUARED SMALL CIRCLE
    'boxdot': '\u22a1',  # ⊡ SQUARED DOT OPERATOR
    'boxminus': '\u229f',  # ⊟ SQUARED MINUS
    'boxplus': '\u229e',  # ⊞ SQUARED PLUS
    'boxslash': '\u29c4',  # ⧄ SQUARED RISING DIAGONAL SLASH
    'boxtimes': '\u22a0',  # ⊠ SQUARED TIMES
    'bullet': '\u2022',  # • BULLET
    'cap': '\u2229',  # ∩ INTERSECTION
    'cdot': '\u22c5',  # ⋅ DOT OPERATOR
    'circ': '\u2218',  # ∘ RING OPERATOR
    'circledast': '\u229b',  # ⊛ CIRCLED ASTERISK OPERATOR
    'circledbslash': '\u29b8',  # ⦸ CIRCLED REVERSE SOLIDUS
    'circledcirc': '\u229a',  # ⊚ CIRCLED RING OPERATOR
    'circleddash': '\u229d',  # ⊝ CIRCLED DASH
    'circledgtr': '\u29c1',  # ⧁ CIRCLED GREATER-THAN
    'circledless': '\u29c0',  # ⧀ CIRCLED LESS-THAN
    'cup': '\u222a',  # ∪ UNION
    'curlyvee': '\u22ce',  # ⋎ CURLY LOGICAL OR
    'curlywedge': '\u22cf',  # ⋏ CURLY LOGICAL AND
    'dagger': '\u2020',  # † DAGGER
    'ddagger': '\u2021',  # ‡ DOUBLE DAGGER
    'diamond': '\u22c4',  # ⋄ DIAMOND OPERATOR
    'div': '\xf7',  # ÷ DIVISION SIGN
    'divideontimes': '\u22c7',  # ⋇ DIVISION TIMES
    'dotplus': '\u2214',  # ∔ DOT PLUS
    'doublebarwedge': '\u2a5e',  # ⩞ LOGICAL AND WITH DOUBLE OVERBAR
    'gtrdot': '\u22d7',  # ⋗ GREATER-THAN WITH DOT
    'intercal': '\u22ba',  # ⊺ INTERCALATE
    'interleave': '\u2af4',  # ⫴ TRIPLE VERTICAL BAR BINARY RELATION
    'invamp': '\u214b',  # ⅋ TURNED AMPERSAND
    'land': '\u2227',  # ∧ LOGICAL AND
    'leftthreetimes': '\u22cb',  # ⋋ LEFT SEMIDIRECT PRODUCT
    'lessdot': '\u22d6',  # ⋖ LESS-THAN WITH DOT
    'lor': '\u2228',  # ∨ LOGICAL OR
    'ltimes': '\u22c9',  # ⋉ LEFT NORMAL FACTOR SEMIDIRECT PRODUCT
    'mp': '\u2213',  # ∓ MINUS-OR-PLUS SIGN
    'odot': '\u2299',  # ⊙ CIRCLED DOT OPERATOR
    'ominus': '\u2296',  # ⊖ CIRCLED MINUS
    'oplus': '\u2295',  # ⊕ CIRCLED PLUS
    'oslash': '\u2298',  # ⊘ CIRCLED DIVISION SLASH
    'otimes': '\u2297',  # ⊗ CIRCLED TIMES
    'pm': '\xb1',  # ± PLUS-MINUS SIGN
    'rightthreetimes': '\u22cc',  # ⋌ RIGHT SEMIDIRECT PRODUCT
    'rtimes': '\u22ca',  # ⋊ RIGHT NORMAL FACTOR SEMIDIRECT PRODUCT
    'setminus': '\u29f5',  # ⧵ REVERSE SOLIDUS OPERATOR
    'slash': '\u2215',  # ∕ DIVISION SLASH
    'smallsetminus': '\u2216',  # ∖ SET MINUS
    'smalltriangledown': '\u25bf',  # ▿ WHITE DOWN-POINTING SMALL TRIANGLE
    'smalltriangleleft': '\u25c3',  # ◃ WHITE LEFT-POINTING SMALL TRIANGLE
    'smalltriangleright': '\u25b9',  # ▹ WHITE RIGHT-POINTING SMALL TRIANGLE
    'sqcap': '\u2293',  # ⊓ SQUARE CAP
    'sqcup': '\u2294',  # ⊔ SQUARE CUP
    'sslash': '\u2afd',  # ⫽ DOUBLE SOLIDUS OPERATOR
    'star': '\u22c6',  # ⋆ STAR OPERATOR
    'talloblong': '\u2afe',  # ⫾ WHITE VERTICAL BAR
    'times': '\xd7',  # × MULTIPLICATION SIGN
    'triangleleft': '\u25c3',  # ◃ WHITE LEFT-POINTING SMALL TRIANGLE
    'triangleright': '\u25b9',  # ▹ WHITE RIGHT-POINTING SMALL TRIANGLE
    'uplus': '\u228e',  # ⊎ MULTISET UNION
    'vee': '\u2228',  # ∨ LOGICAL OR
    'veebar': '\u22bb',  # ⊻ XOR
    'wedge': '\u2227',  # ∧ LOGICAL AND
    'wr': '\u2240',  # ≀ WREATH PRODUCT
    }

mathclose = {
    'Rbag': '\u27c6',  # ⟆ RIGHT S-SHAPED BAG DELIMITER
    'lrcorner': '\u231f',  # ⌟ BOTTOM RIGHT CORNER
    'rangle': '\u27e9',  # ⟩ MATHEMATICAL RIGHT ANGLE BRACKET
    'rbag': '\u27c6',  # ⟆ RIGHT S-SHAPED BAG DELIMITER
    'rbrace': '}',  # } RIGHT CURLY BRACKET
    'rbrack': ']',  # ] RIGHT SQUARE BRACKET
    'rceil': '\u2309',  # ⌉ RIGHT CEILING
    'rfloor': '\u230b',  # ⌋ RIGHT FLOOR
    'rgroup': '\u27ef',  # ⟯ MATHEMATICAL RIGHT FLATTENED PARENTHESIS
    'rrbracket': '\u27e7',  # ⟧ MATHEMATICAL RIGHT WHITE SQUARE BRACKET
    'rrparenthesis': '\u2988',  # ⦈ Z NOTATION RIGHT IMAGE BRACKET
    'urcorner': '\u231d',  # ⌝ TOP RIGHT CORNER
    '}': '}',  # } RIGHT CURLY BRACKET
    }

mathfence = {
    'Vert': '\u2016',  # ‖ DOUBLE VERTICAL LINE
    'vert': '|',  # | VERTICAL LINE
    '|': '\u2016',  # ‖ DOUBLE VERTICAL LINE
    }

mathop = {
    'bigcap': '\u22c2',  # ⋂ N-ARY INTERSECTION
    'bigcup': '\u22c3',  # ⋃ N-ARY UNION
    'biginterleave': '\u2afc',  # ⫼ LARGE TRIPLE VERTICAL BAR OPERATOR
    'bigodot': '\u2a00',  # ⨀ N-ARY CIRCLED DOT OPERATOR
    'bigoplus': '\u2a01',  # ⨁ N-ARY CIRCLED PLUS OPERATOR
    'bigotimes': '\u2a02',  # ⨂ N-ARY CIRCLED TIMES OPERATOR
    'bigsqcap': '\u2a05',  # ⨅ N-ARY SQUARE INTERSECTION OPERATOR
    'bigsqcup': '\u2a06',  # ⨆ N-ARY SQUARE UNION OPERATOR
    'biguplus': '\u2a04',  # ⨄ N-ARY UNION OPERATOR WITH PLUS
    'bigvee': '\u22c1',  # ⋁ N-ARY LOGICAL OR
    'bigwedge': '\u22c0',  # ⋀ N-ARY LOGICAL AND
    'coprod': '\u2210',  # ∐ N-ARY COPRODUCT
    'fatsemi': '\u2a1f',  # ⨟ Z NOTATION SCHEMA COMPOSITION
    'fint': '\u2a0f',  # ⨏ INTEGRAL AVERAGE WITH SLASH
    'iiiint': '\u2a0c',  # ⨌ QUADRUPLE INTEGRAL OPERATOR
    'iiint': '\u222d',  # ∭ TRIPLE INTEGRAL
    'iint': '\u222c',  # ∬ DOUBLE INTEGRAL
    'int': '\u222b',  # ∫ INTEGRAL
    'intop': '\u222b',  # ∫ INTEGRAL
    'oiiint': '\u2230',  # ∰ VOLUME INTEGRAL
    'oiint': '\u222f',  # ∯ SURFACE INTEGRAL
    'oint': '\u222e',  # ∮ CONTOUR INTEGRAL
    'ointctrclockwise': '\u2233',  # ∳ ANTICLOCKWISE CONTOUR INTEGRAL
    'ointop': '\u222e',  # ∮ CONTOUR INTEGRAL
    'prod': '\u220f',  # ∏ N-ARY PRODUCT
    'sqint': '\u2a16',  # ⨖ QUATERNION INTEGRAL OPERATOR
    'sum': '\u2211',  # ∑ N-ARY SUMMATION
    'varointclockwise': '\u2232',  # ∲ CLOCKWISE CONTOUR INTEGRAL
    'varprod': '\u2a09',  # ⨉ N-ARY TIMES OPERATOR
    }

mathopen = {
    'Lbag': '\u27c5',  # ⟅ LEFT S-SHAPED BAG DELIMITER
    'langle': '\u27e8',  # ⟨ MATHEMATICAL LEFT ANGLE BRACKET
    'lbag': '\u27c5',  # ⟅ LEFT S-SHAPED BAG DELIMITER
    'lbrace': '{',  # { LEFT CURLY BRACKET
    'lbrack': '[',  # [ LEFT SQUARE BRACKET
    'lceil': '\u2308',  # ⌈ LEFT CEILING
    'lfloor': '\u230a',  # ⌊ LEFT FLOOR
    'lgroup': '\u27ee',  # ⟮ MATHEMATICAL LEFT FLATTENED PARENTHESIS
    'llbracket': '\u27e6',  # ⟦ MATHEMATICAL LEFT WHITE SQUARE BRACKET
    'llcorner': '\u231e',  # ⌞ BOTTOM LEFT CORNER
    'llparenthesis': '\u2987',  # ⦇ Z NOTATION LEFT IMAGE BRACKET
    'ulcorner': '\u231c',  # ⌜ TOP LEFT CORNER
    '{': '{',  # { LEFT CURLY BRACKET
    }

mathord = {
    '#': '#',  # # NUMBER SIGN
    '$': '$',  # $ DOLLAR SIGN
    '%': '%',  # % PERCENT SIGN
    '&': '&',  # & AMPERSAND
    'AC': '\u223f',  # ∿ SINE WAVE
    'APLcomment': '\u235d',  # ⍝ APL FUNCTIONAL SYMBOL UP SHOE JOT
    'APLdownarrowbox': '\u2357',  # ⍗ APL FUNCTIONAL SYMBOL QUAD DOWNWARDS ARROW
    'APLinput': '\u235e',  # ⍞ APL FUNCTIONAL SYMBOL QUOTE QUAD
    'APLinv': '\u2339',  # ⌹ APL FUNCTIONAL SYMBOL QUAD DIVIDE
    'APLleftarrowbox': '\u2347',  # ⍇ APL FUNCTIONAL SYMBOL QUAD LEFTWARDS ARROW
    'APLlog': '\u235f',  # ⍟ APL FUNCTIONAL SYMBOL CIRCLE STAR
    'APLrightarrowbox': '\u2348',  # ⍈ APL FUNCTIONAL SYMBOL QUAD RIGHTWARDS ARROW
    'APLuparrowbox': '\u2350',  # ⍐ APL FUNCTIONAL SYMBOL QUAD UPWARDS ARROW
    'Aries': '\u2648',  # ♈ ARIES
    'Box': '\u2b1c',  # ⬜ WHITE LARGE SQUARE
    'CIRCLE': '\u25cf',  # ● BLACK CIRCLE
    'CheckedBox': '\u2611',  # ☑ BALLOT BOX WITH CHECK
    'Diamond': '\u25c7',  # ◇ WHITE DIAMOND
    'Diamondblack': '\u25c6',  # ◆ BLACK DIAMOND
    'Diamonddot': '\u27d0',  # ⟐ WHITE DIAMOND WITH CENTRED DOT
    'Finv': '\u2132',  # Ⅎ TURNED CAPITAL F
    'Game': '\u2141',  # ⅁ TURNED SANS-SERIF CAPITAL G
    'Gemini': '\u264a',  # ♊ GEMINI
    'Jupiter': '\u2643',  # ♃ JUPITER
    'LEFTCIRCLE': '\u25d6',  # ◖ LEFT HALF BLACK CIRCLE
    'LEFTcircle': '\u25d0',  # ◐ CIRCLE WITH LEFT HALF BLACK
    'Leo': '\u264c',  # ♌ LEO
    'Libra': '\u264e',  # ♎ LIBRA
    'Mars': '\u2642',  # ♂ MALE SIGN
    'Mercury': '\u263f',  # ☿ MERCURY
    'Neptune': '\u2646',  # ♆ NEPTUNE
    'P': '\xb6',  # ¶ PILCROW SIGN
    'Pluto': '\u2647',  # ♇ PLUTO
    'RIGHTCIRCLE': '\u25d7',  # ◗ RIGHT HALF BLACK CIRCLE
    'RIGHTcircle': '\u25d1',  # ◑ CIRCLE WITH RIGHT HALF BLACK
    'S': '\xa7',  # § SECTION SIGN
    'Saturn': '\u2644',  # ♄ SATURN
    'Scorpio': '\u264f',  # ♏ SCORPIUS
    'Square': '\u2610',  # ☐ BALLOT BOX
    'Sun': '\u2609',  # ☉ SUN
    'Taurus': '\u2649',  # ♉ TAURUS
    'Uranus': '\u2645',  # ♅ URANUS
    'Venus': '\u2640',  # ♀ FEMALE SIGN
    'XBox': '\u2612',  # ☒ BALLOT BOX WITH X
    'Yup': '\u2144',  # ⅄ TURNED SANS-SERIF CAPITAL Y
    '_': '_',  # _ LOW LINE
    'angle': '\u2220',  # ∠ ANGLE
    'aquarius': '\u2652',  # ♒ AQUARIUS
    'aries': '\u2648',  # ♈ ARIES
    'arrowvert': '\u23d0',  # ⏐ VERTICAL LINE EXTENSION
    'backprime': '\u2035',  # ‵ REVERSED PRIME
    'backslash': '\\',  # \ REVERSE SOLIDUS
    'bigstar': '\u2605',  # ★ BLACK STAR
    'blacksmiley': '\u263b',  # ☻ BLACK SMILING FACE
    'blacksquare': '\u25fc',  # ◼ BLACK MEDIUM SQUARE
    'blacktriangle': '\u25b4',  # ▴ BLACK UP-POINTING SMALL TRIANGLE
    'blacktriangledown': '\u25be',  # ▾ BLACK DOWN-POINTING SMALL TRIANGLE
    'blacktriangleup': '\u25b4',  # ▴ BLACK UP-POINTING SMALL TRIANGLE
    'bot': '\u22a5',  # ⊥ UP TACK
    'boy': '\u2642',  # ♂ MALE SIGN
    'bracevert': '\u23aa',  # ⎪ CURLY BRACKET EXTENSION
    'cancer': '\u264b',  # ♋ CANCER
    'capricornus': '\u2651',  # ♑ CAPRICORN
    'cdots': '\u22ef',  # ⋯ MIDLINE HORIZONTAL ELLIPSIS
    'cent': '\xa2',  # ¢ CENT SIGN
    'checkmark': '\u2713',  # ✓ CHECK MARK
    'circledR': '\u24c7',  # Ⓡ CIRCLED LATIN CAPITAL LETTER R
    'circledS': '\u24c8',  # Ⓢ CIRCLED LATIN CAPITAL LETTER S
    'clubsuit': '\u2663',  # ♣ BLACK CLUB SUIT
    'complement': '\u2201',  # ∁ COMPLEMENT
    'diagdown': '\u27cd',  # ⟍ MATHEMATICAL FALLING DIAGONAL
    'diagup': '\u27cb',  # ⟋ MATHEMATICAL RISING DIAGONAL
    'diameter': '\u2300',  # ⌀ DIAMETER SIGN
    'diamondsuit': '\u2662',  # ♢ WHITE DIAMOND SUIT
    'earth': '\u2641',  # ♁ EARTH
    'emptyset': '\u2205',  # ∅ EMPTY SET
    'exists': '\u2203',  # ∃ THERE EXISTS
    'female': '\u2640',  # ♀ FEMALE SIGN
    'flat': '\u266d',  # ♭ MUSIC FLAT SIGN
    'forall': '\u2200',  # ∀ FOR ALL
    'fourth': '\u2057',  # ⁗ QUADRUPLE PRIME
    'frownie': '\u2639',  # ☹ WHITE FROWNING FACE
    'gemini': '\u264a',  # ♊ GEMINI
    'girl': '\u2640',  # ♀ FEMALE SIGN
    'heartsuit': '\u2661',  # ♡ WHITE HEART SUIT
    'hslash': '\u210f',  # ℏ PLANCK CONSTANT OVER TWO PI
    'infty': '\u221e',  # ∞ INFINITY
    'invdiameter': '\u2349',  # ⍉ APL FUNCTIONAL SYMBOL CIRCLE BACKSLASH
    'invneg': '\u2310',  # ⌐ REVERSED NOT SIGN
    'jupiter': '\u2643',  # ♃ JUPITER
    'ldots': '\u2026',  # … HORIZONTAL ELLIPSIS
    'leftmoon': '\u263e',  # ☾ LAST QUARTER MOON
    'leo': '\u264c',  # ♌ LEO
    'libra': '\u264e',  # ♎ LIBRA
    'lmoustache': '\u23b0',  # ⎰ UPPER LEFT OR LOWER RIGHT CURLY BRACKET SECTION
    'lnot': '\xac',  # ¬ NOT SIGN
    'lozenge': '\u25ca',  # ◊ LOZENGE
    'male': '\u2642',  # ♂ MALE SIGN
    'maltese': '\u2720',  # ✠ MALTESE CROSS
    'mathcent': '\xa2',  # ¢ CENT SIGN
    'mathdollar': '$',  # $ DOLLAR SIGN
    'mathsterling': '\xa3',  # £ POUND SIGN
    'measuredangle': '\u2221',  # ∡ MEASURED ANGLE
    'medbullet': '\u26ab',  # ⚫ MEDIUM BLACK CIRCLE
    'medcirc': '\u26aa',  # ⚪ MEDIUM WHITE CIRCLE
    'mercury': '\u263f',  # ☿ MERCURY
    'mho': '\u2127',  # ℧ INVERTED OHM SIGN
    'nabla': '\u2207',  # ∇ NABLA
    'natural': '\u266e',  # ♮ MUSIC NATURAL SIGN
    'neg': '\xac',  # ¬ NOT SIGN
    'neptune': '\u2646',  # ♆ NEPTUNE
    'nexists': '\u2204',  # ∄ THERE DOES NOT EXIST
    'notbackslash': '\u2340',  # ⍀ APL FUNCTIONAL SYMBOL BACKSLASH BAR
    'partial': '\u2202',  # ∂ PARTIAL DIFFERENTIAL
    'pisces': '\u2653',  # ♓ PISCES
    'pluto': '\u2647',  # ♇ PLUTO
    'pounds': '\xa3',  # £ POUND SIGN
    'prime': '\u2032',  # ′ PRIME
    'quarternote': '\u2669',  # ♩ QUARTER NOTE
    'rightmoon': '\u263d',  # ☽ FIRST QUARTER MOON
    'rmoustache': '\u23b1',  # ⎱ UPPER RIGHT OR LOWER LEFT CURLY BRACKET SECTION
    'sagittarius': '\u2650',  # ♐ SAGITTARIUS
    'saturn': '\u2644',  # ♄ SATURN
    'scorpio': '\u264f',  # ♏ SCORPIUS
    'second': '\u2033',  # ″ DOUBLE PRIME
    'sharp': '\u266f',  # ♯ MUSIC SHARP SIGN
    'smiley': '\u263a',  # ☺ WHITE SMILING FACE
    'spadesuit': '\u2660',  # ♠ BLACK SPADE SUIT
    'spddot': '\xa8',  # ¨ DIAERESIS
    'sphat': '^',  # ^ CIRCUMFLEX ACCENT
    'sphericalangle': '\u2222',  # ∢ SPHERICAL ANGLE
    'sptilde': '~',  # ~ TILDE
    'square': '\u25fb',  # ◻ WHITE MEDIUM SQUARE
    'sun': '\u263c',  # ☼ WHITE SUN WITH RAYS
    'surd': '\u221a',  # √ SQUARE ROOT
    'taurus': '\u2649',  # ♉ TAURUS
    'third': '\u2034',  # ‴ TRIPLE PRIME
    'top': '\u22a4',  # ⊤ DOWN TACK
    'twonotes': '\u266b',  # ♫ BEAMED EIGHTH NOTES
    'uranus': '\u2645',  # ♅ URANUS
    'varEarth': '\u2641',  # ♁ EARTH
    'varclubsuit': '\u2667',  # ♧ WHITE CLUB SUIT
    'vardiamondsuit': '\u2666',  # ♦ BLACK DIAMOND SUIT
    'varheartsuit': '\u2665',  # ♥ BLACK HEART SUIT
    'varspadesuit': '\u2664',  # ♤ WHITE SPADE SUIT
    'virgo': '\u264d',  # ♍ VIRGO
    'wasylozenge': '\u2311',  # ⌑ SQUARE LOZENGE
    'yen': '\xa5',  # ¥ YEN SIGN
    }

mathover = {
    'overbrace': '\u23de',  # ⏞ TOP CURLY BRACKET
    'wideparen': '\u23dc',  # ⏜ TOP PARENTHESIS
    }

mathpunct = {
    'ddots': '\u22f1',  # ⋱ DOWN RIGHT DIAGONAL ELLIPSIS
    'vdots': '\u22ee',  # ⋮ VERTICAL ELLIPSIS
    }

mathradical = {
    'sqrt[3]': '\u221b',  # ∛ CUBE ROOT
    'sqrt[4]': '\u221c',  # ∜ FOURTH ROOT
    }

mathrel = {
    'Bot': '\u2aeb',  # ⫫ DOUBLE UP TACK
    'Bumpeq': '\u224e',  # ≎ GEOMETRICALLY EQUIVALENT TO
    'Coloneqq': '\u2a74',  # ⩴ DOUBLE COLON EQUAL
    'Doteq': '\u2251',  # ≑ GEOMETRICALLY EQUAL TO
    'Downarrow': '\u21d3',  # ⇓ DOWNWARDS DOUBLE ARROW
    'Leftarrow': '\u21d0',  # ⇐ LEFTWARDS DOUBLE ARROW
    'Leftrightarrow': '\u21d4',  # ⇔ LEFT RIGHT DOUBLE ARROW
    'Lleftarrow': '\u21da',  # ⇚ LEFTWARDS TRIPLE ARROW
    'Longleftarrow': '\u27f8',  # ⟸ LONG LEFTWARDS DOUBLE ARROW
    'Longleftrightarrow': '\u27fa',  # ⟺ LONG LEFT RIGHT DOUBLE ARROW
    'Longmapsfrom': '\u27fd',  # ⟽ LONG LEFTWARDS DOUBLE ARROW FROM BAR
    'Longmapsto': '\u27fe',  # ⟾ LONG RIGHTWARDS DOUBLE ARROW FROM BAR
    'Longrightarrow': '\u27f9',  # ⟹ LONG RIGHTWARDS DOUBLE ARROW
    'Lsh': '\u21b0',  # ↰ UPWARDS ARROW WITH TIP LEFTWARDS
    'Mapsfrom': '\u2906',  # ⤆ LEFTWARDS DOUBLE ARROW FROM BAR
    'Mapsto': '\u2907',  # ⤇ RIGHTWARDS DOUBLE ARROW FROM BAR
    'Nearrow': '\u21d7',  # ⇗ NORTH EAST DOUBLE ARROW
    'Nwarrow': '\u21d6',  # ⇖ NORTH WEST DOUBLE ARROW
    'Perp': '\u2aeb',  # ⫫ DOUBLE UP TACK
    'Rightarrow': '\u21d2',  # ⇒ RIGHTWARDS DOUBLE ARROW
    'Rrightarrow': '\u21db',  # ⇛ RIGHTWARDS TRIPLE ARROW
    'Rsh': '\u21b1',  # ↱ UPWARDS ARROW WITH TIP RIGHTWARDS
    'Searrow': '\u21d8',  # ⇘ SOUTH EAST DOUBLE ARROW
    'Subset': '\u22d0',  # ⋐ DOUBLE SUBSET
    'Supset': '\u22d1',  # ⋑ DOUBLE SUPERSET
    'Swarrow': '\u21d9',  # ⇙ SOUTH WEST DOUBLE ARROW
    'Top': '\u2aea',  # ⫪ DOUBLE DOWN TACK
    'Uparrow': '\u21d1',  # ⇑ UPWARDS DOUBLE ARROW
    'Updownarrow': '\u21d5',  # ⇕ UP DOWN DOUBLE ARROW
    'VDash': '\u22ab',  # ⊫ DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE
    'Vdash': '\u22a9',  # ⊩ FORCES
    'Vvdash': '\u22aa',  # ⊪ TRIPLE VERTICAL BAR RIGHT TURNSTILE
    'apprge': '\u2273',  # ≳ GREATER-THAN OR EQUIVALENT TO
    'apprle': '\u2272',  # ≲ LESS-THAN OR EQUIVALENT TO
    'approx': '\u2248',  # ≈ ALMOST EQUAL TO
    'approxeq': '\u224a',  # ≊ ALMOST EQUAL OR EQUAL TO
    'asymp': '\u224d',  # ≍ EQUIVALENT TO
    'backepsilon': '\u220d',  # ∍ SMALL CONTAINS AS MEMBER
    'backsim': '\u223d',  # ∽ REVERSED TILDE
    'backsimeq': '\u22cd',  # ⋍ REVERSED TILDE EQUALS
    'barin': '\u22f6',  # ⋶ ELEMENT OF WITH OVERBAR
    'barleftharpoon': '\u296b',  # ⥫ LEFTWARDS HARPOON WITH BARB DOWN BELOW LONG DASH
    'barrightharpoon': '\u296d',  # ⥭ RIGHTWARDS HARPOON WITH BARB DOWN BELOW LONG DASH
    'because': '\u2235',  # ∵ BECAUSE
    'between': '\u226c',  # ≬ BETWEEN
    'blacktriangleleft': '\u25c2',  # ◂ BLACK LEFT-POINTING SMALL TRIANGLE
    'blacktriangleright': '\u25b8',  # ▸ BLACK RIGHT-POINTING SMALL TRIANGLE
    'bowtie': '\u22c8',  # ⋈ BOWTIE
    'bumpeq': '\u224f',  # ≏ DIFFERENCE BETWEEN
    'circeq': '\u2257',  # ≗ RING EQUAL TO
    'circlearrowleft': '\u21ba',  # ↺ ANTICLOCKWISE OPEN CIRCLE ARROW
    'circlearrowright': '\u21bb',  # ↻ CLOCKWISE OPEN CIRCLE ARROW
    'coloneq': '\u2254',  # ≔ COLON EQUALS
    'coloneqq': '\u2254',  # ≔ COLON EQUALS
    'cong': '\u2245',  # ≅ APPROXIMATELY EQUAL TO
    'corresponds': '\u2259',  # ≙ ESTIMATES
    'curlyeqprec': '\u22de',  # ⋞ EQUAL TO OR PRECEDES
    'curlyeqsucc': '\u22df',  # ⋟ EQUAL TO OR SUCCEEDS
    'curvearrowleft': '\u21b6',  # ↶ ANTICLOCKWISE TOP SEMICIRCLE ARROW
    'curvearrowright': '\u21b7',  # ↷ CLOCKWISE TOP SEMICIRCLE ARROW
    'dasharrow': '\u21e2',  # ⇢ RIGHTWARDS DASHED ARROW
    'dashleftarrow': '\u21e0',  # ⇠ LEFTWARDS DASHED ARROW
    'dashrightarrow': '\u21e2',  # ⇢ RIGHTWARDS DASHED ARROW
    'dashv': '\u22a3',  # ⊣ LEFT TACK
    'dlsh': '\u21b2',  # ↲ DOWNWARDS ARROW WITH TIP LEFTWARDS
    'doteq': '\u2250',  # ≐ APPROACHES THE LIMIT
    'doteqdot': '\u2251',  # ≑ GEOMETRICALLY EQUAL TO
    'downarrow': '\u2193',  # ↓ DOWNWARDS ARROW
    'downdownarrows': '\u21ca',  # ⇊ DOWNWARDS PAIRED ARROWS
    'downdownharpoons': '\u2965',  # ⥥ DOWNWARDS HARPOON WITH BARB LEFT BESIDE DOWNWARDS HARPOON WITH BARB RIGHT
    'downharpoonleft': '\u21c3',  # ⇃ DOWNWARDS HARPOON WITH BARB LEFTWARDS
    'downharpoonright': '\u21c2',  # ⇂ DOWNWARDS HARPOON WITH BARB RIGHTWARDS
    'downuparrows': '\u21f5',  # ⇵ DOWNWARDS ARROW LEFTWARDS OF UPWARDS ARROW
    'downupharpoons': '\u296f',  # ⥯ DOWNWARDS HARPOON WITH BARB LEFT BESIDE UPWARDS HARPOON WITH BARB RIGHT
    'drsh': '\u21b3',  # ↳ DOWNWARDS ARROW WITH TIP RIGHTWARDS
    'eqcirc': '\u2256',  # ≖ RING IN EQUAL TO
    'eqcolon': '\u2255',  # ≕ EQUALS COLON
    'eqqcolon': '\u2255',  # ≕ EQUALS COLON
    'eqsim': '\u2242',  # ≂ MINUS TILDE
    'eqslantgtr': '\u2a96',  # ⪖ SLANTED EQUAL TO OR GREATER-THAN
    'eqslantless': '\u2a95',  # ⪕ SLANTED EQUAL TO OR LESS-THAN
    'equiv': '\u2261',  # ≡ IDENTICAL TO
    'fallingdotseq': '\u2252',  # ≒ APPROXIMATELY EQUAL TO OR THE IMAGE OF
    'frown': '\u2322',  # ⌢ FROWN
    'ge': '\u2265',  # ≥ GREATER-THAN OR EQUAL TO
    'geq': '\u2265',  # ≥ GREATER-THAN OR EQUAL TO
    'geqq': '\u2267',  # ≧ GREATER-THAN OVER EQUAL TO
    'geqslant': '\u2a7e',  # ⩾ GREATER-THAN OR SLANTED EQUAL TO
    'gets': '\u2190',  # ← LEFTWARDS ARROW
    'gg': '\u226b',  # ≫ MUCH GREATER-THAN
    'ggcurly': '\u2abc',  # ⪼ DOUBLE SUCCEEDS
    'ggg': '\u22d9',  # ⋙ VERY MUCH GREATER-THAN
    'gggtr': '\u22d9',  # ⋙ VERY MUCH GREATER-THAN
    'gnapprox': '\u2a8a',  # ⪊ GREATER-THAN AND NOT APPROXIMATE
    'gneq': '\u2a88',  # ⪈ GREATER-THAN AND SINGLE-LINE NOT EQUAL TO
    'gneqq': '\u2269',  # ≩ GREATER-THAN BUT NOT EQUAL TO
    'gnsim': '\u22e7',  # ⋧ GREATER-THAN BUT NOT EQUIVALENT TO
    'gtrapprox': '\u2a86',  # ⪆ GREATER-THAN OR APPROXIMATE
    'gtreqless': '\u22db',  # ⋛ GREATER-THAN EQUAL TO OR LESS-THAN
    'gtreqqless': '\u2a8c',  # ⪌ GREATER-THAN ABOVE DOUBLE-LINE EQUAL ABOVE LESS-THAN
    'gtrless': '\u2277',  # ≷ GREATER-THAN OR LESS-THAN
    'gtrsim': '\u2273',  # ≳ GREATER-THAN OR EQUIVALENT TO
    'hash': '\u22d5',  # ⋕ EQUAL AND PARALLEL TO
    'hookleftarrow': '\u21a9',  # ↩ LEFTWARDS ARROW WITH HOOK
    'hookrightarrow': '\u21aa',  # ↪ RIGHTWARDS ARROW WITH HOOK
    'iddots': '\u22f0',  # ⋰ UP RIGHT DIAGONAL ELLIPSIS
    'impliedby': '\u27f8',  # ⟸ LONG LEFTWARDS DOUBLE ARROW
    'implies': '\u27f9',  # ⟹ LONG RIGHTWARDS DOUBLE ARROW
    'in': '\u2208',  # ∈ ELEMENT OF
    'le': '\u2264',  # ≤ LESS-THAN OR EQUAL TO
    'leadsto': '\u2933',  # ⤳ WAVE ARROW POINTING DIRECTLY RIGHT
    'leftarrow': '\u2190',  # ← LEFTWARDS ARROW
    'leftarrowtail': '\u21a2',  # ↢ LEFTWARDS ARROW WITH TAIL
    'leftarrowtriangle': '\u21fd',  # ⇽ LEFTWARDS OPEN-HEADED ARROW
    'leftbarharpoon': '\u296a',  # ⥪ LEFTWARDS HARPOON WITH BARB UP ABOVE LONG DASH
    'leftharpoondown': '\u21bd',  # ↽ LEFTWARDS HARPOON WITH BARB DOWNWARDS
    'leftharpoonup': '\u21bc',  # ↼ LEFTWARDS HARPOON WITH BARB UPWARDS
    'leftleftarrows': '\u21c7',  # ⇇ LEFTWARDS PAIRED ARROWS
    'leftleftharpoons': '\u2962',  # ⥢ LEFTWARDS HARPOON WITH BARB UP ABOVE LEFTWARDS HARPOON WITH BARB DOWN
    'leftrightarrow': '\u2194',  # ↔ LEFT RIGHT ARROW
    'leftrightarrows': '\u21c6',  # ⇆ LEFTWARDS ARROW OVER RIGHTWARDS ARROW
    'leftrightarrowtriangle': '\u21ff',  # ⇿ LEFT RIGHT OPEN-HEADED ARROW
    'leftrightharpoon': '\u294a',  # ⥊ LEFT BARB UP RIGHT BARB DOWN HARPOON
    'leftrightharpoons': '\u21cb',  # ⇋ LEFTWARDS HARPOON OVER RIGHTWARDS HARPOON
    'leftrightsquigarrow': '\u21ad',  # ↭ LEFT RIGHT WAVE ARROW
    'leftslice': '\u2aa6',  # ⪦ LESS-THAN CLOSED BY CURVE
    'leftsquigarrow': '\u21dc',  # ⇜ LEFTWARDS SQUIGGLE ARROW
    'leftturn': '\u21ba',  # ↺ ANTICLOCKWISE OPEN CIRCLE ARROW
    'leq': '\u2264',  # ≤ LESS-THAN OR EQUAL TO
    'leqq': '\u2266',  # ≦ LESS-THAN OVER EQUAL TO
    'leqslant': '\u2a7d',  # ⩽ LESS-THAN OR SLANTED EQUAL TO
    'lessapprox': '\u2a85',  # ⪅ LESS-THAN OR APPROXIMATE
    'lesseqgtr': '\u22da',  # ⋚ LESS-THAN EQUAL TO OR GREATER-THAN
    'lesseqqgtr': '\u2a8b',  # ⪋ LESS-THAN ABOVE DOUBLE-LINE EQUAL ABOVE GREATER-THAN
    'lessgtr': '\u2276',  # ≶ LESS-THAN OR GREATER-THAN
    'lesssim': '\u2272',  # ≲ LESS-THAN OR EQUIVALENT TO
    'lhd': '\u22b2',  # ⊲ NORMAL SUBGROUP OF
    'lightning': '\u21af',  # ↯ DOWNWARDS ZIGZAG ARROW
    'll': '\u226a',  # ≪ MUCH LESS-THAN
    'llcurly': '\u2abb',  # ⪻ DOUBLE PRECEDES
    'lll': '\u22d8',  # ⋘ VERY MUCH LESS-THAN
    'llless': '\u22d8',  # ⋘ VERY MUCH LESS-THAN
    'lnapprox': '\u2a89',  # ⪉ LESS-THAN AND NOT APPROXIMATE
    'lneq': '\u2a87',  # ⪇ LESS-THAN AND SINGLE-LINE NOT EQUAL TO
    'lneqq': '\u2268',  # ≨ LESS-THAN BUT NOT EQUAL TO
    'lnsim': '\u22e6',  # ⋦ LESS-THAN BUT NOT EQUIVALENT TO
    'longleftarrow': '\u27f5',  # ⟵ LONG LEFTWARDS ARROW
    'longleftrightarrow': '\u27f7',  # ⟷ LONG LEFT RIGHT ARROW
    'longmapsfrom': '\u27fb',  # ⟻ LONG LEFTWARDS ARROW FROM BAR
    'longmapsto': '\u27fc',  # ⟼ LONG RIGHTWARDS ARROW FROM BAR
    'longrightarrow': '\u27f6',  # ⟶ LONG RIGHTWARDS ARROW
    'looparrowleft': '\u21ab',  # ↫ LEFTWARDS ARROW WITH LOOP
    'looparrowright': '\u21ac',  # ↬ RIGHTWARDS ARROW WITH LOOP
    'lrtimes': '\u22c8',  # ⋈ BOWTIE
    'mapsfrom': '\u21a4',  # ↤ LEFTWARDS ARROW FROM BAR
    'mapsto': '\u21a6',  # ↦ RIGHTWARDS ARROW FROM BAR
    'mid': '\u2223',  # ∣ DIVIDES
    'models': '\u22a7',  # ⊧ MODELS
    'multimap': '\u22b8',  # ⊸ MULTIMAP
    'multimapboth': '\u29df',  # ⧟ DOUBLE-ENDED MULTIMAP
    'multimapdotbothA': '\u22b6',  # ⊶ ORIGINAL OF
    'multimapdotbothB': '\u22b7',  # ⊷ IMAGE OF
    'multimapinv': '\u27dc',  # ⟜ LEFT MULTIMAP
    'nLeftarrow': '\u21cd',  # ⇍ LEFTWARDS DOUBLE ARROW WITH STROKE
    'nLeftrightarrow': '\u21ce',  # ⇎ LEFT RIGHT DOUBLE ARROW WITH STROKE
    'nRightarrow': '\u21cf',  # ⇏ RIGHTWARDS DOUBLE ARROW WITH STROKE
    'nVDash': '\u22af',  # ⊯ NEGATED DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE
    'nVdash': '\u22ae',  # ⊮ DOES NOT FORCE
    'ncong': '\u2247',  # ≇ NEITHER APPROXIMATELY NOR ACTUALLY EQUAL TO
    'ne': '\u2260',  # ≠ NOT EQUAL TO
    'nearrow': '\u2197',  # ↗ NORTH EAST ARROW
    'neq': '\u2260',  # ≠ NOT EQUAL TO
    'ngeq': '\u2271',  # ≱ NEITHER GREATER-THAN NOR EQUAL TO
    'ngtr': '\u226f',  # ≯ NOT GREATER-THAN
    'ngtrless': '\u2279',  # ≹ NEITHER GREATER-THAN NOR LESS-THAN
    'ni': '\u220b',  # ∋ CONTAINS AS MEMBER
    'nleftarrow': '\u219a',  # ↚ LEFTWARDS ARROW WITH STROKE
    'nleftrightarrow': '\u21ae',  # ↮ LEFT RIGHT ARROW WITH STROKE
    'nleq': '\u2270',  # ≰ NEITHER LESS-THAN NOR EQUAL TO
    'nless': '\u226e',  # ≮ NOT LESS-THAN
    'nlessgtr': '\u2278',  # ≸ NEITHER LESS-THAN NOR GREATER-THAN
    'nmid': '\u2224',  # ∤ DOES NOT DIVIDE
    'notasymp': '\u226d',  # ≭ NOT EQUIVALENT TO
    'notin': '\u2209',  # ∉ NOT AN ELEMENT OF
    'notni': '\u220c',  # ∌ DOES NOT CONTAIN AS MEMBER
    'notowner': '\u220c',  # ∌ DOES NOT CONTAIN AS MEMBER
    'notslash': '\u233f',  # ⌿ APL FUNCTIONAL SYMBOL SLASH BAR
    'nparallel': '\u2226',  # ∦ NOT PARALLEL TO
    'nprec': '\u2280',  # ⊀ DOES NOT PRECEDE
    'npreceq': '\u22e0',  # ⋠ DOES NOT PRECEDE OR EQUAL
    'nrightarrow': '\u219b',  # ↛ RIGHTWARDS ARROW WITH STROKE
    'nsim': '\u2241',  # ≁ NOT TILDE
    'nsimeq': '\u2244',  # ≄ NOT ASYMPTOTICALLY EQUAL TO
    'nsubseteq': '\u2288',  # ⊈ NEITHER A SUBSET OF NOR EQUAL TO
    'nsucc': '\u2281',  # ⊁ DOES NOT SUCCEED
    'nsucceq': '\u22e1',  # ⋡ DOES NOT SUCCEED OR EQUAL
    'nsupseteq': '\u2289',  # ⊉ NEITHER A SUPERSET OF NOR EQUAL TO
    'ntriangleleft': '\u22ea',  # ⋪ NOT NORMAL SUBGROUP OF
    'ntrianglelefteq': '\u22ec',  # ⋬ NOT NORMAL SUBGROUP OF OR EQUAL TO
    'ntriangleright': '\u22eb',  # ⋫ DOES NOT CONTAIN AS NORMAL SUBGROUP
    'ntrianglerighteq': '\u22ed',  # ⋭ DOES NOT CONTAIN AS NORMAL SUBGROUP OR EQUAL
    'nvDash': '\u22ad',  # ⊭ NOT TRUE
    'nvdash': '\u22ac',  # ⊬ DOES NOT PROVE
    'nwarrow': '\u2196',  # ↖ NORTH WEST ARROW
    'owns': '\u220b',  # ∋ CONTAINS AS MEMBER
    'parallel': '\u2225',  # ∥ PARALLEL TO
    'perp': '\u27c2',  # ⟂ PERPENDICULAR
    'pitchfork': '\u22d4',  # ⋔ PITCHFORK
    'prec': '\u227a',  # ≺ PRECEDES
    'precapprox': '\u2ab7',  # ⪷ PRECEDES ABOVE ALMOST EQUAL TO
    'preccurlyeq': '\u227c',  # ≼ PRECEDES OR EQUAL TO
    'preceq': '\u2aaf',  # ⪯ PRECEDES ABOVE SINGLE-LINE EQUALS SIGN
    'preceqq': '\u2ab3',  # ⪳ PRECEDES ABOVE EQUALS SIGN
    'precnapprox': '\u2ab9',  # ⪹ PRECEDES ABOVE NOT ALMOST EQUAL TO
    'precneqq': '\u2ab5',  # ⪵ PRECEDES ABOVE NOT EQUAL TO
    'precnsim': '\u22e8',  # ⋨ PRECEDES BUT NOT EQUIVALENT TO
    'precsim': '\u227e',  # ≾ PRECEDES OR EQUIVALENT TO
    'propto': '\u221d',  # ∝ PROPORTIONAL TO
    'restriction': '\u21be',  # ↾ UPWARDS HARPOON WITH BARB RIGHTWARDS
    'rhd': '\u22b3',  # ⊳ CONTAINS AS NORMAL SUBGROUP
    'rightarrow': '\u2192',  # → RIGHTWARDS ARROW
    'rightarrowtail': '\u21a3',  # ↣ RIGHTWARDS ARROW WITH TAIL
    'rightarrowtriangle': '\u21fe',  # ⇾ RIGHTWARDS OPEN-HEADED ARROW
    'rightbarharpoon': '\u296c',  # ⥬ RIGHTWARDS HARPOON WITH BARB UP ABOVE LONG DASH
    'rightharpoondown': '\u21c1',  # ⇁ RIGHTWARDS HARPOON WITH BARB DOWNWARDS
    'rightharpoonup': '\u21c0',  # ⇀ RIGHTWARDS HARPOON WITH BARB UPWARDS
    'rightleftarrows': '\u21c4',  # ⇄ RIGHTWARDS ARROW OVER LEFTWARDS ARROW
    'rightleftharpoon': '\u294b',  # ⥋ LEFT BARB DOWN RIGHT BARB UP HARPOON
    'rightleftharpoons': '\u21cc',  # ⇌ RIGHTWARDS HARPOON OVER LEFTWARDS HARPOON
    'rightrightarrows': '\u21c9',  # ⇉ RIGHTWARDS PAIRED ARROWS
    'rightrightharpoons': '\u2964',  # ⥤ RIGHTWARDS HARPOON WITH BARB UP ABOVE RIGHTWARDS HARPOON WITH BARB DOWN
    'rightslice': '\u2aa7',  # ⪧ GREATER-THAN CLOSED BY CURVE
    'rightsquigarrow': '\u21dd',  # ⇝ RIGHTWARDS SQUIGGLE ARROW
    'rightturn': '\u21bb',  # ↻ CLOCKWISE OPEN CIRCLE ARROW
    'risingdotseq': '\u2253',  # ≓ IMAGE OF OR APPROXIMATELY EQUAL TO
    'searrow': '\u2198',  # ↘ SOUTH EAST ARROW
    'sim': '\u223c',  # ∼ TILDE OPERATOR
    'simeq': '\u2243',  # ≃ ASYMPTOTICALLY EQUAL TO
    'smile': '\u2323',  # ⌣ SMILE
    'sqsubset': '\u228f',  # ⊏ SQUARE IMAGE OF
    'sqsubseteq': '\u2291',  # ⊑ SQUARE IMAGE OF OR EQUAL TO
    'sqsupset': '\u2290',  # ⊐ SQUARE ORIGINAL OF
    'sqsupseteq': '\u2292',  # ⊒ SQUARE ORIGINAL OF OR EQUAL TO
    'strictfi': '\u297c',  # ⥼ LEFT FISH TAIL
    'strictif': '\u297d',  # ⥽ RIGHT FISH TAIL
    'subset': '\u2282',  # ⊂ SUBSET OF
    'subseteq': '\u2286',  # ⊆ SUBSET OF OR EQUAL TO
    'subseteqq': '\u2ac5',  # ⫅ SUBSET OF ABOVE EQUALS SIGN
    'subsetneq': '\u228a',  # ⊊ SUBSET OF WITH NOT EQUAL TO
    'subsetneqq': '\u2acb',  # ⫋ SUBSET OF ABOVE NOT EQUAL TO
    'succ': '\u227b',  # ≻ SUCCEEDS
    'succapprox': '\u2ab8',  # ⪸ SUCCEEDS ABOVE ALMOST EQUAL TO
    'succcurlyeq': '\u227d',  # ≽ SUCCEEDS OR EQUAL TO
    'succeq': '\u2ab0',  # ⪰ SUCCEEDS ABOVE SINGLE-LINE EQUALS SIGN
    'succeqq': '\u2ab4',  # ⪴ SUCCEEDS ABOVE EQUALS SIGN
    'succnapprox': '\u2aba',  # ⪺ SUCCEEDS ABOVE NOT ALMOST EQUAL TO
    'succneqq': '\u2ab6',  # ⪶ SUCCEEDS ABOVE NOT EQUAL TO
    'succnsim': '\u22e9',  # ⋩ SUCCEEDS BUT NOT EQUIVALENT TO
    'succsim': '\u227f',  # ≿ SUCCEEDS OR EQUIVALENT TO
    'supset': '\u2283',  # ⊃ SUPERSET OF
    'supseteq': '\u2287',  # ⊇ SUPERSET OF OR EQUAL TO
    'supseteqq': '\u2ac6',  # ⫆ SUPERSET OF ABOVE EQUALS SIGN
    'supsetneq': '\u228b',  # ⊋ SUPERSET OF WITH NOT EQUAL TO
    'supsetneqq': '\u2acc',  # ⫌ SUPERSET OF ABOVE NOT EQUAL TO
    'swarrow': '\u2199',  # ↙ SOUTH WEST ARROW
    'therefore': '\u2234',  # ∴ THEREFORE
    'to': '\u2192',  # → RIGHTWARDS ARROW
    'trianglelefteq': '\u22b4',  # ⊴ NORMAL SUBGROUP OF OR EQUAL TO
    'triangleq': '\u225c',  # ≜ DELTA EQUAL TO
    'trianglerighteq': '\u22b5',  # ⊵ CONTAINS AS NORMAL SUBGROUP OR EQUAL TO
    'twoheadleftarrow': '\u219e',  # ↞ LEFTWARDS TWO HEADED ARROW
    'twoheadrightarrow': '\u21a0',  # ↠ RIGHTWARDS TWO HEADED ARROW
    'uparrow': '\u2191',  # ↑ UPWARDS ARROW
    'updownarrow': '\u2195',  # ↕ UP DOWN ARROW
    'updownarrows': '\u21c5',  # ⇅ UPWARDS ARROW LEFTWARDS OF DOWNWARDS ARROW
    'updownharpoons': '\u296e',  # ⥮ UPWARDS HARPOON WITH BARB LEFT BESIDE DOWNWARDS HARPOON WITH BARB RIGHT
    'upharpoonleft': '\u21bf',  # ↿ UPWARDS HARPOON WITH BARB LEFTWARDS
    'upharpoonright': '\u21be',  # ↾ UPWARDS HARPOON WITH BARB RIGHTWARDS
    'upuparrows': '\u21c8',  # ⇈ UPWARDS PAIRED ARROWS
    'upupharpoons': '\u2963',  # ⥣ UPWARDS HARPOON WITH BARB LEFT BESIDE UPWARDS HARPOON WITH BARB RIGHT
    'vDash': '\u22a8',  # ⊨ TRUE
    'vartriangle': '\u25b5',  # ▵ WHITE UP-POINTING SMALL TRIANGLE
    'vartriangleleft': '\u22b2',  # ⊲ NORMAL SUBGROUP OF
    'vartriangleright': '\u22b3',  # ⊳ CONTAINS AS NORMAL SUBGROUP
    'vdash': '\u22a2',  # ⊢ RIGHT TACK
    'wasytherefore': '\u2234',  # ∴ THEREFORE
    }

mathunder = {
    'underbrace': '\u23df',  # ⏟ BOTTOM CURLY BRACKET
    }

space = {
    ' ': ' ',  #   SPACE
    ',': '\u2006',  #   SIX-PER-EM SPACE
    ':': '\u205f',  #   MEDIUM MATHEMATICAL SPACE
    'medspace': '\u205f',  #   MEDIUM MATHEMATICAL SPACE
    'quad': '\u2001',  #   EM QUAD
    'thinspace': '\u2006',  #   SIX-PER-EM SPACE
    }
