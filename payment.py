"""The payment hierarchy: Payment (abstract) + M-Pesa, Card, Cash."""

import random
import string
from abc import ABC, abstractmethod

from exceptions import PaymentError, RentalNotCompletedError


class Payment(ABC):
    """One payment against one rental's final bill.

    The amount is taken from the rental when the payment is created, which is
    why the rental has to be completed first: only then do the late and damage
    charges exist.
    """

    METHOD = "Payment"

    def __init__(self, rental):
        if rental is None:
            raise PaymentError("A payment must be linked to a rental.")
        if rental.status != "COMPLETED":
            raise RentalNotCompletedError(
                f"Rental {rental.rental_id} is {rental.status}; it can only be "
                "paid once the vehicle has been returned."
            )

        amount = rental.calculate_total()
        if amount < 0:
            raise PaymentError("Payment amounts cannot be negative.")

        self.rental = rental
        self.amount = amount
        self.__successful = False        # private: encapsulation

    def was_successful(self):
        return self.__successful

    def _mark_successful(self):
        """Child classes call this once the money has actually moved."""
        self.__successful = True

    @abstractmethod
    def process_payment(self):
        """Take the money. Return True on success, False on failure."""

    def __str__(self):
        state = "successful" if self.__successful else "pending"
        return (f"{self.METHOD} payment of KSh {self.amount:,} for "
                f"{self.rental.rental_id} ({state})")


class MpesaPayment(Payment):
    """Mobile money: generates a transaction code."""

    METHOD = "M-Pesa"

    def __init__(self, rental, phone_number):
        super().__init__(rental)
        if not phone_number:
            raise PaymentError("An M-Pesa payment needs a phone number.")
        self.phone_number = phone_number
        self.transaction_code = None

    def process_payment(self):
        print("Processing M-Pesa payment...")
        self.transaction_code = self._generate_transaction_code()
        print(f"Transaction: {self.transaction_code}")
        print(f"Payment of KSh {self.amount:,} successful.")
        self._mark_successful()
        return True

    @staticmethod
    def _generate_transaction_code():
        alphabet = string.ascii_uppercase + string.digits
        return "".join(random.choice(alphabet) for _ in range(10))


class CardPayment(Payment):
    """Card: only the last four digits are ever stored."""

    METHOD = "Card"

    def __init__(self, rental, card_last_four):
        super().__init__(rental)
        digits = str(card_last_four)
        if len(digits) != 4 or not digits.isdigit():
            raise PaymentError(
                "Store only the last four digits of the card number."
            )
        self.card_last_four = digits

    def process_payment(self):
        print("Processing card payment...")
        print(f"Card ending {self.card_last_four} charged "
              f"KSh {self.amount:,}")
        self._mark_successful()
        return True


class CashPayment(Payment):
    """Cash over the counter: fails if the customer is short."""

    METHOD = "Cash"

    def __init__(self, rental, amount_tendered):
        super().__init__(rental)
        if amount_tendered < 0:
            raise PaymentError("Cash received cannot be negative.")
        self.amount_tendered = amount_tendered
        self.change_due = 0

    def process_payment(self):
        print(f"Cash received: KSh {self.amount_tendered:,}")
        if self.amount_tendered < self.amount:
            shortfall = self.amount - self.amount_tendered
            print(f"Payment failed: KSh {shortfall:,} short of the "
                  f"KSh {self.amount:,} bill.")
            return False
        self.change_due = self.amount_tendered - self.amount
        print(f"Change due:    KSh {self.change_due:,}")
        print(f"Cash payment of KSh {self.amount:,} recorded.")
        self._mark_successful()
        return True
