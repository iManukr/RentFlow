"""The Rental class: one customer + one vehicle + one bill."""

from datetime import datetime

from exceptions import (
    AlreadyPaidError,
    InvalidRentalPeriodError,
    RentalAlreadyCompletedError,
    RentalNotCompletedError,
    RentFlowError,
)

LINE_WIDTH = 36


def money(label, amount):
    """Format one money line of a receipt: label left, amount right."""
    return f"{label:<17} KSh {amount:>6,}"


class Rental:
    """Tracks one hire from pick-up to final payment."""

    LATE_PENALTY_RATE = 0.20     # 20% of the daily rate, per late day
    _counter = 0

    def __init__(self, customer, vehicle, rental_days, rental_id=None):
        if rental_days <= 0:
            raise InvalidRentalPeriodError(
                "Rental days must be greater than zero."
            )

        if rental_id is None:            # bonus: automatic IDs (R001, R002...)
            Rental._counter += 1
            rental_id = f"R{Rental._counter:03d}"

        self.rental_id = rental_id
        self.customer = customer
        self.vehicle = vehicle
        self.rental_days = rental_days
        self.actual_days = None          # filled in on return
        self.status = "ACTIVE"
        self.base_cost = vehicle.calculate_rental_cost(rental_days)
        self.late_fee = 0
        self.damage_charge = 0
        self.__paid = False              # private: encapsulation
        self.started_at = datetime.now()
        self.returned_at = None

    # --- the bill --------------------------------------------------------

    def late_days(self):
        if self.actual_days is None:
            return 0
        return max(0, self.actual_days - self.rental_days)

    def calculate_late_fee(self):
        """20% of the daily rate for every extra day the car was kept.

        The penalty is based on the daily rate only: it never charges a
        second service charge or a second insurance premium.
        """
        daily_penalty = round(self.vehicle.daily_rate * self.LATE_PENALTY_RATE)
        return daily_penalty * self.late_days()

    def calculate_total(self):
        return self.base_cost + self.late_fee + self.damage_charge

    # --- lifecycle -------------------------------------------------------

    def complete_rental(self, actual_days, damage_charge=0):
        """Record the return, add any late and damage charges, and close."""
        if self.status == "COMPLETED":
            raise RentalAlreadyCompletedError(
                f"Rental {self.rental_id} has already been completed."
            )
        if self.status == "CANCELLED":
            raise RentFlowError(
                f"Rental {self.rental_id} was cancelled and cannot be returned."
            )
        if actual_days <= 0:
            raise InvalidRentalPeriodError(
                "Actual days must be greater than zero."
            )
        if damage_charge < 0:
            raise ValueError("Damage charge cannot be negative.")

        self.actual_days = actual_days
        self.damage_charge = damage_charge
        self.late_fee = self.calculate_late_fee()
        self.status = "COMPLETED"
        self.returned_at = datetime.now()
        return self.calculate_total()

    def cancel(self):
        if self.status != "ACTIVE":
            raise RentFlowError(
                f"Only an active rental can be cancelled "
                f"(rental {self.rental_id} is {self.status})."
            )
        self.status = "CANCELLED"

    # --- payment status --------------------------------------------------

    def is_paid(self):
        return self.__paid

    def mark_as_paid(self):
        if self.status != "COMPLETED":
            raise RentalNotCompletedError(
                f"Rental {self.rental_id} must be completed before payment."
            )
        if self.__paid:
            raise AlreadyPaidError(
                f"Rental {self.rental_id} has already been paid."
            )
        self.__paid = True

    # --- output ----------------------------------------------------------

    def display_rental_details(self):
        """Print the receipt."""
        days = self.rental_days
        rental_charge = self.vehicle.daily_rate * days

        print("=" * LINE_WIDTH)
        print("SAFARIDRIVE RENTALS".center(LINE_WIDTH).rstrip())
        print("=" * LINE_WIDTH)
        print(f"{'Rental ID:':<18}{self.rental_id}")
        print(f"{'Customer:':<18}{self.customer.name}")
        print(f"{'Vehicle:':<18}{self.vehicle.full_name}")
        print(f"{'Registration:':<18}{self.vehicle.registration_number}")
        print(f"{'Rental Period:':<18}{days} days")
        if self.actual_days is not None and self.actual_days != days:
            print(f"{'Days Kept:':<18}{self.actual_days} days")
        print(f"{'Daily Rate:':<18}KSh {self.vehicle.daily_rate:,}")
        print()
        print(money("Rental Charge:", rental_charge))
        for label, amount in self.vehicle.extra_charges(days):
            print(money(label, amount))
        if self.late_fee:
            late = self.late_days()
            label = f"Late Fee ({late} day{'s' if late != 1 else ''}):"
            print(money(label, self.late_fee))
        if self.damage_charge:
            print(money("Damage Charge:", self.damage_charge))
        print("-" * LINE_WIDTH)
        print(money("TOTAL:", self.calculate_total()))
        print(f"{'Status:':<18}{self.status}")
        print(f"{'Payment:':<18}{'PAID' if self.__paid else 'UNPAID'}")
        print("=" * LINE_WIDTH)

    def summary(self):
        days = self.actual_days or self.rental_days
        return (f"{self.rental_id}  {self.customer.name:<14} "
                f"{self.vehicle.full_name:<22} "
                f"{self.vehicle.registration_number:<10} "
                f"{days} day(s)  KSh {self.calculate_total():>8,}  "
                f"{'PAID' if self.__paid else 'UNPAID'}")

    def __str__(self):
        return (f"{self.rental_id}: {self.customer.name} -> "
                f"{self.vehicle.full_name} ({self.status})")
