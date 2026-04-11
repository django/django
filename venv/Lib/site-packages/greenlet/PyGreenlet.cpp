/* -*- indent-tabs-mode: nil; tab-width: 4; -*- */
#ifndef PYGREENLET_CPP
#define PYGREENLET_CPP
/*****************
The Python slot functions for TGreenlet.
 */


#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "structmember.h" // PyMemberDef

#include "greenlet_internal.hpp"
#include "TThreadStateDestroy.cpp"
#include "TGreenlet.hpp"
// #include "TUserGreenlet.cpp"
// #include "TMainGreenlet.cpp"
// #include "TBrokenGreenlet.cpp"


#include "greenlet_refs.hpp"
#include "greenlet_slp_switch.hpp"

#include "greenlet_thread_support.hpp"
#include "TGreenlet.hpp"

#include "TGreenletGlobals.cpp"
#include "TThreadStateDestroy.cpp"
#include "PyGreenlet.hpp"
// #include "TGreenlet.cpp"

// #include "TExceptionState.cpp"
// #include "TPythonState.cpp"
// #include "TStackState.cpp"

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



static PyGreenlet*
green_new(PyTypeObject* type, PyObject* UNUSED(args), PyObject* UNUSED(kwds))
{
    PyGreenlet* o =
        (PyGreenlet*)PyBaseObject_Type.tp_new(type, mod_globs->empty_tuple, mod_globs->empty_dict);
    if (o) {
        // Recall: borrowing or getting the current greenlet
        // causes the "deleteme list" to get cleared. So constructing a greenlet
        // can do things like cause other greenlets to get finalized.
        UserGreenlet* c = new UserGreenlet(o, GET_THREAD_STATE().state().borrow_current());
        assert(Py_REFCNT(o) == 1);
        // Also: This looks like a memory leak, but isn't. Constructing the
        // C++ object assigns it to the pimpl pointer of the Python object (o);
        // we'll need that later.
        assert(c == o->pimpl);
    }
    return o;
}


// green_init is used in the tp_init slot. So it's important that
// it can be called directly from CPython. Thus, we don't use
// BorrowedGreenlet and BorrowedObject --- although in theory
// these should be binary layout compatible, that may not be
// guaranteed to be the case (32-bit linux ppc possibly).
static int
green_init(PyGreenlet* self, PyObject* args, PyObject* kwargs)
{
    PyArgParseParam run;
    PyArgParseParam nparent;
    static const char* kwlist[] = {
        "run",
        "parent",
        NULL
    };

    // recall: The O specifier does NOT increase the reference count.
    if (!PyArg_ParseTupleAndKeywords(
             args, kwargs, "|OO:green", (char**)kwlist, &run, &nparent)) {
        return -1;
    }

    if (run) {
        if (green_setrun(self, run, NULL)) {
            return -1;
        }
    }
    if (nparent && !nparent.is_None()) {
        return green_setparent(self, nparent, NULL);
    }
    return 0;
}



static int
green_traverse(PyGreenlet* self, visitproc visit, void* arg)
{
    // We must only visit referenced objects, i.e. only objects
    // Py_INCREF'ed by this greenlet (directly or indirectly):
    //
    // - stack_prev is not visited: holds previous stack pointer, but it's not
    //    referenced
    // - frames are not visited as we don't strongly reference them;
    //    alive greenlets are not garbage collected
    //    anyway. This can be a problem, however, if this greenlet is
    //    never allowed to finish, and is referenced from the frame: we
    //    have an uncollectible cycle in that case. Note that the
    //    frame object itself is also frequently not even tracked by the GC
    //    starting with Python 3.7 (frames are allocated by the
    //    interpreter untracked, and only become tracked when their
    //    evaluation is finished if they have a refcount > 1). All of
    //    this is to say that we should probably strongly reference
    //    the frame object. Doing so, while always allowing GC on a
    //    greenlet, solves several leaks for us.

    Py_VISIT(self->dict);
    if (!self->pimpl) {
        // Hmm. I have seen this at interpreter shutdown time,
        // I think. That's very odd because this doesn't go away until
        // we're ``green_dealloc()``, at which point we shouldn't be
        // traversed anymore.
        return 0;
    }

    return self->pimpl->tp_traverse(visit, arg);
}

static int
green_is_gc(PyObject* _self)
{
    BorrowedGreenlet self(_self);
    int result = 0;
    /* Main greenlet can be garbage collected since it can only
       become unreachable if the underlying thread exited.
       Active greenlets --- including those that are suspended ---
       cannot be garbage collected, however.
    */
    if (self->main() || !self->active()) {
        result = 1;
    }
    // The main greenlet pointer will eventually go away after the thread dies.
    if (self->was_running_in_dead_thread()) {
        // Our thread is dead! We can never run again. Might as well
        // GC us. Note that if a tuple containing only us and other
        // immutable objects had been scanned before this, when we
        // would have returned 0, the tuple will take itself out of GC
        // tracking and never be investigated again. So that could
        // result in both us and the tuple leaking due to an
        // unreachable/uncollectible reference. The same goes for
        // dictionaries.
        //
        // It's not a great idea to be changing our GC state on the
        // fly.
        result = 1;
    }
    return result;
}


static int
green_clear(PyGreenlet* self)
{
    /* Greenlet is only cleared if it is about to be collected.
       Since active greenlets are not garbage collectable, we can
       be sure that, even if they are deallocated during clear,
       nothing they reference is in unreachable or finalizers,
       so even if it switches we are relatively safe. */
    // XXX: Are we responsible for clearing weakrefs here?
    Py_CLEAR(self->dict);
    return self->pimpl->tp_clear();
}

/**
 * Returns 0 on failure (the object was resurrected) or 1 on success.
 **/
static int
_green_dealloc_kill_started_non_main_greenlet(BorrowedGreenlet self)
{
    // During interpreter finalization, we cannot safely throw GreenletExit
    // into the greenlet. Doing so calls g_switch(), which performs a stack
    // switch and runs Python code via _PyEval_EvalFrameDefault. On Python
    // < 3.11, executing Python code in a partially-torn-down interpreter
    // leads to SIGSEGV (greenlet 3.x) or SIGABRT (greenlet 2.x).
    //
    // Python 3.11+ restructured interpreter finalization internals (frame
    // representation, data stack management, recursion tracking) so that
    // g_switch() during finalization is safe. On older Pythons, we simply
    // mark the greenlet dead without throwing, which avoids the crash at
    // the cost of not running any cleanup code inside the greenlet.
    //
    // See: https://github.com/python-greenlet/greenlet/issues/411
    //      https://github.com/python-greenlet/greenlet/issues/351
#if !GREENLET_PY311
    if (_Py_IsFinalizing()) {
        self->murder_in_place();
        return 1;
    }
#endif

    /* Hacks hacks hacks copied from instance_dealloc() */
    /* Temporarily resurrect the greenlet. */
    assert(self.REFCNT() == 0);
    Py_SET_REFCNT(self.borrow(), 1);
    /* Save the current exception, if any. */
    PyErrPieces saved_err;
    try {
        // BY THE TIME WE GET HERE, the state may actually be going
        // away
        // if we're shutting down the interpreter and freeing thread
        // entries,
        // this could result in freeing greenlets that were leaked. So
        // we can't try to read the state.
        self->deallocing_greenlet_in_thread(
              self->thread_state()
              ? static_cast<ThreadState*>(GET_THREAD_STATE())
              : nullptr);
    }
    catch (const PyErrOccurred&) {
        PyErr_WriteUnraisable(self.borrow_o());
        /* XXX what else should we do? */
    }
    /* Check for no resurrection must be done while we keep
     * our internal reference, otherwise PyFile_WriteObject
     * causes recursion if using Py_INCREF/Py_DECREF
     */
    if (self.REFCNT() == 1 && self->active()) {
        /* Not resurrected, but still not dead!
           XXX what else should we do? we complain. */
        PyObject* f = PySys_GetObject("stderr");
        Py_INCREF(self.borrow_o()); /* leak! */
        if (f != NULL) {
            PyFile_WriteString("GreenletExit did not kill ", f);
            PyFile_WriteObject(self.borrow_o(), f, 0);
            PyFile_WriteString("\n", f);
        }
    }
    /* Restore the saved exception. */
    saved_err.PyErrRestore();
    /* Undo the temporary resurrection; can't use DECREF here,
     * it would cause a recursive call.
     */
    assert(self.REFCNT() > 0);

    Py_ssize_t refcnt = self.REFCNT() - 1;
    Py_SET_REFCNT(self.borrow_o(), refcnt);
    if (refcnt != 0) {
        /* Resurrected! */
        _Py_NewReference(self.borrow_o());
        Py_SET_REFCNT(self.borrow_o(), refcnt);
        /* Better to use tp_finalizer slot (PEP 442)
         * and call ``PyObject_CallFinalizerFromDealloc``,
         * but that's only supported in Python 3.4+; see
         * Modules/_io/iobase.c for an example.
         * TODO: We no longer run on anything that old, switch to finalizers.
         *
         * The following approach is copied from iobase.c in CPython 2.7.
         * (along with much of this function in general). Here's their
         * comment:
         *
         * When called from a heap type's dealloc, the type will be
         * decref'ed on return (see e.g. subtype_dealloc in typeobject.c).
         *
         * On free-threaded builds of CPython, the type is meant to be immortal
         * so we probably shouldn't mess with this? See
         * test_issue_245_reference_counting_subclass_no_threads
         */
        if (PyType_HasFeature(self.TYPE(), Py_TPFLAGS_HEAPTYPE)) {
            Py_INCREF(self.TYPE());
        }

        PyObject_GC_Track((PyObject*)self);

        GREENLET_Py_DEC_REFTOTAL;
#ifdef COUNT_ALLOCS
        --Py_TYPE(self)->tp_frees;
        --Py_TYPE(self)->tp_allocs;
#endif /* COUNT_ALLOCS */
        return 0;
    }
    return 1;
}


static void
green_dealloc(PyGreenlet* self)
{
    PyObject_GC_UnTrack(self);
    BorrowedGreenlet me(self);
    if (me->active()
        && me->started()
        && !me->main()) {
        if (!_green_dealloc_kill_started_non_main_greenlet(me)) {
            return;
        }
    }

    if (self->weakreflist != NULL) {
        PyObject_ClearWeakRefs((PyObject*)self);
    }
    Py_CLEAR(self->dict);

    if (self->pimpl) {
        // In case deleting this, which frees some memory,
        // somehow winds up calling back into us. That's usually a
        //bug in our code.
        Greenlet* p = self->pimpl;
        self->pimpl = nullptr;
        delete p;
    }
    // and finally we're done. self is now invalid.
    Py_TYPE(self)->tp_free((PyObject*)self);
}



static OwnedObject
internal_green_throw(BorrowedGreenlet self, PyErrPieces& err_pieces)
{
    PyObject* result = nullptr;
    err_pieces.PyErrRestore();
    assert(PyErr_Occurred());
    if (self->started() && !self->active()) {
        /* dead greenlet: turn GreenletExit into a regular return */
        result = g_handle_exit(OwnedObject()).relinquish_ownership();
    }
    self->args() <<= result;

    return single_result(self->g_switch());
}



PyDoc_STRVAR(
    green_switch_doc,
    "switch(*args, **kwargs)\n"
    "\n"
    "Switch execution to this greenlet.\n"
    "\n"
    "If this greenlet has never been run, then this greenlet\n"
    "will be switched to using the body of ``self.run(*args, **kwargs)``.\n"
    "\n"
    "If the greenlet is active (has been run, but was switch()'ed\n"
    "out before leaving its run function), then this greenlet will\n"
    "be resumed and the return value to its switch call will be\n"
    "None if no arguments are given, the given argument if one\n"
    "argument is given, or the args tuple and keyword args dict if\n"
    "multiple arguments are given.\n"
    "\n"
    "If the greenlet is dead, or is the current greenlet then this\n"
    "function will simply return the arguments using the same rules as\n"
    "above.\n");

static PyObject*
green_switch(PyGreenlet* self, PyObject* args, PyObject* kwargs)
{
    using greenlet::SwitchingArgs;
    SwitchingArgs switch_args(OwnedObject::owning(args), OwnedObject::owning(kwargs));
    self->pimpl->may_switch_away();
    self->pimpl->args() <<= switch_args;

    // If we're switching out of a greenlet, and that switch is the
    // last thing the greenlet does, the greenlet ought to be able to
    // go ahead and die at that point. Currently, someone else must
    // manually switch back to the greenlet so that we "fall off the
    // end" and can perform cleanup. You'd think we'd be able to
    // figure out that this is happening using the frame's ``f_lasti``
    // member, which is supposed to be an index into
    // ``frame->f_code->co_code``, the bytecode string. However, in
    // recent interpreters, ``f_lasti`` tends not to be updated thanks
    // to things like the PREDICT() macros in ceval.c. So it doesn't
    // really work to do that in many cases. For example, the Python
    // code:
    //     def run():
    //         greenlet.getcurrent().parent.switch()
    // produces bytecode of len 16, with the actual call to switch()
    // being at index 10 (in Python 3.10). However, the reported
    // ``f_lasti`` we actually see is...5! (Which happens to be the
    // second byte of the CALL_METHOD op for ``getcurrent()``).

    try {
        //OwnedObject result = single_result(self->pimpl->g_switch());
        OwnedObject result(single_result(self->pimpl->g_switch()));
#ifndef NDEBUG
        // Note that the current greenlet isn't necessarily self. If self
        // finished, we went to one of its parents.
        assert(!self->pimpl->args());

        const BorrowedGreenlet& current = GET_THREAD_STATE().state().borrow_current();
        // It's possible it's never been switched to.
        assert(!current->args());
#endif
        PyObject* p = result.relinquish_ownership();

        if (!p && !PyErr_Occurred()) {
            // This shouldn't be happening anymore, so the asserts
            // are there for debug builds. Non-debug builds
            // crash "gracefully" in this case, although there is an
            // argument to be made for killing the process in all
            // cases --- for this to be the case, our switches
            // probably nested in an incorrect way, so the state is
            // suspicious. Nothing should be corrupt though, just
            // confused at the Python level. Letting this propagate is
            // probably good enough.
            assert(p || PyErr_Occurred());
            throw PyErrOccurred(
                mod_globs->PyExc_GreenletError,
                "Greenlet.switch() returned NULL without an exception set."
            );
        }
        return p;
    }
    catch(const PyErrOccurred&) {
        return nullptr;
    }
}

PyDoc_STRVAR(
    green_throw_doc,
    "Switches execution to this greenlet, but immediately raises the\n"
    "given exception in this greenlet.  If no argument is provided, the "
    "exception\n"
    "defaults to `greenlet.GreenletExit`.  The normal exception\n"
    "propagation rules apply, as described for `switch`.  Note that calling "
    "this\n"
    "method is almost equivalent to the following::\n"
    "\n"
    "    def raiser():\n"
    "        raise typ, val, tb\n"
    "    g_raiser = greenlet(raiser, parent=g)\n"
    "    g_raiser.switch()\n"
    "\n"
    "except that this trick does not work for the\n"
    "`greenlet.GreenletExit` exception, which would not propagate\n"
    "from ``g_raiser`` to ``g``.\n");

static PyObject*
green_throw(PyGreenlet* self, PyObject* args)
{
    PyArgParseParam typ(mod_globs->PyExc_GreenletExit);
    PyArgParseParam val;
    PyArgParseParam tb;

    if (!PyArg_ParseTuple(args, "|OOO:throw", &typ, &val, &tb)) {
        return nullptr;
    }

    assert(typ.borrow() || val.borrow());

    self->pimpl->may_switch_away();
    try {
        // Both normalizing the error and the actual throw_greenlet
        // could throw PyErrOccurred.
        PyErrPieces err_pieces(typ.borrow(), val.borrow(), tb.borrow());

        return internal_green_throw(self, err_pieces).relinquish_ownership();
    }
    catch (const PyErrOccurred&) {
        return nullptr;
    }
}

static int
green_bool(PyGreenlet* self)
{
    return self->pimpl->active();
}

/**
 * CAUTION: Allocates memory, may run GC and arbitrary Python code.
 */
static PyObject*
green_getdict(PyGreenlet* self, void* UNUSED(context))
{
    if (self->dict == NULL) {
        self->dict = PyDict_New();
        if (self->dict == NULL) {
            return NULL;
        }
    }
    Py_INCREF(self->dict);
    return self->dict;
}

static int
green_setdict(PyGreenlet* self, PyObject* val, void* UNUSED(context))
{
    PyObject* tmp;

    if (val == NULL) {
        PyErr_SetString(PyExc_TypeError, "__dict__ may not be deleted");
        return -1;
    }
    if (!PyDict_Check(val)) {
        PyErr_SetString(PyExc_TypeError, "__dict__ must be a dictionary");
        return -1;
    }
    tmp = self->dict;
    Py_INCREF(val);
    self->dict = val;
    Py_XDECREF(tmp);
    return 0;
}

static bool
_green_not_dead(BorrowedGreenlet self)
{
    // XXX: Where else should we do this?
    // Probably on entry to most Python-facing functions?
    if (self->was_running_in_dead_thread()) {
        self->deactivate_and_free();
        return false;
    }
    return self->active() || !self->started();
}


static PyObject*
green_getdead(PyGreenlet* self, void* UNUSED(context))
{
    if (_green_not_dead(self)) {
        Py_RETURN_FALSE;
    }
    else {
        Py_RETURN_TRUE;
    }
}

static PyObject*
green_get_stack_saved(PyGreenlet* self, void* UNUSED(context))
{
    return PyLong_FromSsize_t(self->pimpl->stack_saved());
}


static PyObject*
green_getrun(PyGreenlet* self, void* UNUSED(context))
{
    try {
        OwnedObject result(BorrowedGreenlet(self)->run());
        return result.relinquish_ownership();
    }
    catch(const PyErrOccurred&) {
        return nullptr;
    }
}


static int
green_setrun(PyGreenlet* self, PyObject* nrun, void* UNUSED(context))
{
    try {
        BorrowedGreenlet(self)->run(nrun);
        return 0;
    }
    catch(const PyErrOccurred&) {
        return -1;
    }
}

static PyObject*
green_getparent(PyGreenlet* self, void* UNUSED(context))
{
    return BorrowedGreenlet(self)->parent().acquire_or_None();
}


static int
green_setparent(PyGreenlet* self, PyObject* nparent, void* UNUSED(context))
{
    try {
        BorrowedGreenlet(self)->parent(nparent);
    }
    catch(const PyErrOccurred&) {
        return -1;
    }
    return 0;
}


static PyObject*
green_getcontext(const PyGreenlet* self, void* UNUSED(context))
{
    const Greenlet *const g = self->pimpl;
    try {
        OwnedObject result(g->context());
        return result.relinquish_ownership();
    }
    catch(const PyErrOccurred&) {
        return nullptr;
    }
}

static int
green_setcontext(PyGreenlet* self, PyObject* nctx, void* UNUSED(context))
{
    try {
        BorrowedGreenlet(self)->context(nctx);
        return 0;
    }
    catch(const PyErrOccurred&) {
        return -1;
    }
}


static PyObject*
green_getframe(PyGreenlet* self, void* UNUSED(context))
{
    const PythonState::OwnedFrame& top_frame = BorrowedGreenlet(self)->top_frame();
    return top_frame.acquire_or_None();
}


static PyObject*
green_getstate(PyGreenlet* self)
{
    PyErr_Format(PyExc_TypeError,
                 "cannot serialize '%s' object",
                 Py_TYPE(self)->tp_name);
    return nullptr;
}

static PyObject*
green_repr(PyGreenlet* _self)
{
    BorrowedGreenlet self(_self);
    /*
      Return a string like
      <greenlet.greenlet at 0xdeadbeef [current][active started]|dead main>

      The handling of greenlets across threads is not super good.
      We mostly use the internal definitions of these terms, but they
      generally should make sense to users as well.
     */
    PyObject* result;
    int never_started = !self->started() && !self->active();

    const char* const tp_name = Py_TYPE(self)->tp_name;

    if (_green_not_dead(self)) {
        /* XXX: The otid= is almost useless because you can't correlate it to
         any thread identifier exposed to Python. We could use
         PyThreadState_GET()->thread_id, but we'd need to save that in the
         greenlet, or save the whole PyThreadState object itself.

         As it stands, its only useful for identifying greenlets from the same thread.
        */
        const char* state_in_thread;
        if (self->was_running_in_dead_thread()) {
            // The thread it was running in is dead!
            // This can happen, especially at interpreter shut down.
            // It complicates debugging output because it may be
            // impossible to access the current thread state at that
            // time. Thus, don't access the current thread state.
            state_in_thread = " (thread exited)";
        }
        else {
            state_in_thread = GET_THREAD_STATE().state().is_current(self)
                ? " current"
                : (self->started() ? " suspended" : "");
        }
        result = PyUnicode_FromFormat(
            "<%s object at %p (otid=%p)%s%s%s%s>",
            tp_name,
            self.borrow_o(),
            self->thread_state(),
            state_in_thread,
            self->active() ? " active" : "",
            never_started ? " pending" : " started",
            self->main() ? " main" : ""
        );
    }
    else {
        result = PyUnicode_FromFormat(
            "<%s object at %p (otid=%p) %sdead>",
            tp_name,
            self.borrow_o(),
            self->thread_state(),
            self->was_running_in_dead_thread()
            ? "(thread exited) "
            : ""
            );
    }

    return result;
}


static PyMethodDef green_methods[] = {
    {
      .ml_name="switch",
      .ml_meth=reinterpret_cast<PyCFunction>(green_switch),
      .ml_flags=METH_VARARGS | METH_KEYWORDS,
      .ml_doc=green_switch_doc
    },
    {.ml_name="throw", .ml_meth=(PyCFunction)green_throw, .ml_flags=METH_VARARGS, .ml_doc=green_throw_doc},
    {.ml_name="__getstate__", .ml_meth=(PyCFunction)green_getstate, .ml_flags=METH_NOARGS, .ml_doc=NULL},
    {.ml_name=NULL, .ml_meth=NULL} /* sentinel */
};

static PyGetSetDef green_getsets[] = {
    /* name, getter, setter, doc, context pointer */
    {.name="__dict__", .get=(getter)green_getdict, .set=(setter)green_setdict},
    {.name="run", .get=(getter)green_getrun, .set=(setter)green_setrun},
    {.name="parent", .get=(getter)green_getparent, .set=(setter)green_setparent},
    {.name="gr_frame", .get=(getter)green_getframe },
    {
      .name="gr_context",
      .get=(getter)green_getcontext,
      .set=(setter)green_setcontext
    },
    {.name="dead", .get=(getter)green_getdead},
    {.name="_stack_saved", .get=(getter)green_get_stack_saved},
    {.name=NULL}
};

static PyMemberDef green_members[] = {
    {.name=NULL}
};

static PyNumberMethods green_as_number = {
  .nb_bool=(inquiry)green_bool,
};


PyTypeObject PyGreenlet_Type = {
    .ob_base=PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name="greenlet.greenlet", /* tp_name */
    .tp_basicsize=sizeof(PyGreenlet),  /* tp_basicsize */
    /* methods */
    .tp_dealloc=(destructor)green_dealloc, /* tp_dealloc */
    .tp_repr=(reprfunc)green_repr,      /* tp_repr */
    .tp_as_number=&green_as_number,          /* tp_as _number*/
    .tp_flags=G_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
    .tp_doc="greenlet(run=None, parent=None) -> greenlet\n\n"
    "Creates a new greenlet object (without running it).\n\n"
    " - *run* -- The callable to invoke.\n"
    " - *parent* -- The parent greenlet. The default is the current "
    "greenlet.",                        /* tp_doc */
    .tp_traverse=(traverseproc)green_traverse, /* tp_traverse */
    .tp_clear=(inquiry)green_clear,         /* tp_clear */
    .tp_weaklistoffset=offsetof(PyGreenlet, weakreflist),  /* tp_weaklistoffset */

    .tp_methods=green_methods,                      /* tp_methods */
    .tp_members=green_members,                      /* tp_members */
    .tp_getset=green_getsets,                      /* tp_getset */
    .tp_dictoffset=offsetof(PyGreenlet, dict),         /* tp_dictoffset */
    .tp_init=(initproc)green_init,               /* tp_init */
    .tp_alloc=PyType_GenericAlloc,                  /* tp_alloc */
    .tp_new=(newfunc)green_new,                          /* tp_new */
    .tp_free=PyObject_GC_Del,                   /* tp_free */
#ifndef Py_GIL_DISABLED
/*
  We may have been handling this wrong all along.

  It shows as a problem with the GIL disabled. In builds of 3.14 with
  assertions enabled, we break the garbage collector if we *ever*
  return false from this function. The docs say this is to distinguish
  some objects that are collectable vs some that are not, specifically
  giving the example of PyTypeObject as the only place this is done,
  where it distinguishes between static types like this one (allocated
  by the C runtime at load time) and dynamic heap types (created at
  runtime as objects). With the GIL disabled, all allocations that are
  potentially collectable go in the mimalloc heap, and the collector
  asserts that tp_is_gc() is true for them as it walks through the
  heap object by object. Since we set the Py_TPFLAGS_HAS_GC bit, we
  are always allocated in that mimalloc heap, so we must always be
  collectable.

  XXX: TODO: Could this be responsible for some apparent leaks, even
  on GIL builds, at least in 3.14? See if we can catch an assertion
  failure in the GC on regular 3.14 as well.
 */
    .tp_is_gc=(inquiry)green_is_gc,         /* tp_is_gc */
#endif
};

#endif

// Local Variables:
// flycheck-clang-include-path: ("/opt/local/Library/Frameworks/Python.framework/Versions/3.8/include/python3.8")
// End:
