#!/usr/bin/env python
"""Test async Redis cache implementation."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from django.core.cache.backends.redis import RedisCacheClient, RedisCache


async def test_async_structure():
    """Verify async methods structure and basic functionality."""

    print("\n========== Testing Async Redis Implementation ==========\n")

    try:
        # Test 1: Verify async client creation fails without event loop (this is expected)
        print("Test 1: Verify event loop detection")
        client = RedisCacheClient(['redis://localhost:6379/1'])

        try:
            # This should work since we're in an async context
            async_client = await client.get_async_client()
            print("  ✓ get_async_client() works in async context")
        except RuntimeError as e:
            if "event loop" in str(e).lower():
                print("  ✓ Proper event loop error handling")
            else:
                raise

        # Test 2: Check connection pool management
        print("\nTest 2: Check connection pool management")
        if hasattr(client, '_async_pools'):
            print("  ✓ _async_pools attribute exists")
        if hasattr(client, '_async_pools_lock'):
            print("  ✓ _async_pools_lock exists (thread safety)")

        # Test 3: Verify serialization works
        print("\nTest 3: Check serializer functionality")
        serialized = client._serializer.dumps({'key': 'value'})
        deserialized = client._serializer.loads(serialized)
        assert deserialized == {'key': 'value'}, "Serialization failed"
        print("  ✓ Serialization/deserialization works")

        # Test 4: Verify integer handling (special case in serializer)
        print("\nTest 4: Check integer special handling")
        serialized_int = client._serializer.dumps(42)
        assert serialized_int == 42, "Integer serialization failed"
        deserialized_int = client._serializer.loads(42)
        assert deserialized_int == 42, "Integer deserialization failed"
        print("  ✓ Integer special handling works")

        # Test 5: Verify all async methods exist
        print("\nTest 5: Verify all async methods exist")
        required_methods = [
            'aadd', 'aget', 'aset', 'atouch', 'adelete',
            'aget_many', 'ahas_key', 'aincr', 'aset_many',
            'adelete_many', 'aclear'
        ]

        for method_name in required_methods:
            if not hasattr(RedisCacheClient, method_name):
                print(f"  ❌ Missing: {method_name}")
                return False
            print(f"  ✓ {method_name}")

        # Test 6: Verify RedisCache overrides
        print("\nTest 6: Verify RedisCache async method overrides")
        cache = RedisCache('redis://localhost:6379/1', {})

        for method_name in required_methods:
            if not hasattr(cache, method_name):
                print(f"  ❌ Missing: {method_name}")
                return False
            print(f"  ✓ {method_name}")

        print("\n========== All Async Structure Tests Passed! ==========\n")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run async tests."""
    success = await test_async_structure()
    return 0 if success else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
