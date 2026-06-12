#!/usr/bin/env python
"""Test backward compatibility of sync methods."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from django.core.cache.backends.redis import RedisCacheClient, RedisCache


def test_sync_compatibility():
    """Verify all sync methods still work correctly."""

    print("\n========== Testing Sync Method Compatibility ==========\n")

    try:
        # Create client
        client = RedisCacheClient(['redis://localhost:6379/1'])

        # Test 1: Verify all sync methods exist
        print("Test 1: Verify sync methods exist")
        sync_methods = [
            'add', 'get', 'set', 'touch', 'delete',
            'get_many', 'has_key', 'incr', 'set_many',
            'delete_many', 'clear'
        ]

        for method_name in sync_methods:
            if not hasattr(client, method_name):
                print(f"  ❌ Missing sync method: {method_name}")
                return False
            print(f"  ✓ {method_name}")

        # Test 2: Verify RedisCache has sync methods
        print("\nTest 2: Verify RedisCache sync methods")
        cache = RedisCache('redis://localhost:6379/1', {})

        for method_name in sync_methods:
            if not hasattr(cache, method_name):
                print(f"  ❌ Missing sync method: {method_name}")
                return False
            print(f"  ✓ {method_name}")

        # Test 3: Verify key validation and conversion
        print("\nTest 3: Verify key validation and conversion")
        test_key = cache.make_and_validate_key('test', version=1)
        print(f"  ✓ make_and_validate_key works: {test_key}")

        timeout = cache.get_backend_timeout(60)
        print(f"  ✓ get_backend_timeout works: {timeout}")

        # Test 4: Verify serializer
        print("\nTest 4: Verify serializer")
        test_data = {'test': 'data', 'number': 42}
        serialized = client._serializer.dumps(test_data)
        deserialized = client._serializer.loads(serialized)
        assert deserialized == test_data
        print(f"  ✓ Serialization works correctly")

        # Test 5: Verify connection management
        print("\nTest 5: Verify connection management")
        sync_client = client.get_client()
        print(f"  ✓ get_client() works: {type(sync_client)}")

        print("\n========== All Sync Compatibility Tests Passed! ==========\n")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_sync_compatibility()
    sys.exit(0 if success else 1)
