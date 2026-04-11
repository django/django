from enum import IntFlag, auto
from typing import List, Optional, Sequence

"""
OpenTelemetry configuration for redis-py.

This module handles configuration for OTel observability features,
including parsing environment variables and validating settings.
"""


class MetricGroup(IntFlag):
    """Metric groups that can be enabled/disabled."""

    RESILIENCY = auto()
    CONNECTION_BASIC = auto()
    CONNECTION_ADVANCED = auto()
    COMMAND = auto()
    CSC = auto()
    STREAMING = auto()
    PUBSUB = auto()


class TelemetryOption(IntFlag):
    """Telemetry options to export."""

    METRICS = auto()


def default_operation_duration_buckets() -> Sequence[float]:
    return [
        0.0001,
        0.00025,
        0.0005,
        0.001,
        0.0025,
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2.5,
    ]


def default_histogram_buckets() -> Sequence[float]:
    return [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10]


class OTelConfig:
    """
    Configuration for OpenTelemetry observability in redis-py.

    This class manages all OTel-related settings including metrics, traces (future),
    and logs (future). Configuration can be provided via constructor parameters or
    environment variables (OTEL_* spec).

    Constructor parameters take precedence over environment variables.

    Args:
        enabled_telemetry: Enabled telemetry options to export (default: metrics). Traces and logs will be added
                           in future phases.
        metric_groups: Group of metrics that should be exported.
        include_commands: Explicit allowlist of commands to track
        exclude_commands: Blocklist of commands to track
        hide_pubsub_channel_names: If True, hide PubSub channel names in metrics (default: False)
        hide_stream_names: If True, hide stream names in streaming metrics (default: False)

    Note:
        Redis-py uses the global MeterProvider set by your application.
        Set it up before initializing observability:

            from opentelemetry import metrics
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics._internal.view import View
            from opentelemetry.sdk.metrics._internal.aggregation import ExplicitBucketHistogramAggregation

            # Configure histogram bucket boundaries via Views
            views = [
                View(
                    instrument_name="db.client.operation.duration",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005,
                                    0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5]
                    ),
                ),
                # Add more views for other histograms...
            ]

            provider = MeterProvider(views=views, metric_readers=[reader])
            metrics.set_meter_provider(provider)

            # Then initialize redis-py observability
            from redis.observability import get_observability_instance, OTelConfig
            otel = get_observability_instance()
            otel.init(OTelConfig())
    """

    DEFAULT_TELEMETRY = TelemetryOption.METRICS
    DEFAULT_METRIC_GROUPS = MetricGroup.CONNECTION_BASIC | MetricGroup.RESILIENCY

    def __init__(
        self,
        # Core enablement
        enabled_telemetry: Optional[List[TelemetryOption]] = None,
        # Metrics-specific
        metric_groups: Optional[List[MetricGroup]] = None,
        # Redis-specific telemetry controls
        include_commands: Optional[List[str]] = None,
        exclude_commands: Optional[List[str]] = None,
        # Privacy controls
        hide_pubsub_channel_names: bool = False,
        hide_stream_names: bool = False,
        # Bucket sizes
        buckets_operation_duration: Sequence[
            float
        ] = default_operation_duration_buckets(),
        buckets_stream_processing_duration: Sequence[
            float
        ] = default_histogram_buckets(),
        buckets_connection_create_time: Sequence[float] = default_histogram_buckets(),
        buckets_connection_wait_time: Sequence[float] = default_histogram_buckets(),
    ):
        # Core enablement
        if enabled_telemetry is None:
            self.enabled_telemetry = self.DEFAULT_TELEMETRY
        else:
            self.enabled_telemetry = TelemetryOption(0)
            for option in enabled_telemetry:
                self.enabled_telemetry |= option

        # Enable default metrics if None given
        if metric_groups is None:
            self.metric_groups = self.DEFAULT_METRIC_GROUPS
        else:
            self.metric_groups = MetricGroup(0)
            for metric_group in metric_groups:
                self.metric_groups |= metric_group

        # Redis-specific controls
        self.include_commands = set(include_commands) if include_commands else None
        self.exclude_commands = set(exclude_commands) if exclude_commands else set()

        # Privacy controls for hiding sensitive names in metrics
        self.hide_pubsub_channel_names = hide_pubsub_channel_names
        self.hide_stream_names = hide_stream_names

        # Bucket sizes
        self.buckets_operation_duration = buckets_operation_duration
        self.buckets_stream_processing_duration = buckets_stream_processing_duration
        self.buckets_connection_create_time = buckets_connection_create_time
        self.buckets_connection_wait_time = buckets_connection_wait_time

    def is_enabled(self) -> bool:
        """Check if any observability feature is enabled."""
        return bool(self.enabled_telemetry)

    def should_track_command(self, command_name: str) -> bool:
        """
        Determine if a command should be tracked based on include/exclude lists.

        Args:
            command_name: The Redis command name (e.g., 'GET', 'SET')

        Returns:
            True if the command should be tracked, False otherwise
        """
        command_upper = command_name.upper()

        # If include list is specified, only track commands in the list
        if self.include_commands is not None:
            return command_upper in self.include_commands

        # Otherwise, track all commands except those in exclude list
        return command_upper not in self.exclude_commands

    def __repr__(self) -> str:
        return f"OTelConfig(enabled_telemetry={self.enabled_telemetry}"
