from __future__ import division, absolute_import, print_function

# Code common to build tools
import sys
import warnings
import copy
import binascii

from numpy.distutils.misc_util import mingw32


#-------------------
# Versioning support
#-------------------
# How to change C_API_VERSION ?
#   - increase C_API_VERSION value
#   - record the hash for the new C API with the script cversions.py
#   and add the hash to cversions.txt
# The hash values are used to remind developers when the C API number was not
# updated - generates a MismatchCAPIWarning warning which is turned into an
# exception for released version.

# Binary compatibility version number. This number is increased whenever the
# C-API is changed such that binary compatibility is broken, i.e. whenever a
# recompile of extension modules is needed.
C_ABI_VERSION = 0x01000009

# Minor API version.  This number is increased whenever a change is made to the
# C-API -- whether it breaks binary compatibility or not.  Some changes, such
# as adding a function pointer to the end of the function table, can be made
# without breaking binary compatibility.  In this case, only the C_API_VERSION
# (*not* C_ABI_VERSION) would be increased.  Whenever binary compatibility is
# broken, both C_API_VERSION and C_ABI_VERSION should be increased.
#
# 0x00000008 - 1.7.x
# 0x00000009 - 1.8.x
# 0x00000009 - 1.9.x
# 0x0000000a - 1.10.x
# 0x0000000a - 1.11.x
# 0x0000000a - 1.12.x
# 0x0000000b - 1.13.x
# 0x0000000c - 1.14.x
# 0x0000000c - 1.15.x
# 0x0000000d - 1.16.x
C_API_VERSION = 0x0000000d

class MismatchCAPIWarning(Warning):
    pass

def is_released(config):
    """Return True if a released version of numpy is detected."""
    from distutils.version import LooseVersion

    v = config.get_version('../version.py')
    if v is None:
        raise ValueError("Could not get version")
    pv = LooseVersion(vstring=v).version
    if len(pv) > 3:
        return False
    return True

def get_api_versions(apiversion, codegen_dir):
    """
    Return current C API checksum and the recorded checksum.

    Return current C API checksum and the recorded checksum for the given
    version of the C API version.

    """
    # Compute the hash of the current API as defined in the .txt files in
    # code_generators
    sys.path.insert(0, codegen_dir)
    try:
        m = __import__('genapi')
        numpy_api = __import__('numpy_api')
        curapi_hash = m.fullapi_hash(numpy_api.full_api)
        apis_hash = m.get_versions_hash()
    finally:
        del sys.path[0]

    return curapi_hash, apis_hash[apiversion]

def check_api_version(apiversion, codegen_dir):
    """Emits a MismacthCAPIWarning if the C API version needs updating."""
    curapi_hash, api_hash = get_api_versions(apiversion, codegen_dir)

    # If different hash, it means that the api .txt files in
    # codegen_dir have been updated without the API version being
    # updated. Any modification in those .txt files should be reflected
    # in the api and eventually abi versions.
    # To compute the checksum of the current API, use
    # code_generators/cversions.py script
    if not curapi_hash == api_hash:
        msg = ("API mismatch detected, the C API version "
               "numbers have to be updated. Current C api version is %d, "
               "with checksum %s, but recorded checksum for C API version %d in "
               "codegen_dir/cversions.txt is %s. If functions were added in the "
               "C API, you have to update C_API_VERSION  in %s."
               )
        warnings.warn(msg % (apiversion, curapi_hash, apiversion, api_hash,
                             __file__),
                      MismatchCAPIWarning, stacklevel=2)
# Mandatory functions: if not found, fail the build
MANDATORY_FUNCS = ["sin", "cos", "tan", "sinh", "cosh", "tanh", "fabs",
        "floor", "ceil", "sqrt", "log10", "log", "exp", "asin",
        "acos", "atan", "fmod", 'modf', 'frexp', 'ldexp']

# Standard functions which may not be available and for which we have a
# replacement implementation. Note that some of these are C99 functions.
OPTIONAL_STDFUNCS = ["expm1", "log1p", "acosh", "asinh", "atanh",
        "rint", "trunc", "exp2", "log2", "hypot", "atan2", "pow",
        "copysign", "nextafter", "ftello", "fseeko",
        "strtoll", "strtoull", "cbrt", "strtold_l", "fallocate",
        "backtrace", "madvise"]


OPTIONAL_HEADERS = [
# sse headers only enabled automatically on amd64/x32 builds
                "xmmintrin.h",  # SSE
                "emmintrin.h",  # SSE2
                "features.h",  # for glibc version linux
                "xlocale.h",  # see GH#8367
                "dlfcn.h", # dladdr
                "sys/mman.h", #madvise
]

# optional gcc compiler builtins and their call arguments and optional a
# required header and definition name (HAVE_ prepended)
# call arguments are required as the compiler will do strict signature checking
OPTIONAL_INTRINSICS = [("__builtin_isnan", '5.'),
                       ("__builtin_isinf", '5.'),
                       ("__builtin_isfinite", '5.'),
                       ("__builtin_bswap32", '5u'),
                       ("__builtin_bswap64", '5u'),
                       ("__builtin_expect", '5, 0'),
                       ("__builtin_mul_overflow", '5, 5, (int*)5'),
                       # broken on OSX 10.11, make sure its not optimized away
                       ("volatile int r = __builtin_cpu_supports", '"sse"',
                        "stdio.h", "__BUILTIN_CPU_SUPPORTS"),
                       # MMX only needed for icc, but some clangs don't have it
                       ("_m_from_int64", '0', "emmintrin.h"),
                       ("_mm_load_ps", '(float*)0', "xmmintrin.h"),  # SSE
                       ("_mm_prefetch", '(float*)0, _MM_HINT_NTA',
                        "xmmintrin.h"),  # SSE
                       ("_mm_load_pd", '(double*)0', "emmintrin.h"),  # SSE2
                       ("__builtin_prefetch", "(float*)0, 0, 3"),
                       # check that the linker can handle avx
                       ("__asm__ volatile", '"vpand %xmm1, %xmm2, %xmm3"',
                        "stdio.h", "LINK_AVX"),
                       ("__asm__ volatile", '"vpand %ymm1, %ymm2, %ymm3"',
                        "stdio.h", "LINK_AVX2"),
                       ("__asm__ volatile", '"xgetbv"', "stdio.h", "XGETBV"),
                       ]

# function attributes
# tested via "int %s %s(void *);" % (attribute, name)
# function name will be converted to HAVE_<upper-case-name> preprocessor macro
OPTIONAL_FUNCTION_ATTRIBUTES = [('__attribute__((optimize("unroll-loops")))',
                                'attribute_optimize_unroll_loops'),
                                ('__attribute__((optimize("O3")))',
                                 'attribute_optimize_opt_3'),
                                ('__attribute__((nonnull (1)))',
                                 'attribute_nonnull'),
                                ('__attribute__((target ("avx")))',
                                 'attribute_target_avx'),
                                ('__attribute__((target ("avx2")))',
                                 'attribute_target_avx2'),
                                ]

# variable attributes tested via "int %s a" % attribute
OPTIONAL_VARIABLE_ATTRIBUTES = ["__thread", "__declspec(thread)"]

# Subset of OPTIONAL_STDFUNCS which may already have HAVE_* defined by Python.h
OPTIONAL_STDFUNCS_MAYBE = [
    "expm1", "log1p", "acosh", "atanh", "asinh", "hypot", "copysign",
    "ftello", "fseeko"
    ]

# C99 functions: float and long double versions
C99_FUNCS = [
    "sin", "cos", "tan", "sinh", "cosh", "tanh", "fabs", "floor", "ceil",
    "rint", "trunc", "sqrt", "log10", "log", "log1p", "exp", "expm1",
    "asin", "acos", "atan", "asinh", "acosh", "atanh", "hypot", "atan2",
    "pow", "fmod", "modf", 'frexp', 'ldexp', "exp2", "log2", "copysign",
    "nextafter", "cbrt"
    ]
C99_FUNCS_SINGLE = [f + 'f' for f in C99_FUNCS]
C99_FUNCS_EXTENDED = [f + 'l' for f in C99_FUNCS]
C99_COMPLEX_TYPES = [
    'complex double', 'complex float', 'complex long double'
    ]
C99_COMPLEX_FUNCS = [
    "cabs", "cacos", "cacosh", "carg", "casin", "casinh", "catan",
    "catanh", "ccos", "ccosh", "cexp", "cimag", "clog", "conj", "cpow",
    "cproj", "creal", "csin", "csinh", "csqrt", "ctan", "ctanh"
    ]

def fname2def(name):
    return "HAVE_%s" % name.upper()

def sym2def(symbol):
    define = symbol.replace(' ', '')
    return define.upper()

def type2def(symbol):
    define = symbol.replace(' ', '_')
    return define.upper()

# Code to detect long double representation taken from MPFR m4 macro
def check_long_double_representation(cmd):
    cmd._check_compiler()
    body = LONG_DOUBLE_REPRESENTATION_SRC % {'type': 'long double'}

    # Disable whole program optimization (the default on vs2015, with python 3.5+)
    # which generates intermediary object files and prevents checking the
    # float representation.
    if sys.platform == "win32" and not mingw32():
        try:
            cmd.compiler.compile_options.remove("/GL")
        except (AttributeError, ValueError):
            pass

    # Disable multi-file interprocedural optimization in the Intel compiler on Linux
    # which generates intermediary object files and prevents checking the
    # float representation.
    elif (sys.platform != "win32" 
            and cmd.compiler.compiler_type.startswith('intel') 
            and '-ipo' in cmd.compiler.cc_exe):        
        newcompiler = cmd.compiler.cc_exe.replace(' -ipo', '')
        cmd.compiler.set_executables(
            compiler=newcompiler,
            compiler_so=newcompiler,
            compiler_cxx=newcompiler,
            linker_exe=newcompiler,
            linker_so=newcompiler + ' -shared'
        )

    # We need to use _compile because we need the object filename
    src, obj = cmd._compile(body, None, None, 'c')
    try:
        ltype = long_double_representation(pyod(obj))
        return ltype
    except ValueError:
        # try linking to support CC="gcc -flto" or icc -ipo
        # struct needs to be volatile so it isn't optimized away
        body = body.replace('struct', 'volatile struct')
        body += "int main(void) { return 0; }\n"
        src, obj = cmd._compile(body, None, None, 'c')
        cmd.temp_files.append("_configtest")
        cmd.compiler.link_executable([obj], "_configtest")
        ltype = long_double_representation(pyod("_configtest"))
        return ltype
    finally:
        cmd._clean()

LONG_DOUBLE_REPRESENTATION_SRC = r"""
/* "before" is 16 bytes to ensure there's no padding between it and "x".
 *    We're not expecting any "long double" bigger than 16 bytes or with
 *       alignment requirements stricter than 16 bytes.  */
typedef %(type)s test_type;

struct {
        char         before[16];
        test_type    x;
        char         after[8];
} foo = {
        { '\0', '\0', '\0', '\0', '\0', '\0', '\0', '\0',
          '\001', '\043', '\105', '\147', '\211', '\253', '\315', '\357' },
        -123456789.0,
        { '\376', '\334', '\272', '\230', '\166', '\124', '\062', '\020' }
};
"""

def pyod(filename):
    """Python implementation of the od UNIX utility (od -b, more exactly).

    Parameters
    ----------
    filename : str
        name of the file to get the dump from.

    Returns
    -------
    out : seq
        list of lines of od output

    Note
    ----
    We only implement enough to get the necessary information for long double
    representation, this is not intended as a compatible replacement for od.
    """
    def _pyod2():
        out = []

        fid = open(filename, 'rb')
        try:
            yo = [int(oct(int(binascii.b2a_hex(o), 16))) for o in fid.read()]
            for i in range(0, len(yo), 16):
                line = ['%07d' % int(oct(i))]
                line.extend(['%03d' % c for c in yo[i:i+16]])
                out.append(" ".join(line))
            return out
        finally:
            fid.close()

    def _pyod3():
        out = []

        fid = open(filename, 'rb')
        try:
            yo2 = [oct(o)[2:] for o in fid.read()]
            for i in range(0, len(yo2), 16):
                line = ['%07d' % int(oct(i)[2:])]
                line.extend(['%03d' % int(c) for c in yo2[i:i+16]])
                out.append(" ".join(line))
            return out
        finally:
            fid.close()

    if sys.version_info[0] < 3:
        return _pyod2()
    else:
        return _pyod3()

_BEFORE_SEQ = ['000', '000', '000', '000', '000', '000', '000', '000',
              '001', '043', '105', '147', '211', '253', '315', '357']
_AFTER_SEQ = ['376', '334', '272', '230', '166', '124', '062', '020']

_IEEE_DOUBLE_BE = ['301', '235', '157', '064', '124', '000', '000', '000']
_IEEE_DOUBLE_LE = _IEEE_DOUBLE_BE[::-1]
_INTEL_EXTENDED_12B = ['000', '000', '000', '000', '240', '242', '171', '353',
                       '031', '300', '000', '000']
_INTEL_EXTENDED_16B = ['000', '000', '000', '000', '240', '242', '171', '353',
                       '031', '300', '000', '000', '000', '000', '000', '000']
_MOTOROLA_EXTENDED_12B = ['300', '031', '000', '000', '353', '171',
                          '242', '240', '000', '000', '000', '000']
_IEEE_QUAD_PREC_BE = ['300', '031', '326', '363', '105', '100', '000', '000',
                      '000', '000', '000', '000', '000', '000', '000', '000']
_IEEE_QUAD_PREC_LE = _IEEE_QUAD_PREC_BE[::-1]
_IBM_DOUBLE_DOUBLE_BE = (['301', '235', '157', '064', '124', '000', '000', '000'] +
                     ['000'] * 8)
_IBM_DOUBLE_DOUBLE_LE = (['000', '000', '000', '124', '064', '157', '235', '301'] +
                     ['000'] * 8)

def long_double_representation(lines):
    """Given a binary dump as given by GNU od -b, look for long double
    representation."""

    # Read contains a list of 32 items, each item is a byte (in octal
    # representation, as a string). We 'slide' over the output until read is of
    # the form before_seq + content + after_sequence, where content is the long double
    # representation:
    #  - content is 12 bytes: 80 bits Intel representation
    #  - content is 16 bytes: 80 bits Intel representation (64 bits) or quad precision
    #  - content is 8 bytes: same as double (not implemented yet)
    read = [''] * 32
    saw = None
    for line in lines:
        # we skip the first word, as od -b output an index at the beginning of
        # each line
        for w in line.split()[1:]:
            read.pop(0)
            read.append(w)

            # If the end of read is equal to the after_sequence, read contains
            # the long double
            if read[-8:] == _AFTER_SEQ:
                saw = copy.copy(read)
                # if the content was 12 bytes, we only have 32 - 8 - 12 = 12
                # "before" bytes. In other words the first 4 "before" bytes went
                # past the sliding window.
                if read[:12] == _BEFORE_SEQ[4:]:
                    if read[12:-8] == _INTEL_EXTENDED_12B:
                        return 'INTEL_EXTENDED_12_BYTES_LE'
                    if read[12:-8] == _MOTOROLA_EXTENDED_12B:
                        return 'MOTOROLA_EXTENDED_12_BYTES_BE'
                # if the content was 16 bytes, we are left with 32-8-16 = 16
                # "before" bytes, so 8 went past the sliding window.
                elif read[:8] == _BEFORE_SEQ[8:]:
                    if read[8:-8] == _INTEL_EXTENDED_16B:
                        return 'INTEL_EXTENDED_16_BYTES_LE'
                    elif read[8:-8] == _IEEE_QUAD_PREC_BE:
                        return 'IEEE_QUAD_BE'
                    elif read[8:-8] == _IEEE_QUAD_PREC_LE:
                        return 'IEEE_QUAD_LE'
                    elif read[8:-8] == _IBM_DOUBLE_DOUBLE_LE:
                        return 'IBM_DOUBLE_DOUBLE_LE'
                    elif read[8:-8] == _IBM_DOUBLE_DOUBLE_BE:
                        return 'IBM_DOUBLE_DOUBLE_BE'
                # if the content was 8 bytes, left with 32-8-8 = 16 bytes
                elif read[:16] == _BEFORE_SEQ:
                    if read[16:-8] == _IEEE_DOUBLE_LE:
                        return 'IEEE_DOUBLE_LE'
                    elif read[16:-8] == _IEEE_DOUBLE_BE:
                        return 'IEEE_DOUBLE_BE'

    if saw is not None:
        raise ValueError("Unrecognized format (%s)" % saw)
    else:
        # We never detected the after_sequence
        raise ValueError("Could not lock sequences (%s)" % saw)
