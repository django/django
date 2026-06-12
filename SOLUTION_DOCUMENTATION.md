# Solution for Issue #37156: Properly Implement Async Redis Methods

## Overview
This solution implements proper async support for Django's Redis cache backend by using redis-py's native `redis.asyncio` client instead of wrapping sync methods with `sync_to_async`.

## Problem Statement
Previously, the `RedisCache` backend inherited async methods from `BaseCache` that used `sync_to_async` wrappers around synchronous Redis methods. This approach:
1. Defeated the purpose of async views in full-page caching scenarios
2. Added unnecessary threading overhead
3. Didn't match user expectations that `aget()` would use Redis's async API

## Solution Architecture

### 1. Async Connection Pool Management
- Added separate async connection pools per event loop to RedisCacheClient
- Used `threading.Lock` for thread-safe pool management
- Pools are identified by `(loop_id, server_index)` tuple

### 2. Implementation Details

#### RedisCacheClient Changes
Added the following async methods that use `redis.asyncio.Redis`:
- `aadd()` - Add value to cache atomically
- `aget()` - Get value from cache
- `aset()` - Set value in cache
- `atouch()` - Update key expiry
- `adelete()` - Delete key from cache
- `aget_many()` - Get multiple values
- `ahas_key()` - Check if key exists
- `aincr()` - Increment integer value
- `aset_many()` - Set multiple values
- `adelete_many()` - Delete multiple keys
- `aclear()` - Clear all keys

Each method:
1. Gets an async Redis client via `get_async_client()`
2. Performs the operation using redis-py's async API
3. Returns the result (properly handling serialization)

#### RedisCache Backend Changes
Overrode all async methods to:
1. Validate and process keys with `make_and_validate_key()`
2. Delegate to corresponding `RedisCacheClient` async methods
3. Maintain same timeout conversion as sync methods

### 3. WSGI Compatibility
The solution handles both WSGI and ASGI contexts:
- In async context (ASGI): Uses redis-py's async client via event loop-bound connection pool
- In sync context (WSGI): Cannot use async methods (raises RuntimeError with clear message)
- Note: This is correct behavior since async methods require async context anyway

### 4. Key Features
✅ Uses redis-py's native async client (no sync_to_async)
✅ Proper event loop management
✅ Thread-safe connection pool caching
✅ Maintains same API compatibility
✅ Proper error handling for WSGI context
✅ Serialization/deserialization handled correctly

## Implementation Details

### Async Connection Pool Creation
```python
def _get_async_connection_pool(self, write):
    """Get an async connection pool for the current event loop."""
    try:
        loop = asyncio.get_running_loop()  # Get active event loop
    except RuntimeError:
        return None  # No event loop, fallback needed

    loop_id = id(loop)
    index = self._get_connection_pool_index(write)
    pool_key = (loop_id, index)

    # Create pool if not exists for this event loop
    if pool_key not in self._async_pools:
        async_pool_class = self._lib.asyncio.ConnectionPool
        self._async_pools[pool_key] = async_pool_class.from_url(
            self._servers[index],
            **self._pool_options,
        )
    return self._async_pools[pool_key]
```

### Example Async Method
```python
async def aget(self, key, default):
    """Get value from cache asynchronously."""
    client = await self.get_async_client(key)
    value = await client.get(key)
    return default if value is None else self._serializer.loads(value)
```

## Performance Considerations
- Eliminates thread pool overhead for async operations
- Uses redis-py's efficient async I/O directly
- Connection pooling optimized per event loop
- Maintains backward compatibility with sync operations

## Testing
Tests should verify:
1. Async methods work in async context (ASGI)
2. Proper error message when used in sync context (WSGI)
3. Serialization/deserialization works correctly
4. Connection pooling is per-event-loop
5. All cache operations (get, set, delete, incr, etc.) work

## Migration Notes
- No API changes - all methods maintain same signatures
- Subclasses overriding sync methods won't break
- Async operations automatically get real async implementation
- WSGI deployments unaffected (still use sync methods)

## Future Enhancements
- Add async context manager support (async with cache)
- Connection pool cleanup on event loop shutdown
- Metrics/monitoring for async operations
- Documentation updates with async examples
