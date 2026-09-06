"""OpenTelemetry tracer adapter.

Emits spans to whatever OTLP endpoint the environment configures. The SDK
imports lazily and initialization happens once, so constructing the adapter --
as the registry does at startup -- never imports OpenTelemetry or opens an
exporter. Spans carry RAG-specific attributes (prompt version, retrieved chunk
ids, reranker scores) so a trace explains an answer.
"""

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.config import Settings


class OTelTracer:
    """Spans via OpenTelemetry."""

    name = "otel"

    def __init__(self, service_name: str, endpoint: str | None) -> None:
        self._service_name = service_name
        self._endpoint = endpoint
        self._tracer: Any | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> OTelTracer:
        return cls(
            service_name=settings.OTEL_SERVICE_NAME,
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        )

    def _get_tracer(self) -> Any:
        if self._tracer is None:
            from opentelemetry import trace  # lazy import
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import (
                BatchSpanProcessor,
            )

            resource = Resource.create({"service.name": self._service_name})
            provider = TracerProvider(resource=resource)
            if self._endpoint:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )

                provider.add_span_processor(
                    BatchSpanProcessor(OTLPSpanExporter(endpoint=self._endpoint))
                )
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self._service_name)
        return self._tracer

    def span(self, name: str, **attributes: Any) -> AbstractContextManager[Any]:
        return self._span(name, **attributes)

    @contextmanager
    def _span(self, name: str, **attributes: Any):
        tracer = self._get_tracer()
        with tracer.start_as_current_span(name) as span:
            for key, value in attributes.items():
                span.set_attribute(key, value)
            yield span
