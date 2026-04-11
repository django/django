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

#include "TGreenlet.hpp"

namespace greenlet {

void* BrokenGreenlet::operator new(size_t UNUSED(count))
{
    return allocator.allocate(1);
}


void BrokenGreenlet::operator delete(void* ptr)
{
    return allocator.deallocate(static_cast<BrokenGreenlet*>(ptr),
                                1);
}

greenlet::PythonAllocator<greenlet::BrokenGreenlet> greenlet::BrokenGreenlet::allocator;

bool
BrokenGreenlet::force_slp_switch_error() const noexcept
{
    return this->_force_slp_switch_error;
}

UserGreenlet::switchstack_result_t BrokenGreenlet::g_switchstack(void)
{
  if (this->_force_switch_error) {
    return switchstack_result_t(-1);
  }
  return UserGreenlet::g_switchstack();
}

}; //namespace greenlet
