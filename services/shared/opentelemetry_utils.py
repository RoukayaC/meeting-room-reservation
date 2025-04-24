from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.confluent_kafka import ConfluentKafkaInstrumentor
from prometheus_client import start_http_server
from flask import request  # Added missing import
import os
import logging

def setup_otel(app, service_name):
    """Setup OpenTelemetry instrumentation for the application"""
    try:
        # Create resource
        resource = Resource.create({
            "service.name": service_name,
            "service.version": os.environ.get("SERVICE_VERSION", "0.1.0"),
            "deployment.environment": os.environ.get("ENVIRONMENT", "development")
        })
        
        # Configure tracing
        trace_provider = TracerProvider(resource=resource)
        
        # Setup exporter based on configuration
        otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "")
        if otlp_endpoint:
            span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            span_processor = BatchSpanProcessor(span_exporter)
            trace_provider.add_span_processor(span_processor)
            app.logger.info(f"OpenTelemetry tracing configured with endpoint: {otlp_endpoint}")
        
        # Register the trace provider
        trace.set_tracer_provider(trace_provider)
        
        # Setup metrics
        metrics_readers = []
        
        # Configure Prometheus metrics export if enabled
        prometheus_port = os.environ.get("PROMETHEUS_PORT")
        if prometheus_port:
            prometheus_port = int(prometheus_port)
            prometheus_reader = PrometheusMetricReader()
            metrics_readers.append(prometheus_reader)
            # Start prometheus HTTP server
            start_http_server(prometheus_port)
            app.logger.info(f"Prometheus metrics server started on port {prometheus_port}")
        
        # Setup metric provider if we have readers
        if metrics_readers:
            metrics_provider = MeterProvider(resource=resource, metric_readers=metrics_readers)
            metrics.set_meter_provider(metrics_provider)
        
        # Instrument Flask
        FlaskInstrumentor().instrument_app(app)
        
        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument(engine=app.extensions['sqlalchemy'].db.engine)
        
        # Instrument requests
        RequestsInstrumentor().instrument()
        
        # Instrument Kafka
        ConfluentKafkaInstrumentor().instrument()
        
        # Create meters for Flask requests and errors
        meter = metrics.get_meter(service_name)
        request_counter = meter.create_counter(
            name="http_requests_total",
            description="Total count of HTTP requests",
            unit="1"
        )
        error_counter = meter.create_counter(
            name="http_error_requests_total",
            description="Total count of HTTP error requests",
            unit="1"
        )
        
        return {
            "trace_provider": trace_provider,
            "request_counter": request_counter,
            "error_counter": error_counter
        }
    
    except Exception as e:
        app.logger.error(f"Failed to initialize OpenTelemetry: {str(e)}")
        # Return dummy counters if setup fails
        return {
            "trace_provider": None,
            "request_counter": DummyCounter(),
            "error_counter": DummyCounter()
        }

def setup_request_hooks(app, request_counter, error_counter):
    """Setup request hooks for metrics collection"""
    
    @app.before_request
    def before_request():
        """Record request start time"""
        # This is empty in the original but could be used to track request timing
        pass
        
    @app.after_request
    def after_request(response):
        """Record metrics after each request"""
        try:
            request_counter.add(1, {
                "http.method": request.method,
                "http.url": request.path,
                "http.status_code": response.status_code,
            })
            
            # Record errors
            if 400 <= response.status_code < 600:
                error_counter.add(1, {
                    "http.method": request.method,
                    "http.url": request.path,
                    "http.status_code": response.status_code,
                })
        except Exception as e:
            app.logger.error(f"Error recording metrics: {str(e)}")
            
        return response
        
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Record unhandled exceptions"""
        app.logger.error(f"Unhandled exception: {str(error)}")
        try:
            error_counter.add(1, {
                "http.method": request.method,
                "http.url": request.path,
                "http.status_code": 500,
                "error.type": error.__class__.__name__
            })
        except Exception as e:
            app.logger.error(f"Error recording exception metrics: {str(e)}")
        
        # Let the default handlers take care of the response
        return None

class DummyCounter:
    """Dummy counter for when metrics setup fails"""
    def add(self, amount, attributes=None):
        pass