/* -*- indent-tabs-mode: nil; tab-width: 4; -*- */
/**
 * Implementation of greenlet::UserGreenlet.
 *
 * Format with:
 *  clang-format -i --style=file src/greenlet/greenlet.c
 *
 *
 * Fix missing braces with:
 *   clang-tidy src/greenlet/greenlet.c -fix -checks="readability-braces-around-statements"
*/
#ifndef T_USER_GREENLET_CPP
#define T_USER_GREENLET_CPP

#include "greenlet_internal.hpp"
#include "TGreenlet.hpp"

#include "TThreadStateDestroy.cpp"


namespace greenlet {
using greenlet::refs::BorrowedMainGreenlet;
greenlet::PythonAllocator<UserGreenlet> UserGreenlet::allocator;

void* UserGreenlet::operator new(size_t UNUSED(count))
{
    return allocator.allocate(1);
}


void UserGreenlet::operator delete(void* ptr)
{
    return allocator.deallocate(static_cast<UserGreenlet*>(ptr),
                                1);
}


UserGreenlet::UserGreenlet(PyGreenlet* p, BorrowedGreenlet the_parent)
    : Greenlet(p), _parent(the_parent)
{
}

UserGreenlet::~UserGreenlet()
{
    // Python 3.11: If we don't clear out the raw frame datastack
    // when deleting an unfinished greenlet,
    // TestLeaks.test_untracked_memory_doesnt_increase_unfinished_thread_dealloc_in_main fails.
    this->python_state.did_finish(nullptr);
    this->tp_clear();
}


const BorrowedMainGreenlet
UserGreenlet::main_greenlet() const
{
    return this->_main_greenlet;
}


BorrowedMainGreenlet
UserGreenlet::find_main_greenlet_in_lineage() const
{
    if (this->started()) {
        assert(this->_main_greenlet);
        return BorrowedMainGreenlet(this->_main_greenlet);
    }

    if (!this->_parent) {
        /* garbage collected greenlet in chain */
        // XXX: WHAT?
        return BorrowedMainGreenlet(nullptr);
    }

    return this->_parent->find_main_greenlet_in_lineage();
}


/**
 * CAUTION: This will allocate memory and may trigger garbage
 * collection and arbitrary Python code.
 */
OwnedObject
UserGreenlet::throw_GreenletExit_during_dealloc(const ThreadState& current_thread_state)
{
    /* The dying greenlet cannot be a parent of ts_current
       because the 'parent' field chain would hold a
       reference */
    UserGreenlet::ParentIsCurrentGuard with_current_parent(this, current_thread_state);

    // We don't care about the return value, only whether an
    // exception happened. Whether or not an exception happens,
    // we need to restore the parent in case the greenlet gets
    // resurrected.
    return Greenlet::throw_GreenletExit_during_dealloc(current_thread_state);
}

ThreadState*
UserGreenlet::thread_state() const noexcept
{
    // TODO: maybe make this throw, if the thread state isn't there?
    // if (!this->main_greenlet) {
    //     throw std::runtime_error("No thread state"); // TODO: Better exception
    // }
    if (!this->_main_greenlet) {
        return nullptr;
    }
    return this->_main_greenlet->thread_state();
}


bool
UserGreenlet::was_running_in_dead_thread() const noexcept
{
    return this->_main_greenlet && !this->thread_state();
}

OwnedObject
UserGreenlet::g_switch()
{
    assert(this->args() || PyErr_Occurred());

    try {
        this->check_switch_allowed();
    }
    catch (const PyErrOccurred&) {
        this->release_args();
        throw;
    }

    // Switching greenlets used to attempt to clean out ones that need
    // deleted *if* we detected a thread switch. Should it still do
    // that?
    // An issue is that if we delete a greenlet from another thread,
    // it gets queued to this thread, and ``kill_greenlet()`` switches
    // back into the greenlet

    /* find the real target by ignoring dead greenlets,
       and if necessary starting a greenlet. */
    switchstack_result_t err;
    Greenlet* target = this;
    // TODO: probably cleaner to handle the case where we do
    // switch to ourself separately from the other cases.
    // This can probably even further be simplified if we keep
    // track of the switching_state we're going for and just call
    // into g_switch() if it's not ourself. The main problem with that
    // is that we would be using more stack space.
    bool target_was_me = true;
    bool was_initial_stub = false;
    while (target) {
        if (target->active()) {
            if (!target_was_me) {
                target->args() <<= this->args();
                assert(!this->args());
            }
            err = target->g_switchstack();
            break;
        }
        if (!target->started()) {
            // We never encounter a main greenlet that's not started.
            assert(!target->main());
            UserGreenlet* real_target = static_cast<UserGreenlet*>(target);
            assert(real_target);
            void* dummymarker;
            was_initial_stub = true;
            if (!target_was_me) {
                target->args() <<= this->args();
                assert(!this->args());
            }
            try {
                // This can only throw back to us while we're
                // still in this greenlet. Once the new greenlet
                // is bootstrapped, it has its own exception state.
                err = real_target->g_initialstub(&dummymarker);
            }
            catch (const PyErrOccurred&) {
                this->release_args();
                throw;
            }
            catch (const GreenletStartedWhileInPython&) {
                // The greenlet was started sometime before this
                // greenlet actually switched to it, i.e.,
                // "concurrent" calls to switch() or throw().
                // We need to retry the switch.
                // Note that the current greenlet has been reset
                // to this one (or we wouldn't be running!)
                continue;
            }
            break;
        }

        target = target->parent();
        target_was_me = false;
    }
    // The ``this`` pointer and all other stack or register based
    // variables are invalid now, at least where things succeed
    // above.
    // But this one, probably not so much? It's not clear if it's
    // safe to throw an exception at this point.

    if (err.status < 0) {
        // If we get here, either g_initialstub()
        // failed, or g_switchstack() failed. Either one of those
        // cases SHOULD leave us in the original greenlet with a valid
        // stack.
        return this->on_switchstack_or_initialstub_failure(target, err, target_was_me, was_initial_stub);
    }

    // err.the_new_current_greenlet would be the same as ``target``,
    // if target wasn't probably corrupt.
    return err.the_new_current_greenlet->g_switch_finish(err);
}



Greenlet::switchstack_result_t
UserGreenlet::g_initialstub(void* mark)
{
    OwnedObject run;

    // We need to grab a reference to the current switch arguments
    // in case we're entered concurrently during the call to
    // GetAttr() and have to try again.
    // We'll restore them when we return in that case.
    // Scope them tightly to avoid ref leaks.
    {
        SwitchingArgs args(this->args());

        /* save exception in case getattr clears it */
        PyErrPieces saved;

        /*
          self.run is the object to call in the new greenlet.
          This could run arbitrary python code and switch greenlets!
        */
        run = this->self().PyRequireAttr(mod_globs->str_run);
        /* restore saved exception */
        saved.PyErrRestore();


        /* recheck that it's safe to switch in case greenlet reparented anywhere above */
        this->check_switch_allowed();

        /* by the time we got here another start could happen elsewhere,
         * that means it should now be a regular switch.
         * This can happen if the Python code is a subclass that implements
         * __getattribute__ or __getattr__, or makes ``run`` a descriptor;
         * all of those can run arbitrary code that switches back into
         * this greenlet.
         */
        if (this->stack_state.started()) {
            // the successful switch cleared these out, we need to
            // restore our version. They will be copied on up to the
            // next target.
            assert(!this->args());
            this->args() <<= args;
            throw GreenletStartedWhileInPython();
        }
    }

    // Sweet, if we got here, we have the go-ahead and will switch
    // greenlets.
    // Nothing we do from here on out should allow for a thread or
    // greenlet switch: No arbitrary calls to Python, including
    // decref'ing

#if GREENLET_USE_CFRAME
    /* OK, we need it, we're about to switch greenlets, save the state. */
    /*
      See green_new(). This is a stack-allocated variable used
      while *self* is in PyObject_Call().
      We want to defer copying the state info until we're sure
      we need it and are in a stable place to do so.
    */
    _PyCFrame trace_info;

    this->python_state.set_new_cframe(trace_info);
#endif
    /* start the greenlet */
    ThreadState& thread_state = GET_THREAD_STATE().state();
    this->stack_state = StackState(mark,
                                   thread_state.borrow_current()->stack_state);
    this->python_state.set_initial_state(PyThreadState_GET());
    this->exception_state.clear();
    this->_main_greenlet = thread_state.get_main_greenlet();

    /* perform the initial switch */
    switchstack_result_t err = this->g_switchstack();
    /* returns twice!
       The 1st time with ``err == 1``: we are in the new greenlet.
       This one owns a greenlet that used to be current.
       The 2nd time with ``err <= 0``: back in the caller's
       greenlet; this happens if the child finishes or switches
       explicitly to us. Either way, the ``err`` variable is
       created twice at the same memory location, but possibly
       having different ``origin`` values. Note that it's not
       constructed for the second time until the switch actually happens.
    */
    if (err.status == 1) {
        // In the new greenlet.

        // This never returns! Calling inner_bootstrap steals
        // the contents of our run object within this stack frame, so
        // it is not valid to do anything with it.
        try {
            this->inner_bootstrap(err.origin_greenlet.relinquish_ownership(),
                                  run.relinquish_ownership());
        }
        // Getting a C++ exception here isn't good. It's probably a
        // bug in the underlying greenlet, meaning it's probably a
        // C++ extension. We're going to abort anyway, but try to
        // display some nice information *if* possible. Some obscure
        // platforms don't properly support this (old 32-bit Arm, see see
        // https://github.com/python-greenlet/greenlet/issues/385); that's not
        // great, but should usually be OK because, as mentioned above, we're
        // terminating anyway.
        //
        // The catching is tested by
        // ``test_cpp.CPPTests.test_unhandled_exception_in_greenlet_aborts``.
        //
        // PyErrOccurred can theoretically be thrown by
        // inner_bootstrap() -> g_switch_finish(), but that should
        // never make it back to here. It is a std::exception and
        // would be caught if it is.
        catch (const std::exception& e) {
            std::string base = "greenlet: Unhandled C++ exception: ";
            base += e.what();
            Py_FatalError(base.c_str());
        }
        catch (...) {
            // Some compilers/runtimes use exceptions internally.
            // It appears that GCC on Linux with libstdc++ throws an
            // exception internally at process shutdown time to unwind
            // stacks and clean up resources. Depending on exactly
            // where we are when the process exits, that could result
            // in an unknown exception getting here. If we
            // Py_FatalError() or abort() here, we interfere with
            // orderly process shutdown. Throwing the exception on up
            // is the right thing to do.
            //
            // gevent's ``examples/dns_mass_resolve.py`` demonstrates this.
#ifndef NDEBUG
            fprintf(stderr,
                    "greenlet: inner_bootstrap threw unknown exception; "
                    "is the process terminating?\n");
#endif
            throw;
        }
        Py_FatalError("greenlet: inner_bootstrap returned with no exception.\n");
    }


    // In contrast, notice that we're keeping the origin greenlet
    // around as an owned reference; we need it to call the trace
    // function for the switch back into the parent. It was only
    // captured at the time the switch actually happened, though,
    // so we haven't been keeping an extra reference around this
    // whole time.

    /* back in the parent */
    if (err.status < 0) {
        /* start failed badly, restore greenlet state */
        this->stack_state = StackState();
        this->_main_greenlet.CLEAR();
        // CAUTION: This may run arbitrary Python code.
        run.CLEAR(); // inner_bootstrap didn't run, we own the reference.
    }

    // In the success case, the spawned code (inner_bootstrap) will
    // take care of decrefing this, so we relinquish ownership so as
    // to not double-decref.

    run.relinquish_ownership();

    return err;
}


void
UserGreenlet::inner_bootstrap(PyGreenlet* origin_greenlet, PyObject* run)
{
    // The arguments here would be another great place for move.
    // As it is, we take them as a reference so that when we clear
    // them we clear what's on the stack above us. Do that NOW, and
    // without using a C++ RAII object,
    // so there's no way that exiting the parent frame can clear it,
    // or we clear it unexpectedly. This arises in the context of the
    // interpreter shutting down. See https://github.com/python-greenlet/greenlet/issues/325
    //PyObject* run = _run.relinquish_ownership();

    /* in the new greenlet */
    assert(this->thread_state()->borrow_current() == BorrowedGreenlet(this->_self));
    // C++ exceptions cannot propagate to the parent greenlet from
    // here. (TODO: Do we need a catch(...) clause, perhaps on the
    // function itself? ALl we could do is terminate the program.)
    // NOTE: On 32-bit Windows, the call chain is extremely
    // important here in ways that are subtle, having to do with
    // the depth of the SEH list. The call to restore it MUST NOT
    // add a new SEH handler to the list, or we'll restore it to
    // the wrong thing.
    this->thread_state()->restore_exception_state();
    /* stack variables from above are no good and also will not unwind! */
    // EXCEPT: That can't be true, we access run, among others, here.

    this->stack_state.set_active(); /* running */

    // We're about to possibly run Python code again, which
    // could switch back/away to/from us, so we need to grab the
    // arguments locally.
    SwitchingArgs args;
    args <<= this->args();
    assert(!this->args());

    // XXX: We could clear this much earlier, right?
    // Or would that introduce the possibility of running Python
    // code when we don't want to?
    // CAUTION: This may run arbitrary Python code.
    this->_run_callable.CLEAR();


    // The first switch we need to manually call the trace
    // function here instead of in g_switch_finish, because we
    // never return there.
    if (OwnedObject tracefunc = this->thread_state()->get_tracefunc()) {
        OwnedGreenlet trace_origin;
        trace_origin = origin_greenlet;
        try {
            g_calltrace(tracefunc,
                        args ? mod_globs->event_switch : mod_globs->event_throw,
                        trace_origin,
                        this->_self);
        }
        catch (const PyErrOccurred&) {
            /* Turn trace errors into switch throws */
            args.CLEAR();
        }
    }

    // We no longer need the origin, it was only here for
    // tracing.
    // We may never actually exit this stack frame so we need
    // to explicitly clear it.
    // This could run Python code and switch.
    Py_CLEAR(origin_greenlet);

    OwnedObject result;
    if (!args) {
        /* pending exception */
        result = NULL;
    }
    else {
        /* call g.run(*args, **kwargs) */
        // This could result in further switches
        try {
            //result = run.PyCall(args.args(), args.kwargs());
            // CAUTION: Just invoking this, before the function even
            // runs, may cause memory allocations, which may trigger
            // GC, which may run arbitrary Python code.
            result = OwnedObject::consuming(PyObject_Call(run, args.args().borrow(), args.kwargs().borrow()));
        }
        catch (...) {
            // Unhandled C++ exception!

            // If we declare ourselves as noexcept, if we don't catch
            // this here, most platforms will just abort() the
            // process. But on 64-bit Windows with older versions of
            // the C runtime, this can actually corrupt memory and
            // just return. We see this when compiling with the
            // Windows 7.0 SDK targeting Windows Server 2008, but not
            // when using the Appveyor Visual Studio 2019 image. So
            // this currently only affects Python 2.7 on Windows 64.
            // That is, the tests pass and the runtime aborts
            // everywhere else.
            //
            // However, if we catch it and try to continue with a
            // Python error, then all Windows 64 bit platforms corrupt
            // memory. So all we can do is manually abort, hopefully
            // with a good error message. (Note that the above was
            // tested WITHOUT the `/EHr` switch being used at compile
            // time, so MSVC may have "optimized" out important
            // checking. Using that switch, we may be in a better
            // place in terms of memory corruption.) But sometimes it
            // can't be caught here at all, which is confusing but not
            // terribly surprising; so again, the G_NOEXCEPT_WIN32
            // plus "/EHr".
            //
            // Hopefully the basic C stdlib is still functional enough
            // for us to at least print an error.
            //
            // It gets more complicated than that, though, on some
            // platforms, specifically at least Linux/gcc/libstdc++. They use
            // an exception to unwind the stack when a background
            // thread exits. (See comments about noexcept.) So this
            // may not actually represent anything untoward. On those
            // platforms we allow throws of this to propagate, or
            // attempt to anyway.
# if defined(WIN32) || defined(_WIN32)
            Py_FatalError(
                "greenlet: Unhandled C++ exception from a greenlet run function. "
                "Because memory is likely corrupted, terminating process.");
            std::abort();
#else
            throw;
#endif
        }
    }
    // These lines may run arbitrary code
    args.CLEAR();
    Py_CLEAR(run);

    if (!result
        && mod_globs->PyExc_GreenletExit.PyExceptionMatches()
        && (this->args())) {
        // This can happen, for example, if our only reference
        // goes away after we switch back to the parent.
        // See test_dealloc_switch_args_not_lost
        PyErrPieces clear_error;
        result <<= this->args();
        result = single_result(result);
    }
    this->release_args();
    this->python_state.did_finish(PyThreadState_GET());

    result = g_handle_exit(result);
    assert(this->thread_state()->borrow_current() == this->_self);

    /* jump back to parent */
    this->stack_state.set_inactive(); /* dead */


    // TODO: Can we decref some things here? Release our main greenlet
    // and maybe parent?
    for (Greenlet* parent = this->_parent;
         parent;
         parent = parent->parent()) {
        // We need to somewhere consume a reference to
        // the result; in most cases we'll never have control
        // back in this stack frame again. Calling
        // green_switch actually adds another reference!
        // This would probably be clearer with a specific API
        // to hand results to the parent.
        parent->args() <<= result;
        assert(!result);
        // The parent greenlet now owns the result; in the
        // typical case we'll never get back here to assign to
        // result and thus release the reference.
        try {
            result = parent->g_switch();
        }
        catch (const PyErrOccurred&) {
            // Ignore, keep passing the error on up.
        }

        /* Return here means switch to parent failed,
         * in which case we throw *current* exception
         * to the next parent in chain.
         */
        assert(!result);
    }
    /* We ran out of parents, cannot continue */
    PyErr_WriteUnraisable(this->self().borrow_o());
    Py_FatalError("greenlet: ran out of parent greenlets while propagating exception; "
                  "cannot continue");
    std::abort();
}

void
UserGreenlet::run(const BorrowedObject nrun)
{
    if (this->started()) {
        throw AttributeError(
                        "run cannot be set "
                        "after the start of the greenlet");
    }
    this->_run_callable = nrun;
}

const OwnedGreenlet
UserGreenlet::parent() const
{
    return this->_parent;
}

void
UserGreenlet::parent(const BorrowedObject raw_new_parent)
{
    if (!raw_new_parent) {
        throw AttributeError("can't delete attribute");
    }

    BorrowedMainGreenlet main_greenlet_of_new_parent;
    BorrowedGreenlet new_parent(raw_new_parent.borrow()); // could
                                                          // throw
                                                          // TypeError!
    for (BorrowedGreenlet p = new_parent; p; p = p->parent()) {
        if (p == this->self()) {
            throw ValueError("cyclic parent chain");
        }
        main_greenlet_of_new_parent = p->main_greenlet();
    }

    if (!main_greenlet_of_new_parent) {
        throw ValueError("parent must not be garbage collected");
    }

    if (this->started()
        && this->_main_greenlet != main_greenlet_of_new_parent) {
        throw ValueError("parent cannot be on a different thread");
    }

    this->_parent = new_parent;
}

void
UserGreenlet::murder_in_place()
{
    this->_main_greenlet.CLEAR();
    Greenlet::murder_in_place();
}

bool
UserGreenlet::belongs_to_thread(const ThreadState* thread_state) const
{
    return Greenlet::belongs_to_thread(thread_state) && this->_main_greenlet == thread_state->borrow_main_greenlet();
}


int
UserGreenlet::tp_traverse(visitproc visit, void* arg)
{
    Py_VISIT(this->_parent.borrow_o());
    Py_VISIT(this->_main_greenlet.borrow_o());
    Py_VISIT(this->_run_callable.borrow_o());

    return Greenlet::tp_traverse(visit, arg);
}

int
UserGreenlet::tp_clear()
{
    Greenlet::tp_clear();
    this->_parent.CLEAR();
    this->_main_greenlet.CLEAR();
    this->_run_callable.CLEAR();
    return 0;
}

UserGreenlet::ParentIsCurrentGuard::ParentIsCurrentGuard(UserGreenlet* p,
                                                     const ThreadState& thread_state)
    : oldparent(p->_parent),
      greenlet(p)
{
    p->_parent = thread_state.get_current();
}

UserGreenlet::ParentIsCurrentGuard::~ParentIsCurrentGuard()
{
    this->greenlet->_parent = oldparent;
    oldparent.CLEAR();
}

}; //namespace greenlet
#endif
