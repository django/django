from __future__ import absolute_import, division, print_function

import os
import sys

from cffi import FFI


include_dirs = [os.path.join("extras", "libargon2", "include")]
use_system_argon2 = os.environ.get("ARGON2_CFFI_USE_SYSTEM", "0") == "1"
if use_system_argon2:
    include_dirs = []

# Add vendored integer types headers.
if "win32" in str(sys.platform).lower():
    int_base = os.path.join("extras", "msinttypes")
    inttypes = os.path.join(int_base, "inttypes")
    stdint = os.path.join(int_base, "stdint")
    vi = sys.version_info[0:2]
    if vi in [(2, 6), (2, 7)]:
        # VS 2008 needs both.
        include_dirs += [inttypes, stdint]
    elif vi in [(3, 3), (3, 4)]:
        # VS 2010 needs only inttypes.h
        include_dirs += [inttypes]


ffi = FFI()
ffi.set_source(
    "_ffi",
    "#include <argon2.h>",
    include_dirs=include_dirs,
    libraries=["argon2"],
)

ffi.cdef(
    """\
typedef enum Argon2_type {
    Argon2_d = ...,
    Argon2_i = ...,
    Argon2_id = ...,
} argon2_type;
typedef enum Argon2_version {
    ARGON2_VERSION_10 = ...,
    ARGON2_VERSION_13 = ...,
    ARGON2_VERSION_NUMBER = ...
} argon2_version;

int argon2_hash(const uint32_t t_cost, const uint32_t m_cost,
                const uint32_t parallelism, const void *pwd,
                const size_t pwdlen, const void *salt,
                const size_t saltlen, void *hash,
                const size_t hashlen, char *encoded,
                const size_t encodedlen, argon2_type type,
                const uint32_t version);

int argon2_verify(const char *encoded, const void *pwd,
                  const size_t pwdlen, argon2_type type);

const char *argon2_error_message(int error_code);


typedef int (*allocate_fptr)(uint8_t **memory, size_t bytes_to_allocate);
typedef void (*deallocate_fptr)(uint8_t *memory, size_t bytes_to_allocate);

typedef struct Argon2_Context {
    uint8_t *out;    /* output array */
    uint32_t outlen; /* digest length */

    uint8_t *pwd;    /* password array */
    uint32_t pwdlen; /* password length */

    uint8_t *salt;    /* salt array */
    uint32_t saltlen; /* salt length */

    uint8_t *secret;    /* key array */
    uint32_t secretlen; /* key length */

    uint8_t *ad;    /* associated data array */
    uint32_t adlen; /* associated data length */

    uint32_t t_cost;  /* number of passes */
    uint32_t m_cost;  /* amount of memory requested (KB) */
    uint32_t lanes;   /* number of lanes */
    uint32_t threads; /* maximum number of threads */

    uint32_t version; /* version number */

    allocate_fptr allocate_cbk; /* pointer to memory allocator */
    deallocate_fptr free_cbk;   /* pointer to memory deallocator */

    uint32_t flags; /* array of bool options */
} argon2_context;

int argon2_ctx(argon2_context *context, argon2_type type);

/* Error codes */
typedef enum Argon2_ErrorCodes {
    ARGON2_OK = ...,

    ARGON2_OUTPUT_PTR_NULL = ...,

    ARGON2_OUTPUT_TOO_SHORT = ...,
    ARGON2_OUTPUT_TOO_LONG = ...,

    ARGON2_PWD_TOO_SHORT = ...,
    ARGON2_PWD_TOO_LONG = ...,

    ARGON2_SALT_TOO_SHORT = ...,
    ARGON2_SALT_TOO_LONG = ...,

    ARGON2_AD_TOO_SHORT = ...,
    ARGON2_AD_TOO_LONG = ...,

    ARGON2_SECRET_TOO_SHORT = ...,
    ARGON2_SECRET_TOO_LONG = ...,

    ARGON2_TIME_TOO_SMALL = ...,
    ARGON2_TIME_TOO_LARGE = ...,

    ARGON2_MEMORY_TOO_LITTLE = ...,
    ARGON2_MEMORY_TOO_MUCH = ...,

    ARGON2_LANES_TOO_FEW = ...,
    ARGON2_LANES_TOO_MANY = ...,

    ARGON2_PWD_PTR_MISMATCH = ...,    /* NULL ptr with non-zero length */
    ARGON2_SALT_PTR_MISMATCH = ...,   /* NULL ptr with non-zero length */
    ARGON2_SECRET_PTR_MISMATCH = ..., /* NULL ptr with non-zero length */
    ARGON2_AD_PTR_MISMATCH = ...,     /* NULL ptr with non-zero length */

    ARGON2_MEMORY_ALLOCATION_ERROR = ...,

    ARGON2_FREE_MEMORY_CBK_NULL = ...,
    ARGON2_ALLOCATE_MEMORY_CBK_NULL = ...,

    ARGON2_INCORRECT_PARAMETER = ...,
    ARGON2_INCORRECT_TYPE = ...,

    ARGON2_OUT_PTR_MISMATCH = ...,

    ARGON2_THREADS_TOO_FEW = ...,
    ARGON2_THREADS_TOO_MANY = ...,

    ARGON2_MISSING_ARGS = ...,

    ARGON2_ENCODING_FAIL = ...,

    ARGON2_DECODING_FAIL = ...,

    ARGON2_THREAD_FAIL = ...,

    ARGON2_DECODING_LENGTH_FAIL= ...,

    ARGON2_VERIFY_MISMATCH = ...,
} argon2_error_codes;

#define ARGON2_FLAG_CLEAR_PASSWORD ...
#define ARGON2_FLAG_CLEAR_SECRET ...
#define ARGON2_DEFAULT_FLAGS ...

#define ARGON2_MIN_LANES ...
#define ARGON2_MAX_LANES ...
#define ARGON2_MIN_THREADS ...
#define ARGON2_MAX_THREADS  ...
#define ARGON2_SYNC_POINTS  ...
#define ARGON2_MIN_OUTLEN ...
#define ARGON2_MAX_OUTLEN ...
#define ARGON2_MIN_MEMORY ...
#define ARGON2_MAX_MEMORY_BITS ...
#define ARGON2_MAX_MEMORY ...
#define ARGON2_MIN_TIME ...
#define ARGON2_MAX_TIME ...
#define ARGON2_MIN_PWD_LENGTH ...
#define ARGON2_MAX_PWD_LENGTH ...
#define ARGON2_MIN_AD_LENGTH ...
#define ARGON2_MAX_AD_LENGTH ...
#define ARGON2_MIN_SALT_LENGTH ...
#define ARGON2_MAX_SALT_LENGTH ...
#define ARGON2_MIN_SECRET ...
#define ARGON2_MAX_SECRET ...

uint32_t argon2_encodedlen(uint32_t t_cost, uint32_t m_cost,
                           uint32_t parallelism, uint32_t saltlen,
                           uint32_t hashlen, argon2_type type);

"""
)

if __name__ == "__main__":
    ffi.compile()
