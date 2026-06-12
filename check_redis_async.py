#!/usr/bin/env python
import redis
import redis.asyncio
import inspect

print("Redis version:", redis.__version__)
print("\nAsyncio module attributes:")
print([m for m in dir(redis.asyncio) if not m.startswith('_')])

print("\n\nChecking Redis async client:")
print("Redis async client class:", redis.asyncio.Redis)

# Check if there's an async connection pool
print("\nAsync ConnectionPool:", hasattr(redis.asyncio, 'ConnectionPool'))
print("Async BlockingConnectionPool:", hasattr(redis.asyncio, 'BlockingConnectionPool'))

# Check method signatures
print("\n\nAsync Redis methods (sample):")
for method in ['get', 'set', 'delete', 'mget', 'mset', 'exists', 'expire', 'persist', 'incr']:
    if hasattr(redis.asyncio.Redis, method):
        m = getattr(redis.asyncio.Redis, method)
        print(f"  {method}: coroutine={inspect.iscoroutinefunction(m)}")

# Check from_url
print("\nfrom_url available:", hasattr(redis.asyncio, 'from_url'))

# Check AsyncConnectionPool
if hasattr(redis.asyncio, 'ConnectionPool'):
    print("AsyncConnectionPool from_url:", hasattr(redis.asyncio.ConnectionPool, 'from_url'))
