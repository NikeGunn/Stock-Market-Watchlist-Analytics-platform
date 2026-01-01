"""
Custom exception handler for consistent API error responses.

WHY: DRF's default error responses are inconsistent. We need a standard format
that clients can rely on. This handler transforms all errors into our standard format:
{
    "data": null,
    "meta": {...},
    "errors": [{"code": "...", "message": "...", "field": "..."}]
}
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


# Domain-specific error codes for better client-side error handling
ERROR_CODES = {
    'validation_error': 'VALIDATION_ERROR',
    'authentication_failed': 'AUTHENTICATION_FAILED',
    'permission_denied': 'PERMISSION_DENIED',
    'not_found': 'RESOURCE_NOT_FOUND',
    'method_not_allowed': 'METHOD_NOT_ALLOWED',
    'throttled': 'RATE_LIMIT_EXCEEDED',
    'server_error': 'INTERNAL_SERVER_ERROR',
}


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns errors in our standard format.
    
    WHY: Consistency is key in APIs. Clients should always know what to expect.
    This ensures all errors (validation, auth, server errors) use the same structure.
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)
    
    # If DRF handled the exception, format the response
    if response is not None:
        error_data = format_error_response(exc, response.data, response.status_code)
        response.data = error_data
        
        # Log the error
        request = context.get('request')
        logger.warning(
            f'API Error: {exc.__class__.__name__}',
            extra={
                'correlation_id': getattr(request, 'correlation_id', 'N/A') if request else 'N/A',
                'path': request.path if request else 'N/A',
                'method': request.method if request else 'N/A',
                'status_code': response.status_code,
                'errors': error_data.get('errors', []),
            }
        )
    else:
        # Unhandled exception - return 500
        logger.error(
            f'Unhandled exception: {exc}',
            exc_info=True,
            extra={
                'exception_type': type(exc).__name__,
            }
        )
        response = Response(
            format_error_response(
                exc,
                {'detail': 'An unexpected error occurred. Please try again later.'},
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return response


def format_error_response(exc, error_data, status_code):
    """
    Format error response in our standard structure.
    
    WHY: All errors should follow the same format for consistency.
    """
    errors = []
    
    # Handle different error data structures
    if isinstance(error_data, dict):
        # Check if it's a DRF validation error
        if 'detail' in error_data:
            errors.append({
                'code': get_error_code(exc),
                'message': str(error_data['detail']),
                'field': None,
            })
        else:
            # Field-specific validation errors
            for field, messages in error_data.items():
                if isinstance(messages, list):
                    for message in messages:
                        errors.append({
                            'code': get_error_code(exc),
                            'message': str(message),
                            'field': field if field != 'non_field_errors' else None,
                        })
                else:
                    errors.append({
                        'code': get_error_code(exc),
                        'message': str(messages),
                        'field': field if field != 'non_field_errors' else None,
                    })
    elif isinstance(error_data, list):
        for error in error_data:
            errors.append({
                'code': get_error_code(exc),
                'message': str(error),
                'field': None,
            })
    else:
        errors.append({
            'code': get_error_code(exc),
            'message': str(error_data),
            'field': None,
        })
    
    return {
        'data': None,
        'meta': {
            'status_code': status_code,
            'success': False,
        },
        'errors': errors,
    }


def get_error_code(exc):
    """
    Get domain-specific error code based on exception type.
    
    WHY: Client applications can handle errors programmatically
    using error codes instead of parsing error messages.
    """
    exc_class_name = exc.__class__.__name__
    
    mapping = {
        'ValidationError': ERROR_CODES['validation_error'],
        'ParseError': ERROR_CODES['validation_error'],
        'AuthenticationFailed': ERROR_CODES['authentication_failed'],
        'NotAuthenticated': ERROR_CODES['authentication_failed'],
        'PermissionDenied': ERROR_CODES['permission_denied'],
        'NotFound': ERROR_CODES['not_found'],
        'MethodNotAllowed': ERROR_CODES['method_not_allowed'],
        'Throttled': ERROR_CODES['throttled'],
    }
    
    return mapping.get(exc_class_name, ERROR_CODES['server_error'])
