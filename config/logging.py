"""
Custom JSON logging formatter for structured logging.

WHY: In production, we use tools like ELK Stack, Datadog, or CloudWatch.
These tools work best with structured JSON logs instead of plain text.
JSON logs can be easily parsed, searched, and analyzed.
"""

import json
import logging
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    WHY: Structured logs are easier to query and analyze in production.
    Example: We can search for all errors from a specific user in a time range.
    """
    
    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields if present (like correlation_id)
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        if hasattr(record, 'user'):
            log_data['user'] = record.user
        
        if hasattr(record, 'path'):
            log_data['path'] = record.path
        
        if hasattr(record, 'method'):
            log_data['method'] = record.method
        
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code
        
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)
