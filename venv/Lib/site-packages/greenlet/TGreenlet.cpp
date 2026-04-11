/* -*- indent-tabs-mode: nil; tab-width: 4; -*- */
/**
 * Implementation of greenlet::Greenlet.
 *
 * Format with:
 *  clang-format -i --style=file src/greenlet/greenlet.c
 *
 *
 * Fix missing braces with:
 *   clang-tidy src/greenlet/greenlet.c -fix -checks="readability-braces-around-statements"
*/
#ifndef TGREENLET_CPP
#define TGREENLET_CPP
#include "greenlet_internal.hpp"
#include "TGreenlet.hpp"


#include "TGreenletGlobals.cpp"
#include "TThreadStateDestroy.cpp"

namespace greenlet {

Greenlet::Greenlet(PyGreenlet* p)
    :  Greenlet(p, StackState())
{
}

Greenlet::Greenlet(PyGreenlet* p, const StackState& initial_stack)
    :  _self(p), stack_state(initial_stack)
{
    assert(p->pimpl == nullptr);
    p->pimpl = this;
}

Greenlet::~Greenlet()
{
    // XXX: Can't do this. tp_clear is a virtual function, and by the
    // time we're here, we've sliced off our child classes.
    //this->tp_clear();
    this->_self->pimpl = nullptr;
}

bool
Greenlet::force_slp_switch_error() const noexcept
{
    return false;
}

void
Greenlet::release_args()
{
    this->switch_args.CLEAR();
}

/**
 * CAUTION: This will allocate memory and may trigger garbage
 * collection and arbitrary Python code.
 */
OwnedObject
Greenlet::throw_GreenletExit_during_dealloc(const ThreadState& UNUSED(current_thread_state))
{
    // If we're killed because we lost all references in the
    // middle of a switch, that's ok. Don't reset the args/kwargs,
    // we still want to pass them to the parent.
    PyErr_SetString(mod_globs->PyExc_GreenletExit,
                    "Killing the greenlet because all references have vanished.");
    // To get here it had to have run before
    return this->g_switch();
}

inline void
Greenlet::slp_restore_state() noexcept
{
#ifdef SLP_BEFORE_RESTORE_STATE
    SLP_BEFORE_RESTORE_STATE();
#endif
    this->stack_state.copy_heap_to_stack(
           this->thread_state()->borrow_current()->stack_state);
}


inline int
Greenlet::slp_save_state(char *const stackref) noexcept
{
    // XXX: This used to happen in the middle, before saving, but
    // after finding the next owner. Does that matter? This is
    // only defined for Sparc/GCC where it flushes register
    // windows to the stack (I think)
#ifdef SLP_BEFORE_SAVE_STATE
    SLP_BEFORE_SAVE_STATE();
#endif
    return this->stack_state.copy_stack_to_heap(stackref,
                                                this->thread_state()->borrow_current()->stack_state);
}

/**
 * CAUTION: This will allocate memory and may trigger garbage
 * collection and arbitrary Python code.
 */
OwnedObject
Greenlet::on_switchstack_or_initialstub_failure(
    Greenlet* target,
    const Greenlet::switchstack_result_t& err,
    const bool target_was_me,
    const bool was_initial_stub)
{
    // If we get here, either g_initialstub()
    // failed, or g_switchstack() failed. Either one of those
    // cases SHOULD leave us in the original greenlet with a valid stack.
    if (!PyErr_Occurred()) {
        PyErr_SetString(
            PyExc_SystemError,
            was_initial_stub
            ? "Failed to switch stacks into a greenlet for the first time."
            : "Failed to switch stacks into a running greenlet.");
    }
    this->release_args();

    if (target && !target_was_me) {
        target->murder_in_place();
    }

    assert(!err.the_new_current_greenlet);
    assert(!err.origin_greenlet);
    return OwnedObject();

}

OwnedGreenlet
Greenlet::g_switchstack_success() noexcept
{
    PyThreadState* tstate = PyThreadState_GET();
    // restore the saved state
    this->python_state >> tstate;
    this->exception_state >> tstate;

    // The thread state hasn't been changed yet.
    ThreadState* thread_state = this->thread_state();
    OwnedGreenlet result(thread_state->get_current());
    thread_state->set_current(this->self());
    //assert(thread_state->borrow_current().borrow() == this->_self);
    return result;
}

Greenlet::switchstack_result_t
Greenlet::g_switchstack(void)
{
    // if any of these assertions fail, it's likely because we
    // switched away and tried to switch back to us. Early stages of
    // switching are not reentrant because we re-use ``this->args()``.
    // Switching away would happen if we trigger a garbage collection
    // (by just using some Python APIs that happen to allocate Python
    // objects) and some garbage had weakref callbacks or __del__ that
    // switches (people don't write code like that by hand, but with
    // gevent it's possible without realizing it)
    assert(this->args() || PyErr_Occurred());
    { /* save state */
        if (this->thread_state()->is_current(this->self())) {
            // Hmm, nothing to do.
            // TODO: Does this bypass trace events that are
            // important?
            return switchstack_result_t(0,
                                        this, this->thread_state()->borrow_current());
        }
        BorrowedGreenlet current = this->thread_state()->borrow_current();
        PyThreadState* tstate = PyThreadState_GET();

        current->python_state << tstate;
        current->exception_state << tstate;
        this->python_state.will_switch_from(tstate);
        switching_thread_state = this;
        current->expose_frames();
    }
    assert(this->args() || PyErr_Occurred());
    // If this is the first switch into a greenlet, this will
    // return twice, once with 1 in the new greenlet, once with 0
    // in the origin.
    int err;
    if (this->force_slp_switch_error()) {
        err = -1;
    }
    else {
        err = slp_switch();
    }

    if (err < 0) { /* error */
        // Tested by
        // test_greenlet.TestBrokenGreenlets.test_failed_to_slp_switch_into_running
        //
        // It's not clear if it's worth trying to clean up and
        // continue here. Failing to switch stacks is a big deal which
        // may not be recoverable (who knows what state the stack is in).
        // Also, we've stolen references in preparation for calling
        // ``g_switchstack_success()`` and we don't have a clean
        // mechanism for backing that all out.
        Py_FatalError("greenlet: Failed low-level slp_switch(). The stack is probably corrupt.");
    }

    // No stack-based variables are valid anymore.

    // But the global is volatile so we can reload it without the
    // compiler caching it from earlier.
    Greenlet* greenlet_that_switched_in = switching_thread_state; // aka this
    switching_thread_state = nullptr;
    // except that no stack variables are valid, we would:
    // assert(this == greenlet_that_switched_in);

    // switchstack success is where we restore the exception state,
    // etc. It returns the origin greenlet because its convenient.

    OwnedGreenlet origin = greenlet_that_switched_in->g_switchstack_success();
    assert(greenlet_that_switched_in->args() || PyErr_Occurred());
    return switchstack_result_t(err, greenlet_that_switched_in, origin);
}


inline void
Greenlet::check_switch_allowed() const
{
    // TODO: Make this take a parameter of the current greenlet,
    // or current main greenlet, to make the check for
    // cross-thread switching cheaper. Surely somewhere up the
    // call stack we've already accessed the thread local variable.

    // We expect to always have a main greenlet now; accessing the thread state
    // created it. However, if we get here and cleanup has already
    // begun because we're a greenlet that was running in a
    // (now dead) thread, these invariants will not hold true. In
    // fact, accessing `this->thread_state` may not even be possible.

    // If the thread this greenlet was running in is dead,
    // we'll still have a reference to a main greenlet, but the
    // thread state pointer we have is bogus.
    // TODO: Give the objects an API to determine if they belong
    // to a dead thread.

    const BorrowedMainGreenlet main_greenlet = this->find_main_greenlet_in_lineage();

    if (!main_greenlet) {
        throw PyErrOccurred(mod_globs->PyExc_GreenletError,
                            "cannot switch to a garbage collected greenlet");
    }

    if (!main_greenlet->thread_state()) {
        throw PyErrOccurred(mod_globs->PyExc_GreenletError,
                            "cannot switch to a different thread (which happens to have exited)");
    }

    // The main greenlet we found was from the .parent lineage.
    // That may or may not have any relationship to the main
    // greenlet of the running thread. We can't actually access
    // our this->thread_state members to try to check that,
    // because it could be in the process of getting destroyed,
    // but setting the main_greenlet->thread_state member to NULL
    // may not be visible yet. So we need to check against the
    // current thread state (once the cheaper checks are out of
    // the way)
    const BorrowedMainGreenlet current_main_greenlet = GET_THREAD_STATE().state().borrow_main_greenlet();
    if (
        // lineage main greenlet is not this thread's greenlet
        current_main_greenlet != main_greenlet
        || (
            // atteched to some thread
            this->main_greenlet()
            // XXX: Same condition as above. Was this supposed to be
            // this->main_greenlet()?
            && current_main_greenlet != main_greenlet)
        // switching into a known dead thread (XXX: which, if we get here,
        // is bad, because we just accessed the thread state, which is
        // gone!)
        || (!current_main_greenlet->thread_state())) {
        // CAUTION: This may trigger memory allocations, gc, and
        // arbitrary Python code.
        throw PyErrOccurred(
            mod_globs->PyExc_GreenletError,
            "Cannot switch to a different thread\n\tCurrent:  %R\n\tExpected: %R",
            current_main_greenlet, main_greenlet);
    }
}

const OwnedObject
Greenlet::context() const
{
    using greenlet::PythonStateContext;
    OwnedObject result;

    if (this->is_currently_running_in_some_thread()) {
        /* Currently running greenlet: context is stored in the thread state,
           not the greenlet object. */
        if (GET_THREAD_STATE().state().is_current(this->self())) {
            result = PythonStateContext::context(PyThreadState_GET());
        }
        else {
            throw ValueError(
                            "cannot get context of a "
                            "greenlet that is running in a different thread");
        }
    }
    else {
        /* Greenlet is not running: just return context. */
        result = this->python_state.context();
    }
    if (!result) {
        result = OwnedObject::None();
    }
    return result;
}


void
Greenlet::context(BorrowedObject given)
{
    using greenlet::PythonStateContext;
    if (!given) {
        throw AttributeError("can't delete context attribute");
    }
    if (given.is_None()) {
        /* "Empty context" is stored as NULL, not None. */
        given = nullptr;
    }

    //checks type, incrs refcnt
    greenlet::refs::OwnedContext context(given);
    PyThreadState* tstate = PyThreadState_GET();

    if (this->is_currently_running_in_some_thread()) {
        if (!GET_THREAD_STATE().state().is_current(this->self())) {
            throw ValueError("cannot set context of a greenlet"
                             " that is running in a different thread");
        }

        /* Currently running greenlet: context is stored in the thread state,
           not the greenlet object. */
        OwnedObject octx = OwnedObject::consuming(PythonStateContext::context(tstate));
        PythonStateContext::context(tstate, context.relinquish_ownership());
    }
    else {
        /* Greenlet is not running: just set context. Note that the
           greenlet may be dead.*/
        this->python_state.context() = context;
    }
}

/**
 * CAUTION: May invoke arbitrary Python code.
 *
 * Figure out what the result of ``greenlet.switch(arg, kwargs)``
 * should be and transfers ownership of it to the left-hand-side.
 *
 * If switch() was just passed an arg tuple, then we'll just return that.
 * If only keyword arguments were passed, then we'll pass the keyword
 * argument dict. Otherwise, we'll create a tuple of (args, kwargs) and
 * return both.
 *
 * CAUTION: This may allocate a new tuple object, which may
 * cause the Python garbage collector to run, which in turn may
 * run arbitrary Python code that switches.
 */
OwnedObject& operator<<=(OwnedObject& lhs, greenlet::SwitchingArgs& rhs) noexcept
{
    // Because this may invoke arbitrary Python code, which could
    // result in switching back to us, we need to get the
    // arguments locally on the stack.
    assert(rhs);
    OwnedObject args = rhs.args();
    OwnedObject kwargs = rhs.kwargs();
    rhs.CLEAR();
    // We shouldn't be called twice for the same switch.
    assert(args || kwargs);
    assert(!rhs);

    if (!kwargs) {
        lhs = args;
    }
    else if (!PyDict_Size(kwargs.borrow())) {
        lhs = args;
    }
    else if (!PySequence_Length(args.borrow())) {
        lhs = kwargs;
    }
    else {
        // PyTuple_Pack allocates memory, may GC, may run arbitrary
        // Python code.
        lhs = OwnedObject::consuming(PyTuple_Pack(2, args.borrow(), kwargs.borrow()));
    }
    return lhs;
}

static OwnedObject
g_handle_exit(const OwnedObject& greenlet_result)
{
    if (!greenlet_result && mod_globs->PyExc_GreenletExit.PyExceptionMatches()) {
        /* catch and ignore GreenletExit */
        PyErrFetchParam val;
        PyErr_Fetch(PyErrFetchParam(), val, PyErrFetchParam());
        if (!val) {
            return OwnedObject::None();
        }
        return OwnedObject(val);
    }

    if (greenlet_result) {
        // package the result into a 1-tuple
        // PyTuple_Pack increments the reference of its arguments,
        // so we always need to decref the greenlet result;
        // the owner will do that.
        return OwnedObject::consuming(PyTuple_Pack(1, greenlet_result.borrow()));
    }

    return OwnedObject();
}



/**
 * May run arbitrary Python code.
 */
OwnedObject
Greenlet::g_switch_finish(const switchstack_result_t& err)
{
    assert(err.the_new_current_greenlet == this);

    ThreadState& state = *this->thread_state();
    // Because calling the trace function could do arbitrary things,
    // including switching away from this greenlet and then maybe
    // switching back, we need to capture the arguments now so that
    // they don't change.
    OwnedObject result;
    if (this->args()) {
        result <<= this->args();
    }
    else {
        assert(PyErr_Occurred());
    }
    assert(!this->args());
    try {
        // Our only caller handles the bad error case
        assert(err.status >= 0);
        assert(state.borrow_current() == this->self());
        if (OwnedObject tracefunc = state.get_tracefunc()) {
            assert(result || PyErr_Occurred());
            g_calltrace(tracefunc,
                        result ? mod_globs->event_switch : mod_globs->event_throw,
                        err.origin_greenlet,
                        this->self());
        }
        // The above could have invoked arbitrary Python code, but
        // it couldn't switch back to this object and *also*
        // throw an exception, so the args won't have changed.

        if (PyErr_Occurred()) {
            // We get here if we fell of the end of the run() function
            // raising an exception. The switch itself was
            // successful, but the function raised.
            // valgrind reports that memory allocated here can still
            // be reached after a test run.
            throw PyErrOccurred::from_current();
        }
        return result;
    }
    catch (const PyErrOccurred&) {
        /* Turn switch errors into switch throws */
        /* Turn trace errors into switch throws */
        this->release_args();
        throw;
    }
}

void
Greenlet::g_calltrace(const OwnedObject& tracefunc,
                      const greenlet::refs::ImmortalEventName& event,
                      const BorrowedGreenlet& origin,
                      const BorrowedGreenlet& target)
{
    PyErrPieces saved_exc;
    try {
        TracingGuard tracing_guard;
        // TODO: We have saved the active exception (if any) that's
        // about to be raised. In the 'throw' case, we could provide
        // the exception to the tracefunction, which seems very helpful.
        tracing_guard.CallTraceFunction(tracefunc, event, origin, target);
    }
    catch (const PyErrOccurred&) {
        // In case of exceptions trace function is removed,
        // and any existing exception is replaced with the tracing
        // exception.
        GET_THREAD_STATE().state().set_tracefunc(Py_None);
        throw;
    }

    saved_exc.PyErrRestore();
    assert(
        (event == mod_globs->event_throw && PyErr_Occurred())
        || (event == mod_globs->event_switch && !PyErr_Occurred())
    );
}

void
Greenlet::murder_in_place()
{
    if (this->active()) {
        assert(!this->is_currently_running_in_some_thread());
        this->deactivate_and_free();
    }
}

inline void
Greenlet::deactivate_and_free()
{
    if (!this->active()) {
        return;
    }
    // Throw away any saved stack.
    this->stack_state = StackState();
    assert(!this->stack_state.active());
    // Throw away any Python references.
    // We're holding a borrowed reference to the last
    // frame we executed. Since we borrowed it, the
    // normal traversal, clear, and dealloc functions
    // ignore it, meaning it leaks. (The thread state
    // object can't find it to clear it when that's
    // deallocated either, because by definition if we
    // got an object on this list, it wasn't
    // running and the thread state doesn't have
    // this frame.)
    // So here, we *do* clear it.
    this->python_state.tp_clear(true);
}

bool
Greenlet::belongs_to_thread(const ThreadState* thread_state) const
{
    if (!this->thread_state() // not running anywhere, or thread
                              // exited
        || !thread_state) { // same, or there is no thread state.
        return false;
    }
    return true;
}


void
Greenlet::deallocing_greenlet_in_thread(const ThreadState* current_thread_state)
{
    /* Cannot raise an exception to kill the greenlet if
       it is not running in the same thread! */
    if (this->belongs_to_thread(current_thread_state)) {
        assert(current_thread_state);
        // To get here it had to have run before
        /* Send the greenlet a GreenletExit exception. */

        // We don't care about the return value, only whether an
        // exception happened.
        this->throw_GreenletExit_during_dealloc(*current_thread_state);
        return;
    }

    // Not the same thread! Temporarily save the greenlet
    // into its thread's deleteme list, *if* it exists.
    // If that thread has already exited, and processed its pending
    // cleanup, we'll never be able to clean everything up: we won't
    // be able to raise an exception.
    // That's mostly OK! Since we can't add it to a list, our refcount
    // won't increase, and we'll go ahead with the DECREFs later.

    ThreadState *const  thread_state = this->thread_state();
    if (thread_state) {
        thread_state->delete_when_thread_running(this->self());
    }
    else {
        // The thread is dead, we can't raise an exception.
        // We need to make it look non-active, though, so that dealloc
        // finishes killing it.
        this->deactivate_and_free();
    }
    return;
}


int
Greenlet::tp_traverse(visitproc visit, void* arg)
{

    int result;
    if ((result = this->exception_state.tp_traverse(visit, arg)) != 0) {
        return result;
    }
    //XXX: This is ugly. But so is handling everything having to do
    //with the top frame.
    bool visit_top_frame = this->was_running_in_dead_thread();
    // When true, the thread is dead. Our implicit weak reference to the
    // frame is now all that's left; we consider ourselves to
    // strongly own it now.
    if ((result = this->python_state.tp_traverse(visit, arg, visit_top_frame)) != 0) {
        return result;
    }
    return 0;
}

int
Greenlet::tp_clear()
{
    bool own_top_frame = this->was_running_in_dead_thread();
    this->exception_state.tp_clear();
    this->python_state.tp_clear(own_top_frame);
    return 0;
}

bool Greenlet::is_currently_running_in_some_thread() const
{
    return this->stack_state.active() && !this->python_state.top_frame();
}

#if GREENLET_PY312
void GREENLET_NOINLINE(Greenlet::expose_frames)()
{
    if (!this->python_state.top_frame()) {
        return;
    }

    _PyInterpreterFrame* last_complete_iframe = nullptr;
    _PyInterpreterFrame* iframe = this->python_state.top_frame()->f_frame;
    while (iframe) {
        // We must make a copy before looking at the iframe contents,
        // since iframe might point to a portion of the greenlet's C stack
        // that was spilled when switching greenlets.
        _PyInterpreterFrame iframe_copy;
        this->stack_state.copy_from_stack(&iframe_copy, iframe, sizeof(*iframe));
        if (!_PyFrame_IsIncomplete(&iframe_copy)) {
            // If the iframe were OWNED_BY_CSTACK then it would always be
            // incomplete. Since it's not incomplete, it's not on the C stack
            // and we can access it through the original `iframe` pointer
            // directly.  This is important since GetFrameObject might
            // lazily _create_ the frame object and we don't want the
            // interpreter to lose track of it.
            //
            #if !GREENLET_PY315
            // This enum value was removed in
            //    https://github.com/python/cpython/pull/141108

            assert(iframe_copy.owner != FRAME_OWNED_BY_CSTACK);
            #endif

            // We really want to just write:
            //     PyFrameObject* frame = _PyFrame_GetFrameObject(iframe);
            // but _PyFrame_GetFrameObject calls _PyFrame_MakeAndSetFrameObject
            // which is not a visible symbol in libpython. The easiest
            // way to get a public function to call it is using
            // PyFrame_GetBack, which is defined as follows:
            //     assert(frame != NULL);
            //     assert(!_PyFrame_IsIncomplete(frame->f_frame));
            //     PyFrameObject *back = frame->f_back;
            //     if (back == NULL) {
            //         _PyInterpreterFrame *prev = frame->f_frame->previous;
            //         prev = _PyFrame_GetFirstComplete(prev);
            //         if (prev) {
            //             back = _PyFrame_GetFrameObject(prev);
            //         }
            //     }
            //     return (PyFrameObject*)Py_XNewRef(back);
            if (!iframe->frame_obj) {
                PyFrameObject dummy_frame;
                _PyInterpreterFrame dummy_iframe;
                dummy_frame.f_back = nullptr;
                dummy_frame.f_frame = &dummy_iframe;
                // force the iframe to be considered complete without
                // needing to check its code object:
                dummy_iframe.owner = FRAME_OWNED_BY_GENERATOR;
                dummy_iframe.previous = iframe;
                assert(!_PyFrame_IsIncomplete(&dummy_iframe));
                // Drop the returned reference immediately; the iframe
                // continues to hold a strong reference
                Py_XDECREF(PyFrame_GetBack(&dummy_frame));
                assert(iframe->frame_obj);
            }

            // This is a complete frame, so make the last one of those we saw
            // point at it, bypassing any incomplete frames (which may have
            // been on the C stack) in between the two. We're overwriting
            // last_complete_iframe->previous and need that to be reversible,
            // so we store the original previous ptr in the frame object
            // (which we must have created on a previous iteration through
            // this loop). The frame object has a bunch of storage that is
            // only used when its iframe is OWNED_BY_FRAME_OBJECT, which only
            // occurs when the frame object outlives the frame's execution,
            // which can't have happened yet because the frame is currently
            // executing as far as the interpreter is concerned. So, we can
            // reuse it for our own purposes.
            assert(iframe->owner == FRAME_OWNED_BY_THREAD
                   || iframe->owner == FRAME_OWNED_BY_GENERATOR);
            if (last_complete_iframe) {
                assert(last_complete_iframe->frame_obj);
                memcpy(&last_complete_iframe->frame_obj->_f_frame_data[0],
                       &last_complete_iframe->previous, sizeof(void *));
                last_complete_iframe->previous = iframe;
            }
            last_complete_iframe = iframe;
        }
        // Frames that are OWNED_BY_FRAME_OBJECT are linked via the
        // frame's f_back while all others are linked via the iframe's
        // previous ptr. Since all the frames we traverse are running
        // as far as the interpreter is concerned, we don't have to
        // worry about the OWNED_BY_FRAME_OBJECT case.
        iframe = iframe_copy.previous;
    }

    // Give the outermost complete iframe a null previous pointer to
    // account for any potential incomplete/C-stack iframes between it
    // and the actual top-of-stack
    if (last_complete_iframe) {
        assert(last_complete_iframe->frame_obj);
        memcpy(&last_complete_iframe->frame_obj->_f_frame_data[0],
               &last_complete_iframe->previous, sizeof(void *));
        last_complete_iframe->previous = nullptr;
    }
}
#else
void Greenlet::expose_frames()
{

}
#endif

}; // namespace greenlet
#endif
