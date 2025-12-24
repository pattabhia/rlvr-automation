"""
Unified logging configuration for RLVR Automation.

This module provides consistent logging across all services with:
- Correlation ID tracking
- Structured logging format
- Unified log file output
- Request lifecycle tracing
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

# Unified log directory
LOG_DIR = Path("/workspace/logs")
UNIFIED_LOG_FILE = LOG_DIR / "rlvr-unified.log"


class CorrelationIdFilter(logging.Filter):
    """Add correlation_id to log records."""
    
    def __init__(self):
        super().__init__()
        self.correlation_id = None
    
    def filter(self, record):
        # Add correlation_id to record if available
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = self.correlation_id or 'N/A'
        if not hasattr(record, 'batch_id'):
            record.batch_id = getattr(record, 'batch_id', 'N/A')
        if not hasattr(record, 'event_id'):
            record.event_id = getattr(record, 'event_id', 'N/A')
        return True


class StructuredFormatter(logging.Formatter):
    """Format logs with structured data for easy parsing."""
    
    def format(self, record):
        # Create structured log entry
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'service': record.name,
            'correlation_id': getattr(record, 'correlation_id', 'N/A'),
            'batch_id': getattr(record, 'batch_id', 'N/A'),
            'event_id': getattr(record, 'event_id', 'N/A'),
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Return as JSON for unified log, human-readable for console
        if hasattr(record, 'unified_format') and record.unified_format:
            return json.dumps(log_data)
        else:
            # Human-readable format for console
            return (
                f"{log_data['timestamp']} - {log_data['service']} - {log_data['level']} - "
                f"[correlation_id={log_data['correlation_id']}] "
                f"[batch_id={log_data['batch_id']}] "
                f"[event_id={log_data['event_id']}] - "
                f"{log_data['message']}"
            )


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    enable_unified_log: bool = True,
    enable_service_log: bool = True
) -> logging.Logger:
    """
    Setup logging for a service with correlation ID tracking.
    
    Args:
        service_name: Name of the service (e.g., 'qa-orchestrator', 'verification-worker')
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_unified_log: Write to unified log file
        enable_service_log: Write to service-specific log file
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    logger.addFilter(correlation_filter)
    
    # Console handler (human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)
    
    # Unified log handler (JSON format for easy parsing)
    if enable_unified_log:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        unified_handler = logging.FileHandler(UNIFIED_LOG_FILE)
        unified_handler.setLevel(logging.DEBUG)
        
        # Mark records for JSON formatting
        class UnifiedFilter(logging.Filter):
            def filter(self, record):
                record.unified_format = True
                return True
        
        unified_handler.addFilter(UnifiedFilter())
        unified_handler.setFormatter(StructuredFormatter())
        logger.addHandler(unified_handler)
    
    # Service-specific log handler (human-readable)
    if enable_service_log:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        service_log_file = LOG_DIR / f"{service_name}.log"
        service_handler = logging.FileHandler(service_log_file)
        service_handler.setLevel(logging.DEBUG)
        service_handler.setFormatter(StructuredFormatter())
        logger.addHandler(service_handler)
    
    # Store filter reference for updating correlation_id
    logger.correlation_filter = correlation_filter
    
    return logger


def set_correlation_id(logger: logging.Logger, correlation_id: Optional[str]):
    """Set correlation ID for all subsequent log messages."""
    if hasattr(logger, 'correlation_filter'):
        logger.correlation_filter.correlation_id = correlation_id


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    correlation_id: Optional[str] = None,
    batch_id: Optional[str] = None,
    event_id: Optional[str] = None,
    **kwargs
):
    """
    Log a message with full context (correlation_id, batch_id, event_id).
    
    Args:
        logger: Logger instance
        level: Log level (info, debug, warning, error)
        message: Log message
        correlation_id: Request correlation ID
        batch_id: Batch ID for multi-candidate requests
        event_id: Event ID
        **kwargs: Additional context to log
    """
    # Get log function
    log_func = getattr(logger, level.lower())
    
    # Create extra context
    extra = {}
    if correlation_id:
        extra['correlation_id'] = correlation_id
    if batch_id:
        extra['batch_id'] = batch_id
    if event_id:
        extra['event_id'] = event_id
    
    # Add any additional context
    extra.update(kwargs)
    
    # Log with context
    log_func(message, extra=extra)

