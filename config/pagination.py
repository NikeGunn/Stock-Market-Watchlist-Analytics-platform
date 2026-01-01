"""
Custom pagination classes for efficient data retrieval.

WHY: When dealing with large datasets (like stock prices), we can't return
all records at once. Pagination splits data into manageable chunks.

Cursor-based pagination is better than offset-based for:
1. Performance: No need to count total records
2. Consistency: New records don't affect pagination
3. Scalability: Works well with millions of records
"""

from rest_framework.pagination import CursorPagination
from collections import OrderedDict
from rest_framework.response import Response


class CustomCursorPagination(CursorPagination):
    """
    Custom cursor-based pagination with consistent response format.
    
    WHY CURSOR PAGINATION?
    - Offset pagination (LIMIT/OFFSET) becomes slow with large datasets
    - Cursor pagination uses indexed fields for fast lookups
    - Example: Instead of LIMIT 100 OFFSET 10000, we use WHERE id > 10100 LIMIT 100
    """
    
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    ordering = '-created_at'  # Default ordering
    
    def get_paginated_response(self, data):
        """
        Return paginated response in our standard format.
        
        WHY: Consistent response format across all endpoints.
        Clients know to expect 'data', 'meta', and 'errors' fields.
        """
        return Response(OrderedDict([
            ('data', data),
            ('meta', OrderedDict([
                ('next', self.get_next_link()),
                ('previous', self.get_previous_link()),
                ('count', len(data)),
            ])),
            ('errors', []),
        ]))
