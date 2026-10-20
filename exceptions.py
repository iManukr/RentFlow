"""Custom exceptions for RentFlow.

Every error below is a ValueError, so calling code can either catch the
specific problem (`except VehicleNotAvailableError`) or catch them all with a
plain `except ValueError`.
"""


class RentFlowError(ValueError):
    """Base class for every RentFlow business-rule violation."""


class NotRegisteredError(RentFlowError):
    """A customer or vehicle is not known to the system."""


class VehicleNotAvailableError(RentFlowError):
    """The vehicle is already rented out or under maintenance."""


class VehicleNotRentedError(RentFlowError):
    """The vehicle is not currently out on rental, so it cannot be returned."""


class InvalidRentalPeriodError(RentFlowError):
    """Rental days must be greater than zero."""


class RentalAlreadyCompletedError(RentFlowError):
    """The rental has already been closed."""


class PaymentError(RentFlowError):
    """Base class for payment problems."""


class RentalNotCompletedError(PaymentError):
    """A rental can only be paid once the vehicle is back."""


class AlreadyPaidError(PaymentError):
    """A rental can only be paid once."""
