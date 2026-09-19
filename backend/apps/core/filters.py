from rest_framework.filters import OrderingFilter


class StableOrderingFilter(OrderingFilter):
    """OrderingFilter that always adds `-id` as a final tie-breaker.

    Without it, rows with equal sort values (e.g. many toys at the same price)
    can come back in a different order on every request, so paginated results
    may repeat or skip items between pages.
    """

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        return [*(ordering or []), "-id"]