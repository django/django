/* -*- indent-tabs-mode: nil; tab-width: 4; -*- */
/* Format with:
 *  clang-format -i --style=file src/greenlet/greenlet.c
 *
 *
 * Fix missing braces with:
 *   clang-tidy src/greenlet/greenlet.c -fix -checks="readability-braces-around-statements"
*/
#include <cstdlib>
#include <string>
#include <algorithm>
#include <exception>


#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "structmember.h" // PyMemberDef

#include "greenlet_internal.hpp"
// Code after this point can assume access to things declared in stdint.h,
// including the fixed-width types. This goes for the platform-specific switch functions
// as well.
#include "greenlet_refs.hpp"
#include "greenlet_slp_switch.hpp"

#include "greenlet_thread_support.hpp"
#include "TGreenlet.hpp"

#include "TGreenletGlobals.cpp"

#include "TGreenlet.cpp"
#include "TMainGreenlet.cpp"
#include "TUserGreenlet.cpp"
#include "TBrokenGreenlet.cpp"
#include "TExceptionState.cpp"
#include "TPythonState.cpp"
#include "TStackState.cpp"

#include "TThreadState.hpp"
#include "TThreadStateCreator.hpp"
#include "TThreadStateDestroy.cpp"

#include "PyGreenlet.cpp"
#include "PyGreenletUnswitchable.cpp"
#include "CObjects.cpp"

using greenlet::LockGuard;
using greenlet::LockInitError;
using greenlet::PyErrOccurred;
using greenlet::Require;

using greenlet::g_handle_exit;
using greenlet::single_result;

using greenlet::Greenlet;
using greenlet::UserGreenlet;
using greenlet::MainGreenlet;
using greenlet::BrokenGreenlet;
using greenlet::ThreadState;
using greenlet::PythonState;



// ******* Implementation of things from included files
template<typename T, greenlet::refs::TypeChecker TC>
greenlet::refs::_BorrowedGreenlet<T, TC>& greenlet::refs::_BorrowedGreenlet<T, TC>::operator=(const greenlet::refs::BorrowedObject& other)
{
    this->_set_raw_pointer(static_cast<PyObject*>(other));
    return *this;
}

template <typename T, greenlet::refs::TypeChecker TC>
inline greenlet::refs::_BorrowedGreenlet<T, TC>::operator Greenlet*() const noexcept
{
    if (!this->p) {
        return nullptr;
    }
    return reinterpret_cast<PyGreenlet*>(this->p)->pimpl;
}

template<typename T, greenlet::refs::TypeChecker TC>
greenlet::refs::_BorrowedGreenlet<T, TC>::_BorrowedGreenlet(const BorrowedObject& p)
    : BorrowedReference<T, TC>(nullptr)
{

    this->_set_raw_pointer(p.borrow());
}

template <typename T, greenlet::refs::TypeChecker TC>
inline greenlet::refs::_OwnedGreenlet<T, TC>::operator Greenlet*() const noexcept
{
    if (!this->p) {
        return nullptr;
    }
    return reinterpret_cast<PyGreenlet*>(this->p)->pimpl;
}



#ifdef __clang__
#    pragma clang diagnostic push
#    pragma clang diagnostic ignored "-Wmissing-field-initializers"
#    pragma clang diagnostic ignored "-Wwritable-strings"
#elif defined(__GNUC__)
#    pragma GCC diagnostic push
//  warning: ISO C++ forbids converting a string constant to ‘char*’
// (The python APIs aren't const correct and accept writable char*)
#    pragma GCC diagnostic ignored "-Wwrite-strings"
#endif


/***********************************************************

A PyGreenlet is a range of C stack addresses that must be
saved and restored in such a way that the full range of the
stack contains valid data when we switch to it.

Stack layout for a greenlet:

               |     ^^^       |
               |  older data   |
               |               |
  stack_stop . |_______________|
        .      |               |
        .      | greenlet data |
        .      |   in stack    |
        .    * |_______________| . .  _____________  stack_copy + stack_saved
        .      |               |     |             |
        .      |     data      |     |greenlet data|
        .      |   unrelated   |     |    saved    |
        .      |      to       |     |   in heap   |
 stack_start . |     this      | . . |_____________| stack_copy
               |   greenlet    |
               |               |
               |  newer data   |
               |     vvv       |


Note that a greenlet's stack data is typically partly at its correct
place in the stack, and partly saved away in the heap, but always in
the above configuration: two blocks, the more recent one in the heap
and the older one still in the stack (either block may be empty).

Greenlets are chained: each points to the previous greenlet, which is
the one that owns the data currently in the C stack above my
stack_stop.  The currently running greenlet is the first element of
this chain.  The main (initial) greenlet is the last one.  Greenlets
whose stack is entirely in the heap can be skipped from the chain.

The chain is not related to execution order, but only to the order
in which bits of C stack happen to belong to greenlets at a particular
point in time.

The main greenlet doesn't have a stack_stop: it is responsible for the
complete rest of the C stack, and we don't know where it begins.  We
use (char*) -1, the largest possible address.

States:
  stack_stop == NULL && stack_start == NULL:  did not start yet
  stack_stop != NULL && stack_start == NULL:  already finished
  stack_stop != NULL && stack_start != NULL:  active

The running greenlet's stack_start is undefined but not NULL.

 ***********************************************************/




/***********************************************************/

/* Some functions must not be inlined:
   * slp_restore_state, when inlined into slp_switch might cause
     it to restore stack over its own local variables
   * slp_save_state, when inlined would add its own local
     variables to the saved stack, wasting space
   * slp_switch, cannot be inlined for obvious reasons
   * g_initialstub, when inlined would receive a pointer into its
     own stack frame, leading to incomplete stack save/restore

g_initialstub is a member function and declared virtual so that the
compiler always calls it through a vtable.

slp_save_state and slp_restore_state are also member functions. They
are called from trampoline functions that themselves are declared as
not eligible for inlining.
*/

extern "C" {
static int GREENLET_NOINLINE(slp_save_state_trampoline)(char* stackref)
{
    return switching_thread_state->slp_save_state(stackref);
}
static void GREENLET_NOINLINE(slp_restore_state_trampoline)()
{
    switching_thread_state->slp_restore_state();
}
}


/***********************************************************/


#include "PyModule.cpp"



static PyObject*
greenlet_internal_mod_init() noexcept
{
    static void* _PyGreenlet_API[PyGreenlet_API_pointers];

    try {
        CreatedModule m(greenlet_module_def);

        Require(PyType_Ready(&PyGreenlet_Type));
        Require(PyType_Ready(&PyGreenletUnswitchable_Type));

        mod_globs = new greenlet::GreenletGlobals;
        ThreadState::init();

        m.PyAddObject("greenlet", PyGreenlet_Type);
        m.PyAddObject("UnswitchableGreenlet", PyGreenletUnswitchable_Type);
        m.PyAddObject("error", mod_globs->PyExc_GreenletError);
        m.PyAddObject("GreenletExit", mod_globs->PyExc_GreenletExit);

        m.PyAddObject("GREENLET_USE_GC", 1);
        m.PyAddObject("GREENLET_USE_TRACING", 1);
        m.PyAddObject("GREENLET_USE_CONTEXT_VARS", 1L);
        m.PyAddObject("GREENLET_USE_STANDARD_THREADING", 1L);

        OwnedObject clocks_per_sec = OwnedObject::consuming(PyLong_FromSsize_t(CLOCKS_PER_SEC));
        m.PyAddObject("CLOCKS_PER_SEC", clocks_per_sec);

        /* also publish module-level data as attributes of the greentype. */
        // XXX: This is weird, and enables a strange pattern of
        // confusing the class greenlet with the module greenlet; with
        // the exception of (possibly) ``getcurrent()``, this
        // shouldn't be encouraged so don't add new items here.
        for (const char* const* p = copy_on_greentype; *p; p++) {
            OwnedObject o = m.PyRequireAttr(*p);
            PyDict_SetItemString(PyGreenlet_Type.tp_dict, *p, o.borrow());
        }

        /*
         * Expose C API
         */

        /* types */
        _PyGreenlet_API[PyGreenlet_Type_NUM] = (void*)&PyGreenlet_Type;

        /* exceptions */
        _PyGreenlet_API[PyExc_GreenletError_NUM] = (void*)mod_globs->PyExc_GreenletError;
        _PyGreenlet_API[PyExc_GreenletExit_NUM] = (void*)mod_globs->PyExc_GreenletExit;

        /* methods */
        _PyGreenlet_API[PyGreenlet_New_NUM] = (void*)PyGreenlet_New;
        _PyGreenlet_API[PyGreenlet_GetCurrent_NUM] = (void*)PyGreenlet_GetCurrent;
        _PyGreenlet_API[PyGreenlet_Throw_NUM] = (void*)PyGreenlet_Throw;
        _PyGreenlet_API[PyGreenlet_Switch_NUM] = (void*)PyGreenlet_Switch;
        _PyGreenlet_API[PyGreenlet_SetParent_NUM] = (void*)PyGreenlet_SetParent;

        /* Previously macros, but now need to be functions externally. */
        _PyGreenlet_API[PyGreenlet_MAIN_NUM] = (void*)Extern_PyGreenlet_MAIN;
        _PyGreenlet_API[PyGreenlet_STARTED_NUM] = (void*)Extern_PyGreenlet_STARTED;
        _PyGreenlet_API[PyGreenlet_ACTIVE_NUM] = (void*)Extern_PyGreenlet_ACTIVE;
        _PyGreenlet_API[PyGreenlet_GET_PARENT_NUM] = (void*)Extern_PyGreenlet_GET_PARENT;

        /* XXX: Note that our module name is ``greenlet._greenlet``, but for
           backwards compatibility with existing C code, we need the _C_API to
           be directly in greenlet.
        */
        const NewReference c_api_object(Require(
                                           PyCapsule_New(
                                               (void*)_PyGreenlet_API,
                                               "greenlet._C_API",
                                               NULL)));
        m.PyAddObject("_C_API", c_api_object);
        assert(c_api_object.REFCNT() == 2);

        // cerr << "Sizes:"
        //      << "\n\tGreenlet       : " << sizeof(Greenlet)
        //      << "\n\tUserGreenlet   : " << sizeof(UserGreenlet)
        //      << "\n\tMainGreenlet   : " << sizeof(MainGreenlet)
        //      << "\n\tExceptionState : " << sizeof(greenlet::ExceptionState)
        //      << "\n\tPythonState    : " << sizeof(greenlet::PythonState)
        //      << "\n\tStackState     : " << sizeof(greenlet::StackState)
        //      << "\n\tSwitchingArgs  : " << sizeof(greenlet::SwitchingArgs)
        //      << "\n\tOwnedObject    : " << sizeof(greenlet::refs::OwnedObject)
        //      << "\n\tBorrowedObject : " << sizeof(greenlet::refs::BorrowedObject)
        //      << "\n\tPyGreenlet     : " << sizeof(PyGreenlet)
        //      << endl;

#ifdef Py_GIL_DISABLED
        PyUnstable_Module_SetGIL(m.borrow(), Py_MOD_GIL_NOT_USED);
#endif
        return m.borrow(); // But really it's the main reference.
    }
    catch (const LockInitError& e) {
        PyErr_SetString(PyExc_MemoryError, e.what());
        return NULL;
    }
    catch (const PyErrOccurred&) {
        return NULL;
    }

}

extern "C" {

PyMODINIT_FUNC
PyInit__greenlet(void)
{
    return greenlet_internal_mod_init();
}

}; // extern C

#ifdef __clang__
#    pragma clang diagnostic pop
#elif defined(__GNUC__)
#    pragma GCC diagnostic pop
#endif
