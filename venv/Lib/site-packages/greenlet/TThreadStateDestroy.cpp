/* -*- indent-tabs-mode: nil; tab-width: 4; -*- */
/**
 * Implementation of the ThreadState destructors.
 *
 * Format with:
 *  clang-format -i --style=file src/greenlet/greenlet.c
 *
 *
 * Fix missing braces with:
 *   clang-tidy src/greenlet/greenlet.c -fix -checks="readability-braces-around-statements"
*/
#ifndef T_THREADSTATE_DESTROY
#define T_THREADSTATE_DESTROY

#include "TGreenlet.hpp"

#include "greenlet_thread_support.hpp"
#include "greenlet_compiler_compat.hpp"
#include "TGreenletGlobals.cpp"
#include "TThreadState.hpp"
#include "TThreadStateCreator.hpp"

namespace greenlet {

extern "C" {

struct ThreadState_DestroyNoGIL
{
    /**
       This function uses the same lock that the PendingCallback does
     */
    static void
    MarkGreenletDeadAndQueueCleanup(ThreadState* const state)
    {
#if GREENLET_BROKEN_THREAD_LOCAL_CLEANUP_JUST_LEAK
        // One rare platform.
        return;
#endif
        // We are *NOT* holding the GIL. Our thread is in the middle
        // of its death throes and the Python thread state is already
        // gone so we can't use most Python APIs. One that is safe is
        // ``Py_AddPendingCall``, unless the interpreter itself has
        // been torn down. There is a limited number of calls that can
        // be queued: 32 (NPENDINGCALLS) in CPython 3.10, so we
        // coalesce these calls using our own queue.

        if (!MarkGreenletDeadIfNeeded(state)) {
            // No state, or no greenlet
            return;
        }

        // XXX: Because we don't have the GIL, this is a race condition.
        if (!PyInterpreterState_Head()) {
            // We have to leak the thread state, if the
            // interpreter has shut down when we're getting
            // deallocated, we can't run the cleanup code that
            // deleting it would imply.
            return;
        }

        AddToCleanupQueue(state);

    }

private:

    // If the state has an allocated main greenlet:
    // - mark the greenlet as dead by disassociating it from the state;
    // - return 1
    // Otherwise, return 0.
    static bool
    MarkGreenletDeadIfNeeded(ThreadState* const state)
    {
        if (!state) {
            return false;
        }
        LockGuard cleanup_lock(*mod_globs->thread_states_to_destroy_lock);
        if (state->has_main_greenlet()) {
            // mark the thread as dead ASAP.
            // this is racy! If we try to throw or switch to a
            // greenlet from this thread from some other thread before
            // we clear the state pointer, it won't realize the state
            // is dead which can crash the process.
            PyGreenlet* p(state->borrow_main_greenlet().borrow());
            assert(p->pimpl->thread_state() == state || p->pimpl->thread_state() == nullptr);
            dynamic_cast<MainGreenlet*>(p->pimpl)->thread_state(nullptr);
           return true;
        }
        return false;
    }

    static void
    AddToCleanupQueue(ThreadState* const state)
    {
        assert(state && state->has_main_greenlet());

        // NOTE: Because we're not holding the GIL here, some other
        // Python thread could run and call ``os.fork()``, which would
        // be bad if that happened while we are holding the cleanup
        // lock (it wouldn't function in the child process).
        // Make a best effort to try to keep the duration we hold the
        // lock short.
        // TODO: On platforms that support it, use ``pthread_atfork`` to
        // drop this lock.
        LockGuard cleanup_lock(*mod_globs->thread_states_to_destroy_lock);

        mod_globs->queue_to_destroy(state);
        if (mod_globs->thread_states_to_destroy.size() == 1) {
            // We added the first item to the queue. We need to schedule
            // the cleanup.

            // A size greater than 1 means that we have already added the pending call,
            // and in fact, it may be executing now.
            // If it is executing, our lock makes sure that it will see the item we just added
            // to the queue on its next iteration (after we release the lock)
            //
            // A size of 1 means there is no pending call, OR the pending call is
            // currently executing, has dropped the lock, and is deleting the last item
            // from the queue; its next iteration will go ahead and delete the item we just added.
            // And the pending call we schedule here will have no work to do.
            int result = AddPendingCall(
                           PendingCallback_DestroyQueue,
                            nullptr);
            if (result < 0) {
                // Hmm, what can we do here?
                fprintf(stderr,
                        "greenlet: WARNING: failed in call to Py_AddPendingCall; "
                        "expect a memory leak.\n");
            }
        }
    }

    static int
    PendingCallback_DestroyQueue(void* UNUSED(arg))
    {
        // We're may or may not be holding the GIL here (depending on
        // Py_GIL_DISABLED), so calls to ``os.fork()`` may or may not
        // be possible.
        while (1) {
            ThreadState* to_destroy;
            {
                LockGuard cleanup_lock(*mod_globs->thread_states_to_destroy_lock);
                if (mod_globs->thread_states_to_destroy.empty()) {
                    break;
                }
                to_destroy = mod_globs->take_next_to_destroy();
            }
            assert(to_destroy);
            assert(to_destroy->has_main_greenlet());
            // Drop the lock while we do the actual deletion.
            // This allows other calls to MarkGreenletDeadAndQueueCleanup
            // to enter and add to our queue.
            DestroyOne(to_destroy);
        }
        return 0;
    }

    static void
    DestroyOne(const ThreadState* const state)
    {
        // May or may not be holding the GIL (depending on Py_GIL_DISABLED).
        // Passed a non-shared pointer to the actual thread state.
        // state -> main greenlet
        assert(state->has_main_greenlet());
        PyGreenlet* main(state->borrow_main_greenlet());
        // When we need to do cross-thread operations, we check this.
        // A NULL value means the thread died some time ago.
        // We do this here, rather than in a Python dealloc function
        // for the greenlet, in case there's still a reference out
        // there.
        dynamic_cast<MainGreenlet*>(main->pimpl)->thread_state(nullptr);

        delete state; // Deleting this runs the destructor, DECREFs the main greenlet.
    }


    static int AddPendingCall(int (*func)(void*), void* arg)
    {
        // If the interpreter is in the middle of finalizing, we can't add a
        // pending call. Trying to do so will end up in a SIGSEGV, as
        // Py_AddPendingCall will not be able to get the interpreter and will
        // try to dereference a NULL pointer. It's possible this can still
        // segfault if we happen to get context switched, and maybe we should
        // just always implement our own AddPendingCall, but I'd like to see if
        // this works first
#if GREENLET_PY313
        if (Py_IsFinalizing()) {
#else
        if (_Py_IsFinalizing()) {
#endif
#ifdef GREENLET_DEBUG
            // No need to log in the general case. Yes, we'll leak,
            // but we're shutting down so it should be ok.
            fprintf(stderr,
                    "greenlet: WARNING: Interpreter is finalizing. Ignoring "
                    "call to Py_AddPendingCall; \n");
#endif
            return 0;
        }
        return Py_AddPendingCall(func, arg);
    }





};
};

}; // namespace greenlet

// The intent when GET_THREAD_STATE() is needed multiple times in a
// function is to take a reference to its return value in a local
// variable, to avoid the thread-local indirection. On some platforms
// (macOS), accessing a thread-local involves a function call (plus an
// initial function call in each function that uses a thread local);
// in contrast, static volatile variables are at some pre-computed
// offset.
typedef greenlet::ThreadStateCreator<greenlet::ThreadState_DestroyNoGIL::MarkGreenletDeadAndQueueCleanup> ThreadStateCreator;
static thread_local ThreadStateCreator g_thread_state_global;
#define GET_THREAD_STATE() g_thread_state_global

#endif //T_THREADSTATE_DESTROY
