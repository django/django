import time
import threading
from django.db import connection
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.deprecation import MiddlewareMixin
from .structures import QueryHeap, StatsBuffer, UrlTrie

# Global instances (singleton-like for the process)
GLOBAL_QUERY_HEAP = QueryHeap(k=10)
GLOBAL_STATS_BUFFER = StatsBuffer(maxlen=100)
GLOBAL_URL_TRIE = UrlTrie()

class PerformanceMonitorMiddleware(MiddlewareMixin):
    """
    Middleware that tracks performance metrics and injects a HUD for superusers.
    """
    def process_request(self, request):
        request._monitor_start_time = time.time()
        # Track initial number of queries to isolate queries validation for this request
        if settings.DEBUG:
            request._monitor_start_queries = len(connection.queries)

    def process_response(self, request, response):
        if not hasattr(request, '_monitor_start_time'):
            return response

        duration = time.time() - request._monitor_start_time
        
        # Update Global Stats
        GLOBAL_STATS_BUFFER.append(duration)
        GLOBAL_URL_TRIE.add(request.path, duration)

        # Process Queries
        if settings.DEBUG and hasattr(request, '_monitor_start_queries'):
            start_idx = request._monitor_start_queries
            new_queries = connection.queries[start_idx:]
            for q in new_queries:
                # q is {'sql': '...', 'time': '0.001'}
                try:
                    q_time = float(q['time'])
                except (ValueError, TypeError):
                    q_time = 0.0
                
                GLOBAL_QUERY_HEAP.add(q_time, q['sql'])

        # Inject HUD if applicable
        if (getattr(request, 'user', None) and 
            request.user.is_superuser and 
            'text/html' in response.get('Content-Type', '') and
            not response.streaming):
            
            try:
                self.inject_hud(request, response, duration)
            except Exception as e:
                # Fail silently to not break the page
                print(f"Monitor HUD injection failed: {e}")

        return response

    def inject_hud(self, request, response, duration):
        content = response.content.decode(response.charset)
        body_end = content.lower().rfind('</body>')
        
        if body_end == -1:
            return

        # Prepare context
        min_lat, avg_lat, max_lat = GLOBAL_STATS_BUFFER.get_stats()
        chart_data = GLOBAL_STATS_BUFFER.get_data()
        top_queries = GLOBAL_QUERY_HEAP.get_top_k()
        
        context = {
            'duration_ms': f"{duration*1000:.2f}",
            'min_lat_ms': f"{min_lat*1000:.2f}",
            'avg_lat_ms': f"{avg_lat*1000:.2f}",
            'max_lat_ms': f"{max_lat*1000:.2f}",
            'chart_data': chart_data, # List of floats
            'top_queries': top_queries,
            'debug_on': settings.DEBUG,
        }
        
        hud_html = render_to_string('monitor/hud.html', context)
        
        new_content = content[:body_end] + hud_html + content[body_end:]
        response.content = new_content.encode(response.charset)
        if 'Content-Length' in response:
            try:
                response['Content-Length'] = len(response.content)
            except:
                pass # cookie handling can fail here in some versions
