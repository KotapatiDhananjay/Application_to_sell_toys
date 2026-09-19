class InsufficientStockError(ValueError):
    """Raised when a stock change would push inventory below zero."""

    def __init__(self, product, requested, available):
        self.product = product
        self.requested = requested
        self.available = available
        super().__init__(
            f"Only {available} unit(s) of '{product.name}' available "
            f"(requested {abs(requested)})."
        )