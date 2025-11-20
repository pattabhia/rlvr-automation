"""
Shared OpenTelemetry configuration for all RLVR services.

This module provides a unified way to instrument FastAPI applications with:
- Distributed tracing (via Tempo)
- Metrics collection (via Prometheus)
- Structured logging (via Loki)

Usage:
    from shared.observability import setup_observability
    
    app = FastAPI(title="My Service")
    setup_observability(app, service_name="my-service")
"""

import os
import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

logger = logging.getLogger(__name__)


def setup_observability(
    app,
    service_name: str,
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = False
):
    """
    Set up OpenTelemetry instrumentation for a FastAPI application.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service (e.g., "api-gateway")
        service_version: Version of the service
        otlp_endpoint: OpenTelemetry Collector endpoint (default: from env or localhost:4317)
        enable_console_export: If True, also export to console for debugging
    
    Returns:
        Tuple of (tracer, meter) for custom instrumentation
    """
    # Get OTLP endpoint from environment or use default
    if otlp_endpoint is None:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    
    logger.info(f"Setting up observability for {service_name} (endpoint: {otlp_endpoint})")
    
    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # ========================================================================
    # Set up Tracing
    # ========================================================================
    
    # Create OTLP span exporter
    span_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True  # Use insecure for local development
    )
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    
    # Add batch span processor
    tracer_provider.add_span_processor(
        BatchSpanProcessor(span_exporter)
    )
    
    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)
    
    # ========================================================================
    # Set up Metrics
    # ========================================================================
    
    # Create OTLP metric exporter
    metric_exporter = OTLPMetricExporter(
        endpoint=otlp_endpoint,
        insecure=True
    )
    
    # Create metric reader with 60-second export interval
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=60000  # 60 seconds
    )
    
    # Create meter provider
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader]
    )
    
    # Set global meter provider
    metrics.set_meter_provider(meter_provider)
    
    # ========================================================================
    # Instrument FastAPI
    # ========================================================================
    
    # Auto-instrument FastAPI (captures all HTTP requests/responses)
    FastAPIInstrumentor.instrument_app(app)
    logger.info(f"FastAPI instrumented for {service_name}")
    
    # Auto-instrument HTTPX (captures outgoing HTTP calls)
    HTTPXClientInstrumentor().instrument()
    logger.info("HTTPX client instrumented")
    
    # Instrument logging (adds trace context to logs)
    LoggingInstrumentor().instrument(set_logging_format=True)
    logger.info("Logging instrumented")
    
    # ========================================================================
    # Return tracer and meter for custom instrumentation
    # ========================================================================
    
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)
    
    logger.info(f"✅ Observability setup complete for {service_name}")
    
    return tracer, meter


def get_tracer(name: str = __name__):
    """Get a tracer for custom span creation."""
    return trace.get_tracer(name)


def get_meter(name: str = __name__):
    """Get a meter for custom metrics."""
    return metrics.get_meter(name)


# ============================================================================
# RLVR-Specific Metrics
# ============================================================================

class RLVRMetrics:
    """
    Custom metrics for RLVR-specific observability.

    Tracks:
    - RAGAS scores (faithfulness, relevancy)
    - Reward scores
    - Candidate generation metrics
    - DPO training data quality
    """

    def __init__(self):
        self.meter = get_meter()

        # RAGAS Metrics
        self.ragas_faithfulness = self.meter.create_histogram(
            name="rlvr_ragas_faithfulness",
            description="RAGAS faithfulness score (0.0-1.0)",
            unit="1"
        )

        self.ragas_relevancy = self.meter.create_histogram(
            name="rlvr_ragas_relevancy",
            description="RAGAS answer relevancy score (0.0-1.0)",
            unit="1"
        )

        self.ragas_overall = self.meter.create_histogram(
            name="rlvr_ragas_overall",
            description="RAGAS overall score (0.0-1.0)",
            unit="1"
        )

        # Reward Metrics
        self.reward_score = self.meter.create_histogram(
            name="rlvr_reward_score",
            description="RLVR reward score for candidate answers (0.0-1.0)",
            unit="1"
        )

        # Candidate Metrics
        self.candidates_generated = self.meter.create_counter(
            name="rlvr_candidates_generated_total",
            description="Total number of candidate answers generated"
        )

        self.best_candidate_index = self.meter.create_histogram(
            name="rlvr_best_candidate_index",
            description="Index of the selected best candidate",
            unit="1"
        )

        # DPO Quality Metrics
        self.dpo_score_diff = self.meter.create_histogram(
            name="rlvr_dpo_score_difference",
            description="Score difference between chosen and rejected candidates",
            unit="1"
        )

        self.dpo_pairs_created = self.meter.create_counter(
            name="rlvr_dpo_pairs_created_total",
            description="Total number of DPO training pairs created"
        )

    def record_ragas_scores(self, faithfulness: float, relevancy: float,
                           attributes: dict = None):
        """Record RAGAS verification scores."""
        attrs = attributes or {}
        overall = (faithfulness + relevancy) / 2.0

        self.ragas_faithfulness.record(faithfulness, attrs)
        self.ragas_relevancy.record(relevancy, attrs)
        self.ragas_overall.record(overall, attrs)

    def record_reward_score(self, reward: float, attributes: dict = None):
        """Record RLVR reward score."""
        attrs = attributes or {}
        self.reward_score.record(reward, attrs)

    def record_candidates(self, num_candidates: int, best_index: int,
                         attributes: dict = None):
        """Record candidate generation metrics."""
        attrs = attributes or {}
        self.candidates_generated.add(num_candidates, attrs)
        self.best_candidate_index.record(best_index, attrs)

    def record_dpo_pair(self, chosen_score: float, rejected_score: float,
                       attributes: dict = None):
        """Record DPO training pair quality."""
        attrs = attributes or {}
        score_diff = chosen_score - rejected_score
        self.dpo_score_diff.record(score_diff, attrs)
        self.dpo_pairs_created.add(1, attrs)


# Global RLVR metrics instance
_rlvr_metrics: RLVRMetrics = None


def get_rlvr_metrics() -> RLVRMetrics:
    """
    Get the global RLVR metrics instance.

    Usage:
        from shared.observability import get_rlvr_metrics

        metrics = get_rlvr_metrics()
        metrics.record_ragas_scores(
            faithfulness=0.85,
            relevancy=0.92,
            attributes={"service": "qa-orchestrator"}
        )
    """
    global _rlvr_metrics
    if _rlvr_metrics is None:
        _rlvr_metrics = RLVRMetrics()
    return _rlvr_metrics
