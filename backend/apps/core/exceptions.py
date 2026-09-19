"""Uniform error responses for the React client.

Every API error looks like:
    {"error": {"code": 400, "message": "Validation failed", "details": {...}}}
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:  # unhandled -> Django returns a 500
        return None

    data = response.data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        message, details = str(data["detail"]), None
    elif response.status_code == status.HTTP_400_BAD_REQUEST:
        message, details = "Validation failed", data
    else:
        message, details = "Request failed", data

    # Keep headers that clients rely on (throttling / auth challenges).
    keep = ("Retry-After", "WWW-Authenticate")
    headers = {h: response[h] for h in keep if response.has_header(h)}

    return Response(
        {"error": {"code": response.status_code, "message": message, "details": details}},
        status=response.status_code,
        headers=headers,
    )