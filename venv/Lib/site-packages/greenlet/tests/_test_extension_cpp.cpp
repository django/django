/* This is a set of functions used to test C++ exceptions are not
 * broken during greenlet switches
 */

#include "../greenlet.h"
#include "../greenlet_compiler_compat.hpp"
#include <exception>
#include <stdexcept>

struct exception_t {
    int depth;
    exception_t(int depth) : depth(depth) {}
};

/* Functions are called via pointers to prevent inlining */
static void (*p_test_exception_throw_nonstd)(int depth);
static void (*p_test_exception_throw_std)();
static PyObject* (*p_test_exception_switch_recurse)(int depth, int left);

static void
test_exception_throw_nonstd(int depth)
{
    throw exception_t(depth);
}

static void
test_exception_throw_std()
{
    throw std::runtime_error("Thrown from an extension.");
}

static PyObject*
test_exception_switch_recurse(int depth, int left)
{
    if (left > 0) {
        return p_test_exception_switch_recurse(depth, left - 1);
    }

    PyObject* result = NULL;
    PyGreenlet* self = PyGreenlet_GetCurrent();
    if (self == NULL)
        return NULL;

    try {
        if (PyGreenlet_Switch(PyGreenlet_GET_PARENT(self), NULL, NULL) == NULL) {
            Py_DECREF(self);
            return NULL;
        }
        p_test_exception_throw_nonstd(depth);
        PyErr_SetString(PyExc_RuntimeError,
                        "throwing C++ exception didn't work");
    }
    catch (const exception_t& e) {
        if (e.depth != depth)
            PyErr_SetString(PyExc_AssertionError, "depth mismatch");
        else
            result = PyLong_FromLong(depth);
    }
    catch (...) {
        PyErr_SetString(PyExc_RuntimeError, "unexpected C++ exception");
    }

    Py_DECREF(self);
    return result;
}

/* test_exception_switch(int depth)
 * - recurses depth times
 * - switches to parent inside try/catch block
 * - throws an exception that (expected to be caught in the same function)
 * - verifies depth matches (exceptions shouldn't be caught in other greenlets)
 */
static PyObject*
test_exception_switch(PyObject* UNUSED(self), PyObject* args)
{
    int depth;
    if (!PyArg_ParseTuple(args, "i", &depth))
        return NULL;
    return p_test_exception_switch_recurse(depth, depth);
}


static PyObject*
py_test_exception_throw_nonstd(PyObject* UNUSED(self), PyObject* args)
{
    if (!PyArg_ParseTuple(args, ""))
        return NULL;
    p_test_exception_throw_nonstd(0);
    PyErr_SetString(PyExc_AssertionError, "unreachable code running after throw");
    return NULL;
}

static PyObject*
py_test_exception_throw_std(PyObject* UNUSED(self), PyObject* args)
{
    if (!PyArg_ParseTuple(args, ""))
        return NULL;
    p_test_exception_throw_std();
    PyErr_SetString(PyExc_AssertionError, "unreachable code running after throw");
    return NULL;
}

static PyObject*
py_test_call(PyObject* UNUSED(self), PyObject* arg)
{
    PyObject* noargs = PyTuple_New(0);
    PyObject* ret = PyObject_Call(arg, noargs, nullptr);
    Py_DECREF(noargs);
    return ret;
}



/* test_exception_switch_and_do_in_g2(g2func)
 * - creates new greenlet g2 to run g2func
 * - switches to g2 inside try/catch block
 * - verifies that no exception has been caught
 *
 * it is used together with test_exception_throw to verify that unhandled
 * exceptions thrown in one greenlet do not propagate to other greenlet nor
 * segfault the process.
 */
static PyObject*
test_exception_switch_and_do_in_g2(PyObject* UNUSED(self), PyObject* args)
{
    PyObject* g2func = NULL;
    PyObject* result = NULL;

    if (!PyArg_ParseTuple(args, "O", &g2func))
        return NULL;
    PyGreenlet* g2 = PyGreenlet_New(g2func, NULL);
    if (!g2) {
        return NULL;
    }

    try {
        result = PyGreenlet_Switch(g2, NULL, NULL);
        if (!result) {
            return NULL;
        }
    }
    catch (const exception_t& e) {
        /* if we are here the memory can be already corrupted and the program
         * might crash before below py-level exception might become printed.
         * -> print something to stderr to make it clear that we had entered
         *    this catch block.
         * See comments in inner_bootstrap()
         */
#if defined(WIN32) || defined(_WIN32)
        fprintf(stderr, "C++ exception unexpectedly caught in g1\n");
        PyErr_SetString(PyExc_AssertionError, "C++ exception unexpectedly caught in g1");
        Py_XDECREF(result);
        return NULL;
#else
        throw;
#endif
    }

    Py_XDECREF(result);
    Py_RETURN_NONE;
}

static PyMethodDef test_methods[] = {
    {"test_exception_switch",
     (PyCFunction)&test_exception_switch,
     METH_VARARGS,
     "Switches to parent twice, to test exception handling and greenlet "
     "switching."},
    {"test_exception_switch_and_do_in_g2",
     (PyCFunction)&test_exception_switch_and_do_in_g2,
     METH_VARARGS,
     "Creates new greenlet g2 to run g2func and switches to it inside try/catch "
     "block. Used together with test_exception_throw to verify that unhandled "
     "C++ exceptions thrown in a greenlet doe not corrupt memory."},
    {"test_exception_throw_nonstd",
     (PyCFunction)&py_test_exception_throw_nonstd,
     METH_VARARGS,
     "Throws non-standard C++ exception. Calling this function directly should abort the process."
    },
    {"test_exception_throw_std",
     (PyCFunction)&py_test_exception_throw_std,
     METH_VARARGS,
     "Throws standard C++ exception. Calling this function directly should abort the process."
    },
    {"test_call",
     (PyCFunction)&py_test_call,
     METH_O,
     "Call the given callable. Unlike calling it directly, this creates a "
     "new C-level stack frame, which may be helpful in testing."
    },
    {NULL, NULL, 0, NULL}
};


static struct PyModuleDef moduledef = {PyModuleDef_HEAD_INIT,
                                       "greenlet.tests._test_extension_cpp",
                                       NULL,
                                       0,
                                       test_methods,
                                       NULL,
                                       NULL,
                                       NULL,
                                       NULL};

PyMODINIT_FUNC
PyInit__test_extension_cpp(void)
{
    PyObject* module = NULL;

    module = PyModule_Create(&moduledef);

    if (module == NULL) {
        return NULL;
    }

    PyGreenlet_Import();
    if (_PyGreenlet_API == NULL) {
        return NULL;
    }

    p_test_exception_throw_nonstd = test_exception_throw_nonstd;
    p_test_exception_throw_std = test_exception_throw_std;
    p_test_exception_switch_recurse = test_exception_switch_recurse;
#ifdef Py_GIL_DISABLED
    PyUnstable_Module_SetGIL(module, Py_MOD_GIL_NOT_USED);
#endif

    return module;
}
