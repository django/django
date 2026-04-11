#ifndef COBJECTS_CPP
#define COBJECTS_CPP
/*****************************************************************************
 * C interface
 *
 * These are exported using the CObject API
 */
#ifdef __clang__
#    pragma clang diagnostic push
#    pragma clang diagnostic ignored "-Wunused-function"
#endif

#include "greenlet_exceptions.hpp"

#include "greenlet_internal.hpp"
#include "greenlet_refs.hpp"


#include "TThreadStateDestroy.cpp"

#include "PyGreenlet.hpp"

using greenlet::PyErrOccurred;
using greenlet::Require;



extern "C" {
static PyGreenlet*
PyGreenlet_GetCurrent(void)
{
    return GET_THREAD_STATE().state().get_current().relinquish_ownership();
}

static int
PyGreenlet_SetParent(PyGreenlet* g, PyGreenlet* nparent)
{
    return green_setparent((PyGreenlet*)g, (PyObject*)nparent, NULL);
}

static PyGreenlet*
PyGreenlet_New(PyObject* run, PyGreenlet* parent)
{
    using greenlet::refs::NewDictReference;
    // In the past, we didn't use green_new and green_init, but that
    // was a maintenance issue because we duplicated code. This way is
    // much safer, but slightly slower. If that's a problem, we could
    // refactor green_init to separate argument parsing from initialization.
    OwnedGreenlet g = OwnedGreenlet::consuming(green_new(&PyGreenlet_Type, nullptr, nullptr));
    if (!g) {
        return NULL;
    }

    try {
        NewDictReference kwargs;
        if (run) {
            kwargs.SetItem(mod_globs->str_run, run);
        }
        if (parent) {
            kwargs.SetItem("parent", (PyObject*)parent);
        }

        Require(green_init(g.borrow(), mod_globs->empty_tuple, kwargs.borrow()));
    }
    catch (const PyErrOccurred&) {
        return nullptr;
    }

    return g.relinquish_ownership();
}

static PyObject*
PyGreenlet_Switch(PyGreenlet* self, PyObject* args, PyObject* kwargs)
{
    if (!PyGreenlet_Check(self)) {
        PyErr_BadArgument();
        return NULL;
    }

    if (args == NULL) {
        args = mod_globs->empty_tuple;
    }

    if (kwargs == NULL || !PyDict_Check(kwargs)) {
        kwargs = NULL;
    }

    return green_switch(self, args, kwargs);
}

static PyObject*
PyGreenlet_Throw(PyGreenlet* self, PyObject* typ, PyObject* val, PyObject* tb)
{
    if (!PyGreenlet_Check(self)) {
        PyErr_BadArgument();
        return nullptr;
    }
    try {
        PyErrPieces err_pieces(typ, val, tb);
        return internal_green_throw(self, err_pieces).relinquish_ownership();
    }
    catch (const PyErrOccurred&) {
        return nullptr;
    }
}



static int
Extern_PyGreenlet_MAIN(PyGreenlet* self)
{
    if (!PyGreenlet_Check(self)) {
        PyErr_BadArgument();
        return -1;
    }
    return self->pimpl->main();
}

static int
Extern_PyGreenlet_ACTIVE(PyGreenlet* self)
{
    if (!PyGreenlet_Check(self)) {
        PyErr_BadArgument();
        return -1;
    }
    return self->pimpl->active();
}

static int
Extern_PyGreenlet_STARTED(PyGreenlet* self)
{
    if (!PyGreenlet_Check(self)) {
        PyErr_BadArgument();
        return -1;
    }
    return self->pimpl->started();
}

static PyGreenlet*
Extern_PyGreenlet_GET_PARENT(PyGreenlet* self)
{
    if (!PyGreenlet_Check(self)) {
        PyErr_BadArgument();
        return NULL;
    }
    // This can return NULL even if there is no exception
    return self->pimpl->parent().acquire();
}
} // extern C.

/** End C API ****************************************************************/
#ifdef __clang__
#    pragma clang diagnostic pop
#endif


#endif
