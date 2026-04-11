/* -*- indent-tabs-mode: nil; tab-width: 4; -*- */
#ifndef GREENLET_INTERNAL_H
#define GREENLET_INTERNAL_H
#ifdef __clang__
#    pragma clang diagnostic push
#    pragma clang diagnostic ignored "-Wunused-function"
#endif

/**
 * Implementation helpers.
 *
 * C++ templates and inline functions should go here.
 */
#define PY_SSIZE_T_CLEAN
#include "greenlet_compiler_compat.hpp"
#include "greenlet_cpython_compat.hpp"
#include "greenlet_exceptions.hpp"
#include "TGreenlet.hpp"
#include "greenlet_allocator.hpp"

#include <vector>
#include <string>

#define GREENLET_MODULE
struct _greenlet;
typedef struct _greenlet PyGreenlet;
namespace greenlet {

    class ThreadState;
    // We can't use the PythonAllocator for this, because we push to it
    // from the thread state destructor, which doesn't have the GIL,
    // and Python's allocators can only be called with the GIL.
    typedef std::vector<ThreadState*> cleanup_queue_t;

};


#define implementation_ptr_t greenlet::Greenlet*


#include "greenlet.h"

void
greenlet::refs::MainGreenletExactChecker(void *p)
{
    if (!p) {
        return;
    }
    // We control the class of the main greenlet exactly.
    if (Py_TYPE(p) != &PyGreenlet_Type) {
        std::string err("MainGreenlet: Expected exactly a greenlet, not a ");
        err += Py_TYPE(p)->tp_name;
        throw greenlet::TypeError(err);
    }

    // Greenlets from dead threads no longer respond to main() with a
    // true value; so in that case we need to perform an additional
    // check.
    Greenlet* g = static_cast<PyGreenlet*>(p)->pimpl;
    if (g->main()) {
        return;
    }
    if (!dynamic_cast<MainGreenlet*>(g)) {
        std::string err("MainGreenlet: Expected exactly a main greenlet, not a ");
        err += Py_TYPE(p)->tp_name;
        throw greenlet::TypeError(err);
    }
}



template <typename T, greenlet::refs::TypeChecker TC>
inline greenlet::Greenlet* greenlet::refs::_OwnedGreenlet<T, TC>::operator->() const noexcept
{
    return reinterpret_cast<PyGreenlet*>(this->p)->pimpl;
}

template <typename T, greenlet::refs::TypeChecker TC>
inline greenlet::Greenlet* greenlet::refs::_BorrowedGreenlet<T, TC>::operator->() const noexcept
{
    return reinterpret_cast<PyGreenlet*>(this->p)->pimpl;
}

#include <memory>
#include <stdexcept>


extern PyTypeObject PyGreenlet_Type;



/**
  * Forward declarations needed in multiple files.
  */
static PyObject* green_switch(PyGreenlet* self, PyObject* args, PyObject* kwargs);


#ifdef __clang__
#    pragma clang diagnostic pop
#endif


#endif

// Local Variables:
// flycheck-clang-include-path: ("../../include" "/opt/local/Library/Frameworks/Python.framework/Versions/3.10/include/python3.10")
// End:
