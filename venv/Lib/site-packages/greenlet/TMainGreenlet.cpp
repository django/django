/* -*- indent-tabs-mode: nil; tab-width: 4; -*- */
/**
 * Implementation of greenlet::MainGreenlet.
 *
 * Format with:
 *  clang-format -i --style=file src/greenlet/greenlet.c
 *
 *
 * Fix missing braces with:
 *   clang-tidy src/greenlet/greenlet.c -fix -checks="readability-braces-around-statements"
*/
#ifndef T_MAIN_GREENLET_CPP
#define T_MAIN_GREENLET_CPP

#include "TGreenlet.hpp"

#ifdef Py_GIL_DISABLED
#include <atomic>
#endif

// Incremented when we create a main greenlet, in a new thread, decremented
// when it is destroyed.
#ifdef Py_GIL_DISABLED
static std::atomic<Py_ssize_t> G_TOTAL_MAIN_GREENLETS(0);
#else
// Protected by the GIL.
static Py_ssize_t G_TOTAL_MAIN_GREENLETS;
#endif

namespace greenlet {
greenlet::PythonAllocator<MainGreenlet> MainGreenlet::allocator;

void* MainGreenlet::operator new(size_t UNUSED(count))
{
    return allocator.allocate(1);
}


void MainGreenlet::operator delete(void* ptr)
{
    return allocator.deallocate(static_cast<MainGreenlet*>(ptr),
                                1);
}


MainGreenlet::MainGreenlet(PyGreenlet* p, ThreadState* state)
    : Greenlet(p, StackState::make_main()),
      _self(p),
      _thread_state(state)
{
    G_TOTAL_MAIN_GREENLETS++;
}

MainGreenlet::~MainGreenlet()
{
    G_TOTAL_MAIN_GREENLETS--;
    this->tp_clear();
}

ThreadState*
MainGreenlet::thread_state() const noexcept
{
    return this->_thread_state;
}

void
MainGreenlet::thread_state(ThreadState* t) noexcept
{
    assert(!t);
    this->_thread_state = t;
}


const BorrowedMainGreenlet
MainGreenlet::main_greenlet() const
{
    return this->_self;
}

BorrowedMainGreenlet
MainGreenlet::find_main_greenlet_in_lineage() const
{
    return BorrowedMainGreenlet(this->_self);
}

bool
MainGreenlet::was_running_in_dead_thread() const noexcept
{
    return !this->_thread_state;
}

OwnedObject
MainGreenlet::g_switch()
{
    try {
        this->check_switch_allowed();
    }
    catch (const PyErrOccurred&) {
        this->release_args();
        throw;
    }

    switchstack_result_t err = this->g_switchstack();
    if (err.status < 0) {
        // XXX: This code path is untested, but it is shared
        // with the UserGreenlet path that is tested.
        return this->on_switchstack_or_initialstub_failure(
            this,
            err,
            true, // target was me
            false // was initial stub
        );
    }

    return err.the_new_current_greenlet->g_switch_finish(err);
}

int
MainGreenlet::tp_traverse(visitproc visit, void* arg)
{
    if (this->_thread_state) {
        // we've already traversed main, (self), don't do it again.
        int result = this->_thread_state->tp_traverse(visit, arg, false);
        if (result) {
            return result;
        }
    }
    return Greenlet::tp_traverse(visit, arg);
}

const OwnedObject&
MainGreenlet::run() const
{
    throw AttributeError("Main greenlets do not have a run attribute.");
}

void
MainGreenlet::run(const BorrowedObject UNUSED(nrun))
{
   throw AttributeError("Main greenlets do not have a run attribute.");
}

void
MainGreenlet::parent(const BorrowedObject raw_new_parent)
{
    if (!raw_new_parent) {
        throw AttributeError("can't delete attribute");
    }
    throw AttributeError("cannot set the parent of a main greenlet");
}

const OwnedGreenlet
MainGreenlet::parent() const
{
    return OwnedGreenlet(); // null becomes None
}

}; // namespace greenlet

#endif
