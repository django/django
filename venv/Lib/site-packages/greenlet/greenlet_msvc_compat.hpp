#ifndef GREENLET_MSVC_COMPAT_HPP
#define GREENLET_MSVC_COMPAT_HPP
/*
 * Support for MSVC on Windows.
 *
 * Beginning with Python 3.14, some of the internal
 * include files we need are not compatible with MSVC
 * in C++ mode:
 *
 *   internal\pycore_stackref.h(253): error C4576: a parenthesized type
 *    followed by an initializer list is a non-standard explicit type conversion syntax
 *
 * This file is included from ``internal/pycore_interpframe.h``, which
 * we need for the ``_PyFrame_IsIncomplete`` API.
 *
 * Unfortunately, that API is a ``static inline`` function, as are a
 * bunch of the functions it calls. The only solution seems to be to
 * copy those definitions and the supporting inline functions here.
 *
 * Now, this makes us VERY fragile to changes in those functions. Because
 * they're internal and static, the CPython devs might feel free to change
 * them in even minor versions, meaning that we could runtime link and load,
 * but still crash. We have that problem on all platforms though. It's just worse
 * here because we have to keep copying the updated definitions.
 */
#include <Python.h>
#include "greenlet_cpython_compat.hpp"

// This file is only included on 3.14+

extern "C" {

// pycore_code.h ----------------
#define _PyCode_CODE(CO) _Py_RVALUE((_Py_CODEUNIT *)(CO)->co_code_adaptive)

#ifdef Py_GIL_DISABLED
static inline _PyCodeArray *
_PyCode_GetTLBCArray(PyCodeObject *co)
{
    return _Py_STATIC_CAST(_PyCodeArray *,
                           _Py_atomic_load_ptr_acquire(&co->co_tlbc));
}
#endif
// End pycore_code.h ----------

// pycore_interpframe.h ----------
#if !defined(Py_GIL_DISABLED) && defined(Py_STACKREF_DEBUG)

#define Py_TAG_BITS 0
#else
#define Py_TAG_BITS     ((uintptr_t)1)
#define Py_TAG_DEFERRED (1)
#endif


static const _PyStackRef PyStackRef_NULL = { .bits = Py_TAG_DEFERRED};
#define PyStackRef_IsNull(stackref) ((stackref).bits == PyStackRef_NULL.bits)

static inline PyObject *
PyStackRef_AsPyObjectBorrow(_PyStackRef stackref)
{
    PyObject *cleared = ((PyObject *)((stackref).bits & (~Py_TAG_BITS)));
    return cleared;
}

static inline PyCodeObject *_PyFrame_GetCode(_PyInterpreterFrame *f) {
    assert(!PyStackRef_IsNull(f->f_executable));
    PyObject *executable = PyStackRef_AsPyObjectBorrow(f->f_executable);
    assert(PyCode_Check(executable));
    return (PyCodeObject *)executable;
}


static inline _Py_CODEUNIT *
_PyFrame_GetBytecode(_PyInterpreterFrame *f)
{
#ifdef Py_GIL_DISABLED
    PyCodeObject *co = _PyFrame_GetCode(f);
    _PyCodeArray *tlbc = _PyCode_GetTLBCArray(co);
    assert(f->tlbc_index >= 0 && f->tlbc_index < tlbc->size);
    return (_Py_CODEUNIT *)tlbc->entries[f->tlbc_index];
#else
    return _PyCode_CODE(_PyFrame_GetCode(f));
#endif
}

static inline bool //_Py_NO_SANITIZE_THREAD
_PyFrame_IsIncomplete(_PyInterpreterFrame *frame)
{
    if (frame->owner >= FRAME_OWNED_BY_INTERPRETER) {
        return true;
    }
    return frame->owner != FRAME_OWNED_BY_GENERATOR &&
           frame->instr_ptr < _PyFrame_GetBytecode(frame) +
                                  _PyFrame_GetCode(frame)->_co_firsttraceable;
}
// pycore_interpframe.h ----------

}
#endif // GREENLET_MSVC_COMPAT_HPP
