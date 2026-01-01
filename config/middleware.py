"""
Custom middleware for request logging, correlation IDs, and exception handling.

WHY: Middleware intercepts all requests/responses before they reach views.
- RequestLoggingMiddleware: Adds correlation IDs for tracing requests across services
- ExceptionHandlingMiddleware: Catches unhandled exceptions and logs them
"""

import uuid
import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all incoming requests with correlation IDs.
    
    WHY: In production, we need to track requests across microservices.
    Correlation IDs help us trace a single user request through multiple services.
    """
    
    def process_request(self, request):
        """Add correlation ID to each request."""
        # Generate unique correlation ID for this request
        request.correlation_id = str(uuid.uuid4())
        request.start_time = time.time()
        
        logger.info(
            'Incoming request',
            extra={
                'correlation_id': request.correlation_id,
                'method': request.method,
                'path': request.path,
                'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
            }
        )
    
    def process_response(self, request, response):
        """Log request completion with duration."""
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            logger.info(
                'Request completed',
                extra={
                    'correlation_id': getattr(request, 'correlation_id', 'N/A'),
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': round(duration * 1000, 2),
                }
            )
        
        # Add correlation ID to response headers for debugging
        if hasattr(request, 'correlation_id'):
            response['X-Correlation-ID'] = request.correlation_id
        
        return response


class ExceptionHandlingMiddleware(MiddlewareMixin):
    """
    Middleware to catch and log unhandled exceptions.
    
    WHY: Some exceptions might not be caught by DRF's exception handler.
    This ensures ALL errors are logged with proper context.
    """
    
    def process_exception(self, request, exception):
        """Log unhandled exceptions with full context."""
        logger.error(
            'Unhandled exception',
            exc_info=True,
            extra={
                'correlation_id': getattr(request, 'correlation_id', 'N/A'),
                'method': request.method,
                'path': request.path,
                'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
            }
        )
        # Let Django's default exception handling continue
        return None
