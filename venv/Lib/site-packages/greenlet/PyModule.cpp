#ifndef PY_MODULE_CPP
#define PY_MODULE_CPP

#include "greenlet_internal.hpp"


#include "TGreenletGlobals.cpp"
#include "TMainGreenlet.cpp"
#include "TThreadStateDestroy.cpp"

using greenlet::LockGuard;
using greenlet::ThreadState;

#ifdef __clang__
#    pragma clang diagnostic push
#    pragma clang diagnostic ignored "-Wunused-function"
#    pragma clang diagnostic ignored "-Wunused-variable"
#endif

PyDoc_STRVAR(mod_getcurrent_doc,
             "getcurrent() -> greenlet\n"
             "\n"
             "Returns the current greenlet (i.e. the one which called this "
             "function).\n");

static PyObject*
mod_getcurrent(PyObject* UNUSED(module))
{
    return GET_THREAD_STATE().state().get_current().relinquish_ownership_o();
}

PyDoc_STRVAR(mod_settrace_doc,
             "settrace(callback) -> object\n"
             "\n"
             "Sets a new tracing function and returns the previous one.\n");
static PyObject*
mod_settrace(PyObject* UNUSED(module), PyObject* args)
{
    PyArgParseParam tracefunc;
    if (!PyArg_ParseTuple(args, "O", &tracefunc)) {
        return NULL;
    }
    ThreadState& state = GET_THREAD_STATE();
    OwnedObject previous = state.get_tracefunc();
    if (!previous) {
        previous = Py_None;
    }

    state.set_tracefunc(tracefunc);

    return previous.relinquish_ownership();
}

PyDoc_STRVAR(mod_gettrace_doc,
             "gettrace() -> object\n"
             "\n"
             "Returns the currently set tracing function, or None.\n");

static PyObject*
mod_gettrace(PyObject* UNUSED(module))
{
    OwnedObject tracefunc = GET_THREAD_STATE().state().get_tracefunc();
    if (!tracefunc) {
        tracefunc = Py_None;
    }
    return tracefunc.relinquish_ownership();
}



PyDoc_STRVAR(mod_set_thread_local_doc,
             "set_thread_local(key, value) -> None\n"
             "\n"
             "Set a value in the current thread-local dictionary. Debugging only.\n");

static PyObject*
mod_set_thread_local(PyObject* UNUSED(module), PyObject* args)
{
    PyArgParseParam key;
    PyArgParseParam value;
    PyObject* result = NULL;

    if (PyArg_UnpackTuple(args, "set_thread_local", 2, 2, &key, &value)) {
        if(PyDict_SetItem(
                          PyThreadState_GetDict(), // borrow
                          key,
                          value) == 0 ) {
            // success
            Py_INCREF(Py_None);
            result = Py_None;
        }
    }
    return result;
}

PyDoc_STRVAR(mod_get_pending_cleanup_count_doc,
             "get_pending_cleanup_count() -> Integer\n"
             "\n"
             "Get the number of greenlet cleanup operations pending. Testing only.\n");


static PyObject*
mod_get_pending_cleanup_count(PyObject* UNUSED(module))
{
    LockGuard cleanup_lock(*mod_globs->thread_states_to_destroy_lock);
    return PyLong_FromSize_t(mod_globs->thread_states_to_destroy.size());
}

PyDoc_STRVAR(mod_get_total_main_greenlets_doc,
             "get_total_main_greenlets() -> Integer\n"
             "\n"
             "Quickly return the number of main greenlets that exist. Testing only.\n");

static PyObject*
mod_get_total_main_greenlets(PyObject* UNUSED(module))
{
    return PyLong_FromSize_t(G_TOTAL_MAIN_GREENLETS);
}



PyDoc_STRVAR(mod_get_clocks_used_doing_optional_cleanup_doc,
             "get_clocks_used_doing_optional_cleanup() -> Integer\n"
             "\n"
             "Get the number of clock ticks the program has used doing optional "
             "greenlet cleanup.\n"
             "Beginning in greenlet 2.0, greenlet tries to find and dispose of greenlets\n"
             "that leaked after a thread exited. This requires invoking Python's garbage collector,\n"
             "which may have a performance cost proportional to the number of live objects.\n"
             "This function returns the amount of processor time\n"
             "greenlet has used to do this. In programs that run with very large amounts of live\n"
             "objects, this metric can be used to decide whether the cost of doing this cleanup\n"
             "is worth the memory leak being corrected. If not, you can disable the cleanup\n"
             "using ``enable_optional_cleanup(False)``.\n"
             "The units are arbitrary and can only be compared to themselves (similarly to ``time.clock()``);\n"
             "for example, to see how it scales with your heap. You can attempt to convert them into seconds\n"
             "by dividing by the value of CLOCKS_PER_SEC."
             "If cleanup has been disabled, returns None."
             "\n"
             "This is an implementation specific, provisional API. It may be changed or removed\n"
             "in the future.\n"
             ".. versionadded:: 2.0"
             );
static PyObject*
mod_get_clocks_used_doing_optional_cleanup(PyObject* UNUSED(module))
{
    std::clock_t clocks = ThreadState::clocks_used_doing_gc();

    if (clocks == std::clock_t(-1)) {
        Py_RETURN_NONE;
    }
    // This might not actually work on some implementations; clock_t
    // is an opaque type.
    return PyLong_FromSsize_t(clocks);
}

PyDoc_STRVAR(mod_enable_optional_cleanup_doc,
             "mod_enable_optional_cleanup(bool) -> None\n"
             "\n"
             "Enable or disable optional cleanup operations.\n"
             "See ``get_clocks_used_doing_optional_cleanup()`` for details.\n"
             );
static PyObject*
mod_enable_optional_cleanup(PyObject* UNUSED(module), PyObject* flag)
{
    int is_true = PyObject_IsTrue(flag);
    if (is_true == -1) {
        return nullptr;
    }

    if (is_true) {
        std::clock_t clocks = ThreadState::clocks_used_doing_gc();
        // If we already have a value, we don't want to lose it.
        if (clocks == std::clock_t(-1)) {
            ThreadState::set_clocks_used_doing_gc(0);
        }
    }
    else {
        ThreadState::set_clocks_used_doing_gc(std::clock_t(-1));
    }
    Py_RETURN_NONE;
}




#if !GREENLET_PY313
PyDoc_STRVAR(mod_get_tstate_trash_delete_nesting_doc,
             "get_tstate_trash_delete_nesting() -> Integer\n"
             "\n"
             "Return the 'trash can' nesting level. Testing only.\n");
static PyObject*
mod_get_tstate_trash_delete_nesting(PyObject* UNUSED(module))
{
    PyThreadState* tstate = PyThreadState_GET();

#if GREENLET_PY312
    return PyLong_FromLong(tstate->trash.delete_nesting);
#else
    return PyLong_FromLong(tstate->trash_delete_nesting);
#endif
}
#endif




static PyMethodDef GreenMethods[] = {
    {
      .ml_name="getcurrent",
      .ml_meth=(PyCFunction)mod_getcurrent,
      .ml_flags=METH_NOARGS,
      .ml_doc=mod_getcurrent_doc
    },
    {
      .ml_name="settrace",
      .ml_meth=(PyCFunction)mod_settrace,
      .ml_flags=METH_VARARGS,
      .ml_doc=mod_settrace_doc
    },
    {
      .ml_name="gettrace",
      .ml_meth=(PyCFunction)mod_gettrace,
      .ml_flags=METH_NOARGS,
      .ml_doc=mod_gettrace_doc
    },
    {
      .ml_name="set_thread_local",
      .ml_meth=(PyCFunction)mod_set_thread_local,
      .ml_flags=METH_VARARGS,
      .ml_doc=mod_set_thread_local_doc
    },
    {
      .ml_name="get_pending_cleanup_count",
      .ml_meth=(PyCFunction)mod_get_pending_cleanup_count,
      .ml_flags=METH_NOARGS,
      .ml_doc=mod_get_pending_cleanup_count_doc
    },
    {
      .ml_name="get_total_main_greenlets",
      .ml_meth=(PyCFunction)mod_get_total_main_greenlets,
      .ml_flags=METH_NOARGS,
      .ml_doc=mod_get_total_main_greenlets_doc
    },
    {
      .ml_name="get_clocks_used_doing_optional_cleanup",
      .ml_meth=(PyCFunction)mod_get_clocks_used_doing_optional_cleanup,
      .ml_flags=METH_NOARGS,
      .ml_doc=mod_get_clocks_used_doing_optional_cleanup_doc
    },
    {
      .ml_name="enable_optional_cleanup",
      .ml_meth=(PyCFunction)mod_enable_optional_cleanup,
      .ml_flags=METH_O,
      .ml_doc=mod_enable_optional_cleanup_doc
    },
#if !GREENLET_PY313
    {
      .ml_name="get_tstate_trash_delete_nesting",
      .ml_meth=(PyCFunction)mod_get_tstate_trash_delete_nesting,
      .ml_flags=METH_NOARGS,
      .ml_doc=mod_get_tstate_trash_delete_nesting_doc
    },
#endif
    {.ml_name=NULL, .ml_meth=NULL} /* Sentinel */
};

static const char* const copy_on_greentype[] = {
    "getcurrent",
    "error",
    "GreenletExit",
    "settrace",
    "gettrace",
    NULL
};

static struct PyModuleDef greenlet_module_def = {
    .m_base=PyModuleDef_HEAD_INIT,
    .m_name="greenlet._greenlet",
    .m_doc=NULL,
    .m_size=-1,
    .m_methods=GreenMethods,
};


#endif

#ifdef __clang__
#    pragma clang diagnostic pop
#elif defined(__GNUC__)
#    pragma GCC diagnostic pop
#endif
