import os
import django
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import User
from django.contrib.monitor.structures import UrlTrie, QueryHeap, StatsBuffer
from django.contrib.monitor.middleware import PerformanceMonitorMiddleware, GLOBAL_STATS_BUFFER, GLOBAL_QUERY_HEAP, GLOBAL_URL_TRIE

# Clear globals before tests
def clear_globals():
    GLOBAL_STATS_BUFFER.buffer.clear()
    GLOBAL_QUERY_HEAP.heap.clear()
    GLOBAL_URL_TRIE.root.children.clear()

monitor_templates = os.path.join(django.__path__[0], 'contrib/monitor/templates')
print(f"DEBUG: monitor_templates={monitor_templates}")
if os.path.exists(monitor_templates):
    print(f"DEBUG: contents={os.listdir(monitor_templates)}")
else:
    print(f"DEBUG: directory does not exist")


@override_settings(
    INSTALLED_APPS=['django.contrib.monitor', 'django.contrib.auth', 'django.contrib.contenttypes'],
    MIDDLEWARE=['django.contrib.monitor.middleware.PerformanceMonitorMiddleware'],
    DEBUG=True,
    TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [monitor_templates],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
            ],
        },
    }]
)
class MonitorDataStructuresTests(TestCase):
    def setUp(self):
        clear_globals()

    def test_query_heap(self):
        heap = QueryHeap(k=3)
        # Add 5 items
        heap.add(0.1, "SELECT 1")
        heap.add(0.5, "SELECT 5")
        heap.add(0.2, "SELECT 2")
        heap.add(0.9, "SELECT 9")
        heap.add(0.3, "SELECT 3")
        
        top = heap.get_top_k()
        # Should be [0.9, 0.5, 0.3]
        self.assertEqual(len(top), 3)
        self.assertEqual(top[0][0], 0.9)
        self.assertEqual(top[2][0], 0.3)

    def test_stats_buffer(self):
        buf = StatsBuffer(maxlen=3)
        buf.append(10)
        buf.append(20)
        buf.append(30)
        buf.append(40) # Should push out 10
        
        min_v, avg_v, max_v = buf.get_stats()
        self.assertEqual(min_v, 20)
        self.assertEqual(max_v, 40)
        self.assertEqual(avg_v, 30)

    def test_url_trie(self):
        trie = UrlTrie()
        trie.add("/api/v1/users/1/", 0.1)
        trie.add("/api/v1/users/2/", 0.2)
        trie.add("/api/v2/posts/", 0.3)
        
        hot = trie.get_hot_paths(limit=10)
        # Check paths exist
        paths = [p for p, t in hot]
        self.assertIn("/api/v1/users/1", paths)
        self.assertIn("/api/v1/users/2", paths)
        self.assertIn("/api/v2/posts", paths)

class MonitorMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PerformanceMonitorMiddleware(lambda r: None)
        clear_globals()
        
        # Create superuser
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.user = User.objects.create_user('user', 'user@example.com', 'password')

    def test_middleware_superuser_injection(self):
        from django.conf import settings
        
        # Manually override for this test block ensuring it applies
        with override_settings(
            INSTALLED_APPS=['django.contrib.monitor', 'django.contrib.auth', 'django.contrib.contenttypes'],
            TEMPLATES=[{
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [monitor_templates],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                    ],
                },
            }]
        ):
            request = self.factory.get('/admin/dashboard/')
            request.user = self.superuser
            
            # Simulating a view that returns HTML
            def get_response(req):
                from django.http import HttpResponse
                return HttpResponse("<html><body><h1>Dashboard</h1></body></html>", content_type="text/html")
            
            middleware = PerformanceMonitorMiddleware(get_response)
            response = middleware(request)
            
            content = response.content.decode()
            
            self.assertIn('id="dj-monitor-hud"', content)
            self.assertIn('DJANGO MONITOR', content)

    def test_middleware_anon_no_injection(self):
        request = self.factory.get('/')
        request.user = self.user # Normal user
        
        def get_response(req):
            from django.http import HttpResponse
            return HttpResponse("<html><body><h1>Home</h1></body></html>", content_type="text/html")
            
        middleware = PerformanceMonitorMiddleware(get_response)
        response = middleware(request)
        
        content = response.content.decode()
        self.assertNotIn('id="dj-monitor-hud"', content)
