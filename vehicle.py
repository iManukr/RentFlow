"""The vehicle hierarchy: Vehicle (abstract) + EconomyCar, SUV, LuxuryCar."""

from abc import ABC, abstractmethod

from exceptions import VehicleNotAvailableError, VehicleNotRentedError


class Vehicle(ABC):
    """A car in the fleet.

    This class is abstract: it says *what* every vehicle must be able to do
    (work out its own rental cost) without saying *how*. Creating a plain
    Vehicle raises a TypeError, which is abstraction doing its job.
    """

    CATEGORY = "Vehicle"        # used by search_vehicles()
    PLURAL = "Vehicles"         # used in listing headings

    def __init__(self, registration_number, make, model, year, daily_rate):
        if not registration_number:
            raise ValueError("A vehicle must have a registration number.")
        if daily_rate < 0:
            raise ValueError("Daily rate cannot be negative.")

        self.registration_number = registration_number
        self.make = make
        self.model = model
        self.year = year
        self.daily_rate = daily_rate
        self.__available = True            # private: encapsulation
        self.__under_maintenance = False   # private: encapsulation

    # --- read-only views of the protected state -------------------------

    @property
    def full_name(self):
        return f"{self.make} {self.model}"

    @property
    def status(self):
        if self.__under_maintenance:
            return "MAINTENANCE"
        return "AVAILABLE" if self.__available else "RENTED"

    def is_available(self):
        return self.__available and not self.__under_maintenance

    def is_rented(self):
        return not self.__available

    # --- the only ways to change that state -----------------------------

    def mark_as_rented(self):
        if not self.is_available():
            raise VehicleNotAvailableError(
                f"{self.registration_number} is not available ({self.status})."
            )
        self.__available = False

    def mark_as_available(self):
        self.__available = True
        self.__under_maintenance = False

    def send_for_maintenance(self):
        if self.is_rented():
            raise VehicleNotAvailableError(
                f"{self.registration_number} is out on rental and cannot go "
                "for maintenance yet."
            )
        self.__under_maintenance = True

    def return_from_maintenance(self):
        if not self.__under_maintenance:
            raise VehicleNotRentedError(
                f"{self.registration_number} is not under maintenance."
            )
        self.__under_maintenance = False

    # --- costing ---------------------------------------------------------

    @abstractmethod
    def calculate_rental_cost(self, days):
        """Return the cost of renting this vehicle for `days` days."""

    def extra_charges(self, days):
        """Return [(label, amount)] of charges on top of the daily rate.

        Overridden by the child classes so a receipt can print the right
        extra line without ever asking what type of car it is holding.
        """
        return []

    def _check_days(self, days):
        if days <= 0:
            raise ValueError("Rental days must be greater than zero.")

    # --- output ----------------------------------------------------------

    def display_details(self):
        print(f"{self.registration_number}  {self.full_name} ({self.year})")
        print(
            f"  Category: {self.CATEGORY:<8} "
            f"Rate: KSh {self.daily_rate:,}/day    "
            f"Status: {self.status}"
        )

    def __str__(self):
        return f"{self.full_name} [{self.registration_number}] - {self.status}"


class EconomyCar(Vehicle):
    """Small, cheap, no extras: the cost is simply rate x days."""

    CATEGORY = "Economy"
    PLURAL = "Economy Cars"

    def calculate_rental_cost(self, days):
        self._check_days(days)
        return self.daily_rate * days


class SUV(Vehicle):
    """Bigger car: a one-off service charge is added to every rental."""

    CATEGORY = "SUV"
    PLURAL = "SUVs"
    SERVICE_CHARGE = 2000

    def calculate_rental_cost(self, days):
        self._check_days(days)
        return self.daily_rate * days + self.SERVICE_CHARGE

    def extra_charges(self, days):
        return [("Service Charge:", self.SERVICE_CHARGE)]


class LuxuryCar(Vehicle):
    """Premium car: insurance is charged as a percentage of the rental."""

    CATEGORY = "Luxury"
    PLURAL = "Luxury Cars"
    INSURANCE_RATE = 0.10

    def calculate_rental_cost(self, days):
        self._check_days(days)
        rental_charge = self.daily_rate * days
        return rental_charge + self._insurance(rental_charge)

    def extra_charges(self, days):
        self._check_days(days)
        return [("Insurance (10%):", self._insurance(self.daily_rate * days))]

    def _insurance(self, rental_charge):
        return round(rental_charge * self.INSURANCE_RATE)
