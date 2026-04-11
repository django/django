# Copyright 2012 Pinterest.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A client for falling back to older memcached servers when performing reads.

It is sometimes necessary to deploy memcached on new servers, or with a
different configuration. In these cases, it is undesirable to start up an
empty memcached server and point traffic to it, since the cache will be cold,
and the backing store will have a large increase in traffic.

This class attempts to solve that problem by providing an interface identical
to the Client interface, but which can fall back to older memcached servers
when reads to the primary server fail. The approach for upgrading memcached
servers or configuration then becomes:

 1. Deploy a new host (or fleet) with memcached, possibly with a new
    configuration.
 2. From your application servers, use FallbackClient to write and read from
    the new cluster, and to read from the old cluster when there is a miss in
    the new cluster.
 3. Wait until the new cache is warm enough to support the load.
 4. Switch from FallbackClient to a regular Client library for doing all
    reads and writes to the new cluster.
 5. Take down the old cluster.

Best Practices:
---------------
 - Make sure that the old client has "ignore_exc" set to True, so that it
   treats failures like cache misses. That will allow you to take down the
   old cluster before you switch away from FallbackClient.
"""


class FallbackClient:
    def __init__(self, caches):
        assert len(caches) > 0
        self.caches = caches

    def close(self):
        "Close each of the memcached clients"
        for cache in self.caches:
            cache.close()

    def set(self, key, value, expire=0, noreply=True):
        self.caches[0].set(key, value, expire, noreply)

    def add(self, key, value, expire=0, noreply=True):
        self.caches[0].add(key, value, expire, noreply)

    def replace(self, key, value, expire=0, noreply=True):
        self.caches[0].replace(key, value, expire, noreply)

    def append(self, key, value, expire=0, noreply=True):
        self.caches[0].append(key, value, expire, noreply)

    def prepend(self, key, value, expire=0, noreply=True):
        self.caches[0].prepend(key, value, expire, noreply)

    def cas(self, key, value, cas, expire=0, noreply=True):
        self.caches[0].cas(key, value, cas, expire, noreply)

    def get(self, key):
        for cache in self.caches:
            result = cache.get(key)
            if result is not None:
                return result
        return None

    def get_many(self, keys):
        for cache in self.caches:
            result = cache.get_many(keys)
            if result:
                return result
        return []

    def gets(self, key):
        for cache in self.caches:
            result = cache.gets(key)
            if result is not None:
                return result
        return None

    def gets_many(self, keys):
        for cache in self.caches:
            result = cache.gets_many(keys)
            if result:
                return result
        return []

    def delete(self, key, noreply=True):
        self.caches[0].delete(key, noreply)

    def incr(self, key, value, noreply=True):
        self.caches[0].incr(key, value, noreply)

    def decr(self, key, value, noreply=True):
        self.caches[0].decr(key, value, noreply)

    def touch(self, key, expire=0, noreply=True):
        self.caches[0].touch(key, expire, noreply)

    def stats(self):
        # TODO: ??
        pass

    def flush_all(self, delay=0, noreply=True):
        self.caches[0].flush_all(delay, noreply)

    def quit(self):
        # TODO: ??
        pass
