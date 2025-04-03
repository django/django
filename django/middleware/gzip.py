from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin
from django.utils.regex_helper import _lazy_re_compile
from django.utils.text import compress_sequence, compress_string

re_accepts_gzip = _lazy_re_compile(r"\bgzip\b")


class GZipMiddleware(MiddlewareMixin):
    """
    Compress content if the browser allows gzip compression.
    Set the Vary header accordingly, so that caches will base their storage
    on the Accept-Encoding header.
    """

    max_random_bytes = 100

    @classmethod
    def should_streaming_gzip(cls, response=None) -> bool:
        """
        Determine whether gzip compression should be applied to the response.
        Can be disabled via response.no_gzip_streaming.

        eg1: streaming response no gzip
            response.no_gzip_streaming = True
        """
        no_gzip_streaming = getattr(response, "no_gzip_streaming", False)
        return not no_gzip_streaming

    @classmethod
    def should_flush_each(cls, response=None) -> bool:
        """
        Determine whether to enable flush_each.
        By default, enabled for text/event-stream unless explicitly disabled via
        response.no_flush_each.

        When gzip is enabled,
            SSE responses should enable flush_each to avoid blocking.

        eg1:
            # sse response will blocking
            response.no_flush_each = True
        """
        if getattr(response, "no_flush_each", False):
            return False
        return response.get("Content-Type", "").startswith("text/event-stream")

    def process_response(self, request, response):
        # It's not worth attempting to compress really short responses.
        if not response.streaming and len(response.content) < 200:
            return response

        # Avoid gzipping if we've already got a content-encoding.
        if response.has_header("Content-Encoding"):
            return response

        patch_vary_headers(response, ("Accept-Encoding",))

        ae = request.META.get("HTTP_ACCEPT_ENCODING", "")
        if not re_accepts_gzip.search(ae):
            return response

        if response.streaming:
            if not self.should_streaming_gzip(response=response):
                return response
            if response.is_async:
                # pull to lexical scope to capture fixed reference in case
                # streaming_content is set again later.
                orignal_iterator = response.streaming_content

                async def gzip_wrapper():
                    async for chunk in orignal_iterator:
                        yield compress_string(
                            chunk,
                            max_random_bytes=self.max_random_bytes,
                        )

                response.streaming_content = gzip_wrapper()
            else:
                # Determine whether to flush after each write.
                # This is important for SSE (Server-Sent Events) or similar streaming
                # responses that benefit from reduced latency and timely delivery.
                flush_each = self.should_flush_each(response=response)
                response.streaming_content = compress_sequence(
                    response.streaming_content,
                    max_random_bytes=self.max_random_bytes,
                    flush_each=flush_each,
                )
            # Delete the `Content-Length` header for streaming content, because
            # we won't know the compressed size until we stream it.
            del response.headers["Content-Length"]
        else:
            # Return the compressed content only if it's actually shorter.
            compressed_content = compress_string(
                response.content,
                max_random_bytes=self.max_random_bytes,
            )
            if len(compressed_content) >= len(response.content):
                return response
            response.content = compressed_content
            response.headers["Content-Length"] = str(len(response.content))

        # If there is a strong ETag, make it weak to fulfill the requirements
        # of RFC 9110 Section 8.8.1 while also allowing conditional request
        # matches on ETags.
        etag = response.get("ETag")
        if etag and etag.startswith('"'):
            response.headers["ETag"] = "W/" + etag
        response.headers["Content-Encoding"] = "gzip"

        return response
