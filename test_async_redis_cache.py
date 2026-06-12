#!/usr/bin/env python
"""Test async Redis cache methods."""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')

import django
django.setup()

from django.core.cache import caches
from django.test.utils import override_settings


async def test_async_redis_methods():
    """Test that async Redis methods use redis-py's async client."""

    # Configure to use Redis cache
    with override_settings(
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                'LOCATION': 'redis://127.0.0.1:6379/1',
            }
        }
    ):
        cache = caches['default']

        print("\n========== Testing Async Redis Cache Methods ==========\n")

        try:
            # Test aset and aget
            print("1. Testing aset and aget...")
            await cache.aset('test_key', 'test_value', timeout=10)
            value = await cache.aget('test_key')
            assert value == 'test_value', f"Expected 'test_value', got {value}"
            print("   ✓ aset/aget works correctly")

            # Test aadd
            print("2. Testing aadd...")
            result = await cache.aadd('new_key', 'new_value', timeout=10)
            assert result is True, f"Expected True, got {result}"
            result = await cache.aadd('new_key', 'another_value')  # Should fail
            assert result is False, f"Expected False on duplicate add, got {result}"
            print("   ✓ aadd works correctly")

            # Test ahas_key
            print("3. Testing ahas_key...")
            has_key = await cache.ahas_key('test_key')
            assert has_key is True, f"Expected True, got {has_key}"
            has_key = await cache.ahas_key('nonexistent')
            assert has_key is False, f"Expected False, got {has_key}"
            print("   ✓ ahas_key works correctly")

            # Test aset_many and aget_many
            print("4. Testing aset_many and aget_many...")
            await cache.aset_many({'key1': 'val1', 'key2': 'val2'}, timeout=10)
            values = await cache.aget_many(['key1', 'key2'])
            assert values == {'key1': 'val1', 'key2': 'val2'}, f"Got {values}"
            print("   ✓ aset_many/aget_many works correctly")

            # Test aincr
            print("5. Testing aincr...")
            await cache.aset('counter', 1, timeout=10)
            new_val = await cache.aincr('counter')
            assert new_val == 2, f"Expected 2, got {new_val}"
            print("   ✓ aincr works correctly")

            # Test atouch
            print("6. Testing atouch...")
            result = await cache.atouch('test_key', timeout=20)
            assert result is True, f"Expected True, got {result}"
            print("   ✓ atouch works correctly")

            # Test adelete
            print("7. Testing adelete...")
            await cache.aset('temp_key', 'temp_value')
            result = await cache.adelete('temp_key')
            assert result is True, f"Expected True, got {result}"
            result = await cache.adelete('temp_key')  # Already deleted
            assert result is False, f"Expected False, got {result}"
            print("   ✓ adelete works correctly")

            # Test adelete_many
            print("8. Testing adelete_many...")
            await cache.aset_many({'dk1': 'dv1', 'dk2': 'dv2'})
            await cache.adelete_many(['dk1', 'dk2'])
            has_k1 = await cache.ahas_key('dk1')
            assert has_k1 is False, f"Expected False after delete_many, got {has_k1}"
            print("   ✓ adelete_many works correctly")

            # Clean up
            print("9. Testing aclear...")
            await cache.aclear()
            has_any = await cache.ahas_key('test_key')
            assert has_any is False, f"Expected empty cache, but test_key still exists"
            print("   ✓ aclear works correctly")

            print("\n========== All Tests Passed! ==========\n")
            return True

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}\n")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run the async tests."""
    try:
        success = await test_async_redis_methods()
        return 0 if success else 1
    except ConnectionRefusedError:
        print("\n❌ Redis server is not running on localhost:6379\n")
        print("To run this test, start a Redis server:")
        print("  redis-server")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
