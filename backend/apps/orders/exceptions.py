class InvalidStatusTransition(ValueError):
    """Raised when an order is moved to a status that isn't allowed from its current one."""