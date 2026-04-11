#ifndef GREENLET_ALLOCATOR_HPP
#define GREENLET_ALLOCATOR_HPP

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <memory>
#include "greenlet_compiler_compat.hpp"
#include "greenlet_cpython_compat.hpp"


namespace greenlet
{
    // This allocator is stateless; all instances are identical.
    // It can *ONLY* be used when we're sure we're holding the GIL
    // (Python's allocators require the GIL).
    template <class T>
    struct PythonAllocator : public std::allocator<T> {

        PythonAllocator(const PythonAllocator& UNUSED(other))
            : std::allocator<T>()
        {
        }

        PythonAllocator(const std::allocator<T> other)
            : std::allocator<T>(other)
        {}

        template <class U>
        PythonAllocator(const std::allocator<U>& other)
            : std::allocator<T>(other)
        {
        }

        PythonAllocator() : std::allocator<T>() {}

        T* allocate(size_t number_objects, const void* UNUSED(hint)=0)
        {
            void* p;
            if (number_objects == 1) {
#ifdef Py_GIL_DISABLED
                p = PyMem_Malloc(sizeof(T) * number_objects);
#else
                p = PyObject_Malloc(sizeof(T));
#endif
            }
            else {
                p = PyMem_Malloc(sizeof(T) * number_objects);
            }
            return static_cast<T*>(p);
        }

        void deallocate(T* t, size_t n)
        {
            void* p = t;
            if (n == 1) {
#ifdef Py_GIL_DISABLED
                PyMem_Free(p);
#else
                PyObject_Free(p);
#endif
            }
            else {
                PyMem_Free(p);
            }
        }
        // This member is deprecated in C++17 and removed in C++20
        template< class U >
        struct rebind {
            typedef PythonAllocator<U> other;
        };

    };

}

#endif
