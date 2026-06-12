#!/usr/bin/env python
import redis.asyncio
import asyncio
import inspect

async def test_redis_async():
    # Create an async redis client
    redis_client = redis.asyncio.Redis()

    print("Redis client type:", type(redis_client))
    print("Redis get method:", redis_client.get)
    print("Is get a coroutine function?", inspect.iscoroutinefunction(redis_client.get))

    # Check the get method more carefully
    get_method = redis_client.get
    print("Get method callable?", callable(get_method))

    # Try calling it to see what happens
    result = redis_client.get("test_key")
    print("Result of get call:", result)
    print("Is result a coroutine?", inspect.iscoroutine(result))

    await redis_client.close()

if __name__ == "__main__":
    asyncio.run(test_redis_async())
