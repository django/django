#ifndef GREENLET_EXCEPTION_STATE_CPP
#define GREENLET_EXCEPTION_STATE_CPP

#include <Python.h>
#include "TGreenlet.hpp"

namespace greenlet {


ExceptionState::ExceptionState()
{
    this->clear();
}

void ExceptionState::operator<<(const PyThreadState *const tstate) noexcept
{
    this->exc_info = tstate->exc_info;
    this->exc_state = tstate->exc_state;
}

void ExceptionState::operator>>(PyThreadState *const tstate) noexcept
{
    tstate->exc_state = this->exc_state;
    tstate->exc_info =
        this->exc_info ? this->exc_info : &tstate->exc_state;
    this->clear();
}

void ExceptionState::clear() noexcept
{
    this->exc_info = nullptr;
    this->exc_state.exc_value = nullptr;
#if !GREENLET_PY311
    this->exc_state.exc_type = nullptr;
    this->exc_state.exc_traceback = nullptr;
#endif
    this->exc_state.previous_item = nullptr;
}

int ExceptionState::tp_traverse(visitproc visit, void* arg) noexcept
{
    Py_VISIT(this->exc_state.exc_value);
#if !GREENLET_PY311
    Py_VISIT(this->exc_state.exc_type);
    Py_VISIT(this->exc_state.exc_traceback);
#endif
    return 0;
}

void ExceptionState::tp_clear() noexcept
{
    Py_CLEAR(this->exc_state.exc_value);
#if !GREENLET_PY311
    Py_CLEAR(this->exc_state.exc_type);
    Py_CLEAR(this->exc_state.exc_traceback);
#endif
}


}; // namespace greenlet

#endif // GREENLET_EXCEPTION_STATE_CPP
