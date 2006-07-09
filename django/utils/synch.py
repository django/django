"""
Synchronization primitives:
    
    - reader-writer lock (preference to writers)

(Contributed to Django by eugene@lazutkin.com)
"""

try:
    import threading
except ImportError:
    import dummy_threading as threading

class RWLock:
    """
    Classic implementation of reader-writer lock with preference to writers.
    
    Readers can access a resource simultaneously.
    Writers get an exclusive access.
    
    API is self-descriptive:
        reader_enters()
        reader_leaves()
        writer_enters()
        writer_leaves()
    """
    
    def __init__(self):
        self.mutex     = threading.RLock()
        self.can_read  = threading.Semaphore(0)
        self.can_write = threading.Semaphore(0)
        self.active_readers  = 0
        self.active_writers  = 0
        self.waiting_readers = 0
        self.waiting_writers = 0
        
    def reader_enters(self):
        self.mutex.acquire()
        try:
            if self.active_writers == 0 and self.waiting_writers == 0:
                self.active_readers += 1
                self.can_read.release()
            else:
                self.waiting_readers += 1
        finally:
            self.mutex.release()
        self.can_read.acquire()
        
    def reader_leaves(self):
        self.mutex.acquire()
        try:
            self.active_readers -= 1
            if self.active_readers == 0 and self.waiting_writers != 0:
                self.active_writers  += 1
                self.waiting_writers -= 1
                self.can_write.release()
        finally:
            self.mutex.release()
    
    def writer_enters(self):
        self.mutex.acquire()
        try:
            if self.active_writers == 0 and self.waiting_writers == 0 and self.active_readers == 0:
                self.active_writers += 1
                self.can_write.release()
            else:
                self.waiting_writers += 1
        finally:
            self.mutex.release()
        self.can_write.acquire()
        
    def writer_leaves(self):
        self.mutex.acquire()
        try:
            self.active_writers -= 1
            if self.waiting_writers != 0:
                self.active_writers  += 1
                self.waiting_writers -= 1
                self.can_write.release()
            elif self.waiting_readers != 0:
                t = self.waiting_readers
                self.waiting_readers = 0
                self.active_readers += t
                while t > 0:
                    self.can_read.release()
                    t -= 1
        finally:
            self.mutex.release()
