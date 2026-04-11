#ifndef GREENLET_STACK_STATE_CPP
#define GREENLET_STACK_STATE_CPP

#include "TGreenlet.hpp"

namespace greenlet {

#ifdef GREENLET_USE_STDIO
#include <iostream>
using std::cerr;
using std::endl;

std::ostream& operator<<(std::ostream& os, const StackState& s)
{
    os << "StackState(stack_start=" << (void*)s._stack_start
       << ", stack_stop=" << (void*)s.stack_stop
       << ", stack_copy=" << (void*)s.stack_copy
       << ", stack_saved=" << s._stack_saved
       << ", stack_prev=" << s.stack_prev
       << ", addr=" << &s
       << ")";
    return os;
}
#endif

StackState::StackState(void* mark, StackState& current)
    : _stack_start(nullptr),
      stack_stop((char*)mark),
      stack_copy(nullptr),
      _stack_saved(0),
      /* Skip a dying greenlet */
      stack_prev(current._stack_start
                 ? &current
                 : current.stack_prev)
{
}

StackState::StackState()
    : _stack_start(nullptr),
      stack_stop(nullptr),
      stack_copy(nullptr),
      _stack_saved(0),
      stack_prev(nullptr)
{
}

StackState::StackState(const StackState& other)
// can't use a delegating constructor because of
// MSVC for Python 2.7
    : _stack_start(nullptr),
      stack_stop(nullptr),
      stack_copy(nullptr),
      _stack_saved(0),
      stack_prev(nullptr)
{
    this->operator=(other);
}

StackState& StackState::operator=(const StackState& other)
{
    if (&other == this) {
        return *this;
    }
    if (other._stack_saved) {
        throw std::runtime_error("Refusing to steal memory.");
    }

    //If we have memory allocated, dispose of it
    this->free_stack_copy();

    this->_stack_start = other._stack_start;
    this->stack_stop = other.stack_stop;
    this->stack_copy = other.stack_copy;
    this->_stack_saved = other._stack_saved;
    this->stack_prev = other.stack_prev;
    return *this;
}

inline void StackState::free_stack_copy() noexcept
{
    PyMem_Free(this->stack_copy);
    this->stack_copy = nullptr;
    this->_stack_saved = 0;
}

inline void StackState::copy_heap_to_stack(const StackState& current) noexcept
{

    /* Restore the heap copy back into the C stack */
    if (this->_stack_saved != 0) {
        memcpy(this->_stack_start, this->stack_copy, this->_stack_saved);
        this->free_stack_copy();
    }
    StackState* owner = const_cast<StackState*>(&current);
    if (!owner->_stack_start) {
        owner = owner->stack_prev; /* greenlet is dying, skip it */
    }
    while (owner && owner->stack_stop <= this->stack_stop) {
        // cerr << "\tOwner: " << owner << endl;
        owner = owner->stack_prev; /* find greenlet with more stack */
    }
    this->stack_prev = owner;
    // cerr << "\tFinished with: " << *this << endl;
}

inline int StackState::copy_stack_to_heap_up_to(const char* const stop) noexcept
{
    /* Save more of g's stack into the heap -- at least up to 'stop'
       g->stack_stop |________|
                     |        |
                     |    __ stop       . . . . .
                     |        |    ==>  .       .
                     |________|          _______
                     |        |         |       |
                     |        |         |       |
      g->stack_start |        |         |_______| g->stack_copy
     */
    intptr_t sz1 = this->_stack_saved;
    intptr_t sz2 = stop - this->_stack_start;
    assert(this->_stack_start);
    if (sz2 > sz1) {
        char* c = (char*)PyMem_Realloc(this->stack_copy, sz2);
        if (!c) {
            PyErr_NoMemory();
            return -1;
        }
        memcpy(c + sz1, this->_stack_start + sz1, sz2 - sz1);
        this->stack_copy = c;
        this->_stack_saved = sz2;
    }
    return 0;
}

inline int StackState::copy_stack_to_heap(char* const stackref,
                                          const StackState& current) noexcept
{
    /* must free all the C stack up to target_stop */
    const char* const target_stop = this->stack_stop;

    StackState* owner = const_cast<StackState*>(&current);
    assert(owner->_stack_saved == 0); // everything is present on the stack
    if (!owner->_stack_start) {
        owner = owner->stack_prev; /* not saved if dying */
    }
    else {
        owner->_stack_start = stackref;
    }

    while (owner->stack_stop < target_stop) {
        /* ts_current is entierely within the area to free */
        if (owner->copy_stack_to_heap_up_to(owner->stack_stop)) {
            return -1; /* XXX */
        }
        owner = owner->stack_prev;
    }
    if (owner != this) {
        if (owner->copy_stack_to_heap_up_to(target_stop)) {
            return -1; /* XXX */
        }
    }
    return 0;
}

inline bool StackState::started() const noexcept
{
    return this->stack_stop != nullptr;
}

inline bool StackState::main() const noexcept
{
    return this->stack_stop == (char*)-1;
}

inline bool StackState::active() const noexcept
{
    return this->_stack_start != nullptr;
}

inline void StackState::set_active() noexcept
{
    assert(this->_stack_start == nullptr);
    this->_stack_start = (char*)1;
}

inline void StackState::set_inactive() noexcept
{
    this->_stack_start = nullptr;
    // XXX: What if we still have memory out there?
    // That case is actually triggered by
    // test_issue251_issue252_explicit_reference_not_collectable (greenlet.tests.test_leaks.TestLeaks)
    // and
    // test_issue251_issue252_need_to_collect_in_background
    // (greenlet.tests.test_leaks.TestLeaks)
    //
    // Those objects never get deallocated, so the destructor never
    // runs.
    // It *seems* safe to clean up the memory here?
    if (this->_stack_saved) {
        this->free_stack_copy();
    }
}

inline intptr_t StackState::stack_saved() const noexcept
{
    return this->_stack_saved;
}

inline char* StackState::stack_start() const noexcept
{
    return this->_stack_start;
}


inline StackState StackState::make_main() noexcept
{
    StackState s;
    s._stack_start = (char*)1;
    s.stack_stop = (char*)-1;
    return s;
}

StackState::~StackState()
{
    if (this->_stack_saved != 0) {
        this->free_stack_copy();
    }
}

void StackState::copy_from_stack(void* vdest, const void* vsrc, size_t n) const
{
    char* dest = static_cast<char*>(vdest);
    const char* src = static_cast<const char*>(vsrc);
    if (src + n <= this->_stack_start
        || src >= this->_stack_start + this->_stack_saved
        || this->_stack_saved == 0) {
        // Nothing we're copying was spilled from the stack
        memcpy(dest, src, n);
        return;
    }

    if (src < this->_stack_start) {
        // Copy the part before the saved stack.
        // We know src + n > _stack_start due to the test above.
        const size_t nbefore = this->_stack_start - src;
        memcpy(dest, src, nbefore);
        dest += nbefore;
        src += nbefore;
        n -= nbefore;
    }
    // We know src >= _stack_start after the before-copy, and
    // src < _stack_start + _stack_saved due to the first if condition
    size_t nspilled = std::min<size_t>(n, this->_stack_start + this->_stack_saved - src);
    memcpy(dest, this->stack_copy + (src - this->_stack_start), nspilled);
    dest += nspilled;
    src += nspilled;
    n -= nspilled;
    if (n > 0) {
        // Copy the part after the saved stack
        memcpy(dest, src, n);
    }
}

}; // namespace greenlet

#endif // GREENLET_STACK_STATE_CPP
