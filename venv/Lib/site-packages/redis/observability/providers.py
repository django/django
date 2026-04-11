"""
OpenTelemetry provider management for redis-py.

This module handles initialization and lifecycle management of OTel SDK components
including MeterProvider, TracerProvider (future), and LoggerProvider (future).

Uses a singleton pattern - initialize once globally, all Redis clients use it automatically.

Redis-py uses the global MeterProvider set by your application. Set it up before
initializing observability:

    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider

    provider = MeterProvider(...)
    metrics.set_meter_provider(provider)

    # Then initialize redis-py observability
    otel = get_observability_instance()
    otel.init(OTelConfig(enable_metrics=True))
"""

import logging
from typing import Optional

from redis.observability.config import OTelConfig

logger = logging.getLogger(__name__)

# Optional imports - OTel SDK may not be installed
try:
    from opentelemetry.sdk.metrics import MeterProvider

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    MeterProvider = None

# Global singleton instance
_global_provider_manager: Optional["OTelProviderManager"] = None


class OTelProviderManager:
    """
    Manages OpenTelemetry SDK providers and their lifecycle.

    This class handles:
    - Getting the global MeterProvider set by the application
    - Configuring histogram bucket boundaries via Views
    - Graceful shutdown

    Args:
        config: OTel configuration object
    """

    def __init__(self, config: OTelConfig):
        self.config = config
        self._meter_provider: Optional[MeterProvider] = None

    def get_meter_provider(self) -> Optional[MeterProvider]:
        """
        Get the global MeterProvider set by the application.

        Returns:
            MeterProvider instance or None if metrics are disabled

        Raises:
            ImportError: If OpenTelemetry is not installed
            RuntimeError: If metrics are enabled but no global MeterProvider is set
        """
        if not self.config.is_enabled():
            return None

        # Lazy import - only import OTel when metrics are enabled
        try:
            from opentelemetry import metrics
            from opentelemetry.metrics import NoOpMeterProvider
        except ImportError:
            raise ImportError(
                "OpenTelemetry is not installed. Install it with:\n"
                "  pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http"
            )

        # Get the global MeterProvider
        if self._meter_provider is None:
            self._meter_provider = metrics.get_meter_provider()

            # Check if it's a real provider (not NoOp)
            if isinstance(self._meter_provider, NoOpMeterProvider):
                raise RuntimeError(
                    "Metrics are enabled but no global MeterProvider is configured.\n"
                    "\n"
                    "Set up OpenTelemetry before initializing redis-py observability:\n"
                    "\n"
                    "  from opentelemetry import metrics\n"
                    "  from opentelemetry.sdk.metrics import MeterProvider\n"
                    "  from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader\n"
                    "  from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter\n"
                    "\n"
                    "  # Create exporter\n"
                    "  exporter = OTLPMetricExporter(\n"
                    "      endpoint='http://localhost:4318/v1/metrics'\n"
                    "  )\n"
                    "\n"
                    "  # Create reader\n"
                    "  reader = PeriodicExportingMetricReader(\n"
                    "      exporter=exporter,\n"
                    "      export_interval_millis=10000\n"
                    "  )\n"
                    "\n"
                    "  # Create and set global provider\n"
                    "  provider = MeterProvider(metric_readers=[reader])\n"
                    "  metrics.set_meter_provider(provider)\n"
                    "\n"
                    "  # Now initialize redis-py observability\n"
                    "  from redis.observability import get_observability_instance, OTelConfig\n"
                    "  otel = get_observability_instance()\n"
                    "  otel.init(OTelConfig(enable_metrics=True))\n"
                )

            logger.info("Using global MeterProvider from application")

        return self._meter_provider

    def shutdown(self, timeout_millis: int = 30000) -> bool:
        """
        Shutdown observability and flush any pending metrics.

        Note: We don't shutdown the global MeterProvider since it's owned by the application.
        We only force flush pending metrics.

        Args:
            timeout_millis: Maximum time to wait for flush

        Returns:
            True if flush was successful, False otherwise
        """
        logger.debug(
            "Flushing metrics before shutdown (not shutting down global MeterProvider)"
        )
        return self.force_flush(timeout_millis=timeout_millis)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Force flush any pending metrics from the global MeterProvider.

        Args:
            timeout_millis: Maximum time to wait for flush

        Returns:
            True if flush was successful, False otherwise
        """
        if self._meter_provider is None:
            return True

        # NoOpMeterProvider doesn't have force_flush method
        if not hasattr(self._meter_provider, "force_flush"):
            logger.debug("MeterProvider does not support force_flush, skipping")
            return True

        try:
            logger.debug("Force flushing metrics from global MeterProvider")
            self._meter_provider.force_flush(timeout_millis=timeout_millis)
            return True
        except Exception as e:
            logger.error(f"Error flushing metrics: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit - shutdown provider."""
        self.shutdown()

    def __repr__(self) -> str:
        return f"OTelProviderManager(config={self.config})"


# Singleton instance class


class ObservabilityInstance:
    """
    Singleton instance for managing OpenTelemetry observability.

    This class follows the singleton pattern similar to Glide's GetOtelInstance().
    Use GetObservabilityInstance() to get the singleton instance, then call init()
    to initialize observability.

    Example:
        >>> from redis.observability.config import OTelConfig
        >>>
        >>> # Get singleton instance
        >>> otel = get_observability_instance()
        >>>
        >>> # Initialize once at app startup
        >>> otel.init(OTelConfig())
        >>>
        >>> # All Redis clients now automatically collect metrics
        >>> import redis
        >>> r = redis.Redis(host='localhost', port=6379)
        >>> r.set('key', 'value')  # Metrics collected automatically
    """

    def __init__(self):
        self._provider_manager: Optional[OTelProviderManager] = None

    def init(self, config: OTelConfig) -> "ObservabilityInstance":
        """
        Initialize OpenTelemetry observability globally for all Redis clients.

        This should be called once at application startup. After initialization,
        all Redis clients will automatically collect and export metrics without
        needing any additional configuration.

        Safe to call multiple times - will shutdown previous instance before
        initializing a new one.

        Args:
            config: OTel configuration object

        Returns:
            Self for method chaining

        Example:
            >>> otel = get_observability_instance()
            >>> otel.init(OTelConfig())
        """
        if self._provider_manager is not None:
            logger.warning(
                "Observability already initialized. Shutting down previous instance."
            )
            self._provider_manager.shutdown()

        self._provider_manager = OTelProviderManager(config)

        logger.info("Observability initialized")

        return self

    def is_enabled(self) -> bool:
        """
        Check if observability is enabled.

        Returns:
            True if observability is initialized and metrics are enabled

        Example:
            >>> otel = get_observability_instance()
            >>> if otel.is_enabled():
            ...     print("Metrics are being collected")
        """
        return (
            self._provider_manager is not None
            and self._provider_manager.config.is_enabled()
        )

    def get_provider_manager(self) -> Optional[OTelProviderManager]:
        """
        Get the provider manager instance.

        Returns:
            The provider manager, or None if not initialized

        Example:
            >>> otel = get_observability_instance()
            >>> manager = otel.get_provider_manager()
            >>> if manager is not None:
            ...     print(f"Observability enabled: {manager.config.is_enabled()}")
        """
        return self._provider_manager

    def shutdown(self, timeout_millis: int = 30000) -> bool:
        """
        Shutdown observability and flush any pending metrics.

        This should be called at application shutdown to ensure all metrics
        are exported before the application exits.

        Args:
            timeout_millis: Maximum time to wait for shutdown

        Returns:
            True if shutdown was successful

        Example:
            >>> otel = get_observability_instance()
            >>> # At application shutdown
            >>> otel.shutdown()
        """
        if self._provider_manager is None:
            logger.debug("Observability not initialized, nothing to shutdown")
            return True

        success = self._provider_manager.shutdown(timeout_millis)
        self._provider_manager = None
        logger.info("Observability shutdown")

        return success

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Force flush all pending metrics immediately.

        Useful for testing or when you want to ensure metrics are exported
        before a specific point in your application.

        Args:
            timeout_millis: Maximum time to wait for flush

        Returns:
            True if flush was successful

        Example:
            >>> otel = get_observability_instance()
            >>> # Execute some Redis commands
            >>> r.set('key', 'value')
            >>> # Force flush metrics immediately
            >>> otel.force_flush()
        """
        if self._provider_manager is None:
            logger.debug("Observability not initialized, nothing to flush")
            return True

        return self._provider_manager.force_flush(timeout_millis)


# Global singleton instance
_observability_instance: Optional[ObservabilityInstance] = None


def get_observability_instance() -> ObservabilityInstance:
    """
    Get the global observability singleton instance.

    This is the Pythonic way to get the singleton instance.

    Returns:
        The global ObservabilityInstance singleton

    Example:
        >>>
        >>> otel = get_observability_instance()
        >>> otel.init(OTelConfig())
    """
    global _observability_instance

    if _observability_instance is None:
        _observability_instance = ObservabilityInstance()

    return _observability_instance


def reset_observability_instance() -> None:
    """
    Reset the global observability singleton instance.

    This is primarily used for testing and benchmarking to ensure
    a clean state between test runs.

    Warning:
        This will shutdown any active provider manager and reset
        the global state. Use with caution in production code.
    """
    global _observability_instance

    if _observability_instance is not None:
        _observability_instance.shutdown()
        _observability_instance = None
