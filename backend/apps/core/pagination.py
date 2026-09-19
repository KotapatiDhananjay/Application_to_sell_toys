from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """12 items per page by default; clients may ask for ?page_size=N (max 48)."""

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 48