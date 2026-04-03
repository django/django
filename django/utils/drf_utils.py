"""
Django REST Framework utilities - helpful functions for DRF.
"""

from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message=None, status_code=status.HTTP_200_OK):
    """
    Create a standardized success response.

    Args:
        data: Response data
        message: Optional success message
        status_code: HTTP status code

    Returns:
        DRF Response object
    """
    response_data = {
        'success': True,
    }

    if message:
        response_data['message'] = message

    if data is not None:
        response_data['data'] = data

    return Response(response_data, status=status_code)


def error_response(message, error_code=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Create a standardized error response.

    Args:
        message: Error message
        error_code: Optional error code
        status_code: HTTP status code

    Returns:
        DRF Response object
    """
    response_data = {
        'success': False,
        'error': message,
    }

    if error_code:
        response_data['error_code'] = error_code

    return Response(response_data, status=status_code)


def paginated_response(queryset, serializer_class, request, per_page=20):
    """
    Create a paginated response for DRF views.

    Args:
        queryset: DRF queryset
        serializer_class: Serializer class for serialization
        request: DRF request object
        per_page: Items per page

    Returns:
        DRF Response with pagination info
    """
    from rest_framework.pagination import PageNumberPagination
    from rest_framework.generics import ListAPIView

    class CustomPagination(PageNumberPagination):
        page_size = per_page
        page_size_query_param = 'page_size'
        max_page_size = 100

    paginator = CustomPagination()
    page = paginator.paginate_queryset(queryset, request)

    if page is not None:
        serializer = serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = serializer_class(queryset, many=True)
    return Response(serializer.data)


def validate_request_data(data, required_fields):
    """
    Validate that required fields are present in request data.

    Args:
        data: Request data
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, missing_fields)
    """
    missing = [field for field in required_fields if field not in data or not data[field]]
    return len(missing) == 0, missing


class APIViewMixin:
    """
    Mixin class for standard API responses.
    """

    def success(self, data=None, message=None):
        """Return success response."""
        return success_response(data, message)

    def error(self, message, error_code=None, status_code=status.HTTP_400_BAD_REQUEST):
        """Return error response."""
        return error_response(message, error_code, status_code)