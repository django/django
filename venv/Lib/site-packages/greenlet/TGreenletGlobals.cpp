/* -*- indent-tabs-mode: nil; tab-width: 4; -*- */
/**
 * Implementation of GreenletGlobals.
 *
 * Format with:
 *  clang-format -i --style=file src/greenlet/greenlet.c
 *
 *
 * Fix missing braces with:
 *   clang-tidy src/greenlet/greenlet.c -fix -checks="readability-braces-around-statements"
*/
#ifndef T_GREENLET_GLOBALS
#define T_GREENLET_GLOBALS

#include "greenlet_refs.hpp"
#include "greenlet_exceptions.hpp"
#include "greenlet_thread_support.hpp"
#include "greenlet_internal.hpp"

namespace greenlet {

// This encapsulates what were previously module global "constants"
// established at init time.
// This is a step towards Python3 style module state that allows
// reloading.
//
// In an earlier iteration of this code, we used placement new to be
// able to allocate this object statically still, so that references
// to its members don't incur an extra pointer indirection.
// But under some scenarios, that could result in crashes at
// shutdown because apparently the destructor was getting run twice?
class GreenletGlobals
{

public:
    const greenlet::refs::ImmortalEventName event_switch;
    const greenlet::refs::ImmortalEventName event_throw;
    const greenlet::refs::ImmortalException PyExc_GreenletError;
    const greenlet::refs::ImmortalException PyExc_GreenletExit;
    const greenlet::refs::ImmortalObject empty_tuple;
    const greenlet::refs::ImmortalObject empty_dict;
    const greenlet::refs::ImmortalString str_run;
    Mutex* const thread_states_to_destroy_lock;
    greenlet::cleanup_queue_t thread_states_to_destroy;

    GreenletGlobals() :
        event_switch("switch"),
        event_throw("throw"),
        PyExc_GreenletError("greenlet.error"),
        PyExc_GreenletExit("greenlet.GreenletExit", PyExc_BaseException),
        empty_tuple(Require(PyTuple_New(0))),
        empty_dict(Require(PyDict_New())),
        str_run("run"),
        thread_states_to_destroy_lock(new Mutex())
    {}

    ~GreenletGlobals()
    {
        // This object is (currently) effectively immortal, and not
        // just because of those placement new tricks; if we try to
        // deallocate the static object we allocated, and overwrote,
        // we would be doing so at C++ teardown time, which is after
        // the final Python GIL is released, and we can't use the API
        // then.
        // (The members will still be destructed, but they also don't
        // do any deallocation.)
    }

    void queue_to_destroy(ThreadState* ts) const
    {
        // we're currently accessed through a static const object,
        // implicitly marking our members as const, so code can't just
        // call push_back (or pop_back) without casting away the
        // const.
        //
        // Do that for callers.
        greenlet::cleanup_queue_t& q = const_cast<greenlet::cleanup_queue_t&>(this->thread_states_to_destroy);
        q.push_back(ts);
    }

    ThreadState* take_next_to_destroy() const
    {
        greenlet::cleanup_queue_t& q = const_cast<greenlet::cleanup_queue_t&>(this->thread_states_to_destroy);
        ThreadState* result = q.back();
        q.pop_back();
        return result;
    }
};

}; // namespace greenlet

static const greenlet::GreenletGlobals* mod_globs;

#endif // T_GREENLET_GLOBALS
