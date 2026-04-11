/* -*- indent-tabs-mode: nil; tab-width: 4; -*- */
/**
   Implementation of the Python slots for PyGreenletUnswitchable_Type
*/
#ifndef PY_GREENLET_UNSWITCHABLE_CPP
#define PY_GREENLET_UNSWITCHABLE_CPP



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

#include "TGreenlet.cpp"
#include "TGreenletGlobals.cpp"
#include "TThreadStateDestroy.cpp"


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


#include "PyGreenlet.hpp"

static PyGreenlet*
green_unswitchable_new(PyTypeObject* type, PyObject* UNUSED(args), PyObject* UNUSED(kwds))
{
    PyGreenlet* o =
        (PyGreenlet*)PyBaseObject_Type.tp_new(type, mod_globs->empty_tuple, mod_globs->empty_dict);
    if (o) {
        new BrokenGreenlet(o, GET_THREAD_STATE().state().borrow_current());
        assert(Py_REFCNT(o) == 1);
    }
    return o;
}

static PyObject*
green_unswitchable_getforce(PyGreenlet* self, void* UNUSED(context))
{
    BrokenGreenlet* broken = dynamic_cast<BrokenGreenlet*>(self->pimpl);
    return PyBool_FromLong(broken->_force_switch_error);
}

static int
green_unswitchable_setforce(PyGreenlet* self, PyObject* nforce, void* UNUSED(context))
{
    if (!nforce) {
        PyErr_SetString(
            PyExc_AttributeError,
            "Cannot delete force_switch_error"
        );
        return -1;
    }
    BrokenGreenlet* broken = dynamic_cast<BrokenGreenlet*>(self->pimpl);
    int is_true = PyObject_IsTrue(nforce);
    if (is_true == -1) {
        return -1;
    }
    broken->_force_switch_error = is_true;
    return 0;
}

static PyObject*
green_unswitchable_getforceslp(PyGreenlet* self, void* UNUSED(context))
{
    BrokenGreenlet* broken = dynamic_cast<BrokenGreenlet*>(self->pimpl);
    return PyBool_FromLong(broken->_force_slp_switch_error);
}

static int
green_unswitchable_setforceslp(PyGreenlet* self, PyObject* nforce, void* UNUSED(context))
{
    if (!nforce) {
        PyErr_SetString(
            PyExc_AttributeError,
            "Cannot delete force_slp_switch_error"
        );
        return -1;
    }
    BrokenGreenlet* broken = dynamic_cast<BrokenGreenlet*>(self->pimpl);
    int is_true = PyObject_IsTrue(nforce);
    if (is_true == -1) {
        return -1;
    }
    broken->_force_slp_switch_error = is_true;
    return 0;
}

static PyGetSetDef green_unswitchable_getsets[] = {
    /* name, getter, setter, doc, closure (context pointer) */
    {
      .name="force_switch_error",
      .get=(getter)green_unswitchable_getforce,
      .set=(setter)green_unswitchable_setforce,
      .doc=NULL
    },
    {
      .name="force_slp_switch_error",
      .get=(getter)green_unswitchable_getforceslp,
      .set=(setter)green_unswitchable_setforceslp,
      .doc=nullptr
    },
    {.name=nullptr}
};

PyTypeObject PyGreenletUnswitchable_Type = {
    .ob_base=PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name="greenlet._greenlet.UnswitchableGreenlet",
    .tp_dealloc= (destructor)green_dealloc, /* tp_dealloc */
    .tp_flags=G_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
    .tp_doc="Undocumented internal class",                        /* tp_doc */
    .tp_traverse=(traverseproc)green_traverse, /* tp_traverse */
    .tp_clear=(inquiry)green_clear,         /* tp_clear */

    .tp_getset=green_unswitchable_getsets,                      /* tp_getset */
    .tp_base=&PyGreenlet_Type,                                  /* tp_base */
    .tp_init=(initproc)green_init,               /* tp_init */
    .tp_alloc=PyType_GenericAlloc,                  /* tp_alloc */
    .tp_new=(newfunc)green_unswitchable_new,                          /* tp_new */
    .tp_free=PyObject_GC_Del,                   /* tp_free */
    .tp_is_gc=(inquiry)green_is_gc,         /* tp_is_gc */
};


#endif
