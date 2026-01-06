# Cache Backends Reference

This document details all Django cache backends, their configurations, and when to use each.

## Table of Contents

- [Redis](#redis)
- [Memcached](#memcached)
- [Database](#database)
- [File System](#file-system)
- [Local Memory](#local-memory)
- [Dummy Cache](#dummy-cache)
- [Multiple Cache Configuration](#multiple-cache-configuration)
- [Backend Comparison](#backend-comparison)

## Redis

### Overview

Redis is the recommended production cache backend. It's fast, supports persistence, and has advanced features like pattern-based deletion.

### Basic Configuration

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### Advanced Configuration with django-redis

```python
# Install: pip install django-redis redis

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': True,  # Don't break app if Redis is down
        },
        'KEY_PREFIX': 'myapp',
        'VERSION': 1,
        'TIMEOUT': 300,  # Default timeout in seconds
    }
}
```

### Redis Sentinel (High Availability)

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': [
            'redis://sentinel1:26379/1',
            'redis://sentinel2:26379/1',
            'redis://sentinel3:26379/1',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.SentinelClient',
            'SENTINELS': [
                ('sentinel1', 26379),
                ('sentinel2', 26379),
                ('sentinel3', 26379),
            ],
            'SENTINEL_KWARGS': {
                'socket_timeout': 0.5,
            },
            'CONNECTION_POOL_CLASS': 'redis.sentinel.SentinelConnectionPool',
            'CONNECTION_POOL_KWARGS': {
                'service_name': 'mymaster',
                'socket_connect_timeout': 5,
            },
        }
    }
}
```

### Redis Cluster

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': [
            'redis://node1:6379/0',
            'redis://node2:6379/0',
            'redis://node3:6379/0',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.ClusterClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
            }
        }
    }
}
```

### Redis with Authentication

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://username:password@127.0.0.1:6379/1',
        # Or using URL encoding for special characters
        # 'LOCATION': 'redis://:p%40ssw0rd@127.0.0.1:6379/1',
    }
}
```

### Unix Socket Connection

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'unix:///var/run/redis/redis.sock',
    }
}
```

## Memcached

### Overview

Memcached is extremely fast and simple, ideal for high-throughput caching. No persistence means data is lost on restart.

### Python-Memcached Backend

```python
# Install: pip install python-memcached

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}
```

### PyLibMC Backend (Faster)

```python
# Install: pip install pylibmc

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211',
        'OPTIONS': {
            'binary': True,
            'behaviors': {
                'tcp_nodelay': True,
                'ketama': True,
            }
        }
    }
}
```

### Multiple Memcached Servers

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': [
            '172.19.26.240:11211',
            '172.19.26.242:11211',
            'memcached.example.com:11211',
        ],
    }
}
```

### Unix Socket Connection

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'unix:/tmp/memcached.sock',
    }
}
```

## Database

### Overview

Uses Django's database for caching. Slower but requires no additional services. Good for shared hosting.

### Configuration

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'my_cache_table',
        'OPTIONS': {
            'MAX_ENTRIES': 1000,  # Maximum entries before culling
            'CULL_FREQUENCY': 3,  # 1/3 of entries culled when MAX_ENTRIES reached
        }
    }
}
```

### Setup

```bash
# Create cache table
python manage.py createcachetable
```

### Multiple Tables

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_default',
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_sessions',
    }
}
```

### Using Specific Database

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'my_cache_table',
        'OPTIONS': {
            'db_alias': 'cache_db',  # Use specific database connection
        }
    }
}
```

## File System

### Overview

Stores cached data as files on disk. Simple but not suitable for multi-server setups.

### Configuration

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/django_cache',
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}
```

### Best Practices

```python
import os
from pathlib import Path

# Use system temp directory
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(
            os.environ.get('TMPDIR', '/tmp'),
            'django_cache'
        ),
    }
}

# Or use project temp directory
BASE_DIR = Path(__file__).resolve().parent.parent
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / 'tmp' / 'cache',
    }
}
```

### Permissions

Ensure the directory is writable:

```bash
mkdir -p /var/tmp/django_cache
chmod 777 /var/tmp/django_cache
```

## Local Memory

### Overview

Stores cache in Python process memory. Very fast but not shared across processes/servers. Good for development.

### Configuration

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}
```

### Multiple Local Memory Caches

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'default-cache',
    },
    'secondary': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'secondary-cache',
    }
}
```

**Note:** `LOCATION` must be unique for each cache to prevent conflicts.

## Dummy Cache

### Overview

Doesn't actually cache anything. Used for testing or disabling cache in development.

### Configuration

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
```

### Conditional Dummy Cache

```python
# Disable cache in development
DEBUG = True

if DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
        }
    }
```

## Multiple Cache Configuration

### Different Caches for Different Purposes

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'TIMEOUT': 300,
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'TIMEOUT': 86400,  # 24 hours
    },
    'api': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/3',
        'TIMEOUT': 60,  # Short timeout for API data
    },
    'staticfiles': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'staticfiles-cache',
    }
}
```

### Using Multiple Caches

```python
from django.core.cache import caches

# Use specific cache
sessions_cache = caches['sessions']
sessions_cache.set('session_key', 'session_data', 3600)

api_cache = caches['api']
api_cache.set('api_response', data, 60)

# Default cache
from django.core.cache import cache
cache.set('key', 'value', 300)
```

## Backend Comparison

### Performance Comparison

| Backend | Read Speed | Write Speed | Memory Usage | Setup Complexity |
|---------|-----------|-------------|--------------|------------------|
| Redis | ★★★★★ | ★★★★★ | Medium | Medium |
| Memcached | ★★★★★ | ★★★★★ | Low | Low |
| Database | ★★☆☆☆ | ★★☆☆☆ | Low | Very Low |
| File System | ★★★☆☆ | ★★☆☆☆ | Very Low | Very Low |
| Local Memory | ★★★★★ | ★★★★★ | High | Very Low |
| Dummy | N/A | N/A | None | None |

### Feature Comparison

| Feature | Redis | Memcached | Database | File System | Local Memory |
|---------|-------|-----------|----------|-------------|--------------|
| Persistence | ✅ | ❌ | ✅ | ✅ | ❌ |
| Pattern Deletion | ✅ | ❌ | ❌ | ❌ | ❌ |
| Atomic Operations | ✅ | ✅ | ✅ | ❌ | ✅ |
| Multi-Server | ✅ | ✅ | ✅ | ❌ | ❌ |
| Key Expiration | ✅ | ✅ | ✅ | ✅ | ✅ |
| Complex Data Types | ✅ | ❌ | ❌ | ❌ | ✅ |
| Compression | ✅ | ✅ | ❌ | ❌ | ❌ |
| Eviction Policies | ✅ | ✅ | ✅ | ✅ | ✅ |

### Use Case Recommendations

**Redis:**
- Production applications
- Need for persistence
- Pattern-based cache invalidation
- Complex caching requirements
- High availability needed

**Memcached:**
- Very high throughput requirements
- Simple key-value caching
- Don't need persistence
- Multiple servers for distribution

**Database:**
- Shared hosting (no Redis/Memcached available)
- Small to medium traffic sites
- Already have database optimization
- Need persistence without extra services

**File System:**
- Single-server deployments
- Development/testing
- Limited memory
- Simple caching needs

**Local Memory:**
- Development only
- Single-process applications
- Testing cache logic
- Very fast access needed (in-process)

**Dummy:**
- Testing cache-dependent code
- Development with caching disabled
- CI/CD pipelines where caching interferes

## Common Configuration Options

### All Backends Support

```python
CACHES = {
    'default': {
        'BACKEND': '...',
        'LOCATION': '...',
        'TIMEOUT': 300,           # Default timeout (seconds)
        'KEY_PREFIX': 'myapp',    # Prefix for all keys
        'VERSION': 1,             # Cache version number
        'KEY_FUNCTION': 'path.to.make_key',  # Custom key function
    }
}
```

### Custom Key Function

```python
def make_key(key, key_prefix, version):
    """Custom cache key function"""
    return f'{key_prefix}:{version}:{key}'.lower()

CACHES = {
    'default': {
        'BACKEND': '...',
        'KEY_FUNCTION': 'myapp.utils.make_key',
    }
}
```

## Environment-Based Configuration

```python
import os

# Use environment variable to determine cache backend
CACHE_BACKEND = os.environ.get('CACHE_BACKEND', 'locmem')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1')

if CACHE_BACKEND == 'redis':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
elif CACHE_BACKEND == 'dummy':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'default',
        }
    }
```

## Production Best Practices

### Redis Production Config

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,  # Critical: don't break app
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'REDIS_CLIENT_KWARGS': {
                'ssl_cert_reqs': None,  # For SSL connections
            }
        },
        'KEY_PREFIX': os.environ.get('CACHE_KEY_PREFIX', 'myapp'),
        'VERSION': int(os.environ.get('CACHE_VERSION', '1')),
        'TIMEOUT': 300,
    }
}
```

### Connection Pooling

```python
# Redis connection pooling
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'timeout': 20,  # Block for 20s if no connection available
            }
        }
    }
}
```

### Monitoring and Logging

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'LOG_IGNORED_EXCEPTIONS': True,  # Log cache errors
        }
    }
}

# Configure logging
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django_redis': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    },
}
```
