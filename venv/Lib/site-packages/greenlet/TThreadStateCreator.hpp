#ifndef GREENLET_THREAD_STATE_CREATOR_HPP
#define GREENLET_THREAD_STATE_CREATOR_HPP

#include <ctime>
#include <stdexcept>

#include "greenlet_internal.hpp"
#include "greenlet_refs.hpp"
#include "greenlet_thread_support.hpp"

#include "TThreadState.hpp"

namespace greenlet {


typedef void (*ThreadStateDestructor)(ThreadState* const);

// Only one of these, auto created per thread as a thread_local.
// Constructing the state constructs the MainGreenlet.
template<ThreadStateDestructor Destructor>
class ThreadStateCreator
{
private:
    // Initialized to 1, and, if still 1, created on access.
    // Set to 0 on destruction.
    ThreadState* _state;
    G_NO_COPIES_OF_CLS(ThreadStateCreator);

    inline bool has_initialized_state() const noexcept
    {
        return this->_state != (ThreadState*)1;
    }

    inline bool has_state() const noexcept
    {
        return this->has_initialized_state() && this->_state != nullptr;
    }

public:

    ThreadStateCreator() :
        _state((ThreadState*)1)
    {
    }

    ~ThreadStateCreator()
    {
        if (this->has_state()) {
            Destructor(this->_state);
        }

        this->_state = nullptr;
    }

    inline ThreadState& state()
    {
        // The main greenlet will own this pointer when it is created,
        // which will be right after this. The plan is to give every
        // greenlet a pointer to the main greenlet for the thread it
        // runs in; if we are doing something cross-thread, we need to
        // access the pointer from the main greenlet. Deleting the
        // thread, and hence the thread-local storage, will delete the
        // state pointer in the main greenlet.
        if (!this->has_initialized_state()) {
            // XXX: Assuming allocation never fails
            this->_state = new ThreadState;
            // For non-standard threading, we need to store an object
            // in the Python thread state dictionary so that it can be
            // DECREF'd when the thread ends (ideally; the dict could
            // last longer) and clean this object up.
        }
        if (!this->_state) {
            throw std::runtime_error("Accessing state after destruction.");
        }
        return *this->_state;
    }

    operator ThreadState&()
    {
        return this->state();
    }

    operator ThreadState*()
    {
        return &this->state();
    }

    inline int tp_traverse(visitproc visit, void* arg)
    {
        if (this->has_state()) {
            return this->_state->tp_traverse(visit, arg);
        }
        return 0;
    }

};



}; // namespace greenlet

#endif
