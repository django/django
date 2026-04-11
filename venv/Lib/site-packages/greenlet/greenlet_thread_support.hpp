#ifndef GREENLET_THREAD_SUPPORT_HPP
#define GREENLET_THREAD_SUPPORT_HPP

/**
 * Defines various utility functions to help greenlet integrate well
 * with threads. This used to be needed when we supported Python
 * 2.7 on Windows, which used a very old compiler. We wrote an
 * alternative implementation using Python APIs and POSIX or Windows
 * APIs, but that's no longer needed. So this file is a shadow of its
 * former self --- but may be needed in the future.
 */

#include <stdexcept>
#include <thread>
#include <mutex>

#include "greenlet_compiler_compat.hpp"

namespace greenlet {
    typedef std::mutex Mutex;
    typedef std::lock_guard<Mutex> LockGuard;
    class LockInitError : public std::runtime_error
    {
    public:
        LockInitError(const char* what) : std::runtime_error(what)
        {};
    };
};


#endif /* GREENLET_THREAD_SUPPORT_HPP */
