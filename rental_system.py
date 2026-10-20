"""CarRentalSystem: the manager that holds the lists and enforces the rules."""

from exceptions import (
    AlreadyPaidError,
    InvalidRentalPeriodError,
    NotRegisteredError,
    PaymentError,
    RentalNotCompletedError,
    VehicleNotAvailableError,
    VehicleNotRentedError,
)
from rental import Rental
from vehicle import EconomyCar, LuxuryCar, SUV, Vehicle

REPORT_WIDTH = 37

# Accepted spellings for search_vehicles(vehicle_type=...)
VEHICLE_TYPES = {
    "economy": EconomyCar,
    "economycar": EconomyCar,
    "economy car": EconomyCar,
    "suv": SUV,
    "luxury": LuxuryCar,
    "luxurycar": LuxuryCar,
    "luxury car": LuxuryCar,
}


class CarRentalSystem:
    """Runs the business: the fleet, the customers, the rentals, the money."""

    def __init__(self, name="SafariDrive Rentals"):
        self.name = name
        self.vehicles = []
        self.customers = []
        self.rentals = []
        self.payments = []
        self.__revenue = 0               # private: encapsulation

    # --- revenue is read-only from outside ------------------------------

    @property
    def revenue(self):
        """Total money taken. Read-only: only process_payment() adds to it."""
        return self.__revenue

    # --- registration ----------------------------------------------------

    def add_vehicle(self, vehicle):
        if not isinstance(vehicle, Vehicle):
            raise TypeError("Only Vehicle objects can join the fleet.")
        if self.find_vehicle(vehicle.registration_number):
            raise NotRegisteredError(
                f"{vehicle.registration_number} is already in the fleet."
            )
        self.vehicles.append(vehicle)
        return vehicle

    def register_customer(self, customer):
        if self.find_customer(customer.customer_id):
            raise NotRegisteredError(
                f"Customer {customer.customer_id} is already registered."
            )
        self.customers.append(customer)
        return customer

    def find_vehicle(self, registration_number):
        for vehicle in self.vehicles:
            if vehicle.registration_number == registration_number:
                return vehicle
        return None

    def find_customer(self, customer_id):
        for customer in self.customers:
            if customer.customer_id == customer_id:
                return customer
        return None

    def find_rental(self, rental_id):
        for rental in self.rentals:
            if rental.rental_id == rental_id:
                return rental
        return None

    # --- browsing the fleet ----------------------------------------------

    def available_vehicles(self):
        return [v for v in self.vehicles if v.is_available()]

    def rented_vehicles(self):
        return [v for v in self.vehicles if v.is_rented()]

    def show_available_vehicles(self):
        return self.search_vehicles()

    def search_vehicles(self, vehicle_type=None, max_daily_rate=None):
        """List the available vehicles, optionally filtered by type and price."""
        matches = self.available_vehicles()
        heading = "VEHICLES"

        if vehicle_type is not None:
            wanted = VEHICLE_TYPES.get(str(vehicle_type).strip().lower())
            if wanted is None:
                raise ValueError(
                    f"Unknown vehicle type '{vehicle_type}'. "
                    "Try Economy, SUV or Luxury."
                )
            matches = [v for v in matches if isinstance(v, wanted)]
            heading = wanted.PLURAL

        if max_daily_rate is not None:
            matches = [v for v in matches if v.daily_rate <= max_daily_rate]

        print(f"\nAVAILABLE {heading}")
        if max_daily_rate is not None:
            print(f"(up to KSh {max_daily_rate:,}/day)")
        print()
        if not matches:
            print("No vehicles match that search.")
            return matches

        for number, vehicle in enumerate(matches, start=1):
            print(f"{number}. {vehicle.full_name}")
            print(f"   Registration: {vehicle.registration_number}")
            print(f"   Rate: KSh {vehicle.daily_rate:,}/day")
            print()
        return matches

    # --- renting and returning -------------------------------------------

    def rent_vehicle(self, customer, vehicle, days):
        """Check every rule, then create the rental and take the car off the lot."""
        if customer not in self.customers:
            raise NotRegisteredError(
                f"{customer.name} must be registered before renting."
            )
        if vehicle not in self.vehicles:
            raise NotRegisteredError(
                f"{vehicle.registration_number} is not in the fleet."
            )
        if days <= 0:
            raise InvalidRentalPeriodError(
                "Rental days must be greater than zero."
            )
        if not vehicle.is_available():
            raise VehicleNotAvailableError(
                f"{vehicle.full_name} ({vehicle.registration_number}) is "
                f"{vehicle.status} and cannot be rented."
            )

        rental = Rental(customer, vehicle, days)
        vehicle.mark_as_rented()
        customer.add_rental(rental)
        self.rentals.append(rental)
        print(f"{vehicle.full_name} rented to {customer.name} for "
              f"{days} day(s). Bill so far: KSh {rental.base_cost:,}")
        return rental

    def return_vehicle(self, rental, actual_days, damage_charge=0):
        """Close the rental, add late and damage charges, free the vehicle."""
        if rental not in self.rentals:
            raise NotRegisteredError(
                f"Rental {rental.rental_id} is not known to {self.name}."
            )
        if not rental.vehicle.is_rented():
            raise VehicleNotRentedError(
                f"{rental.vehicle.registration_number} is not out on rental, "
                "so it cannot be returned."
            )

        total = rental.complete_rental(actual_days, damage_charge)
        rental.vehicle.mark_as_available()
        print(f"{rental.vehicle.full_name} returned after {actual_days} day(s).")
        if rental.late_fee:
            print(f"  Late by {rental.late_days()} day(s): "
                  f"late fee KSh {rental.late_fee:,}")
        if rental.damage_charge:
            print(f"  Damage charge: KSh {rental.damage_charge:,}")
        print(f"  Amount due: KSh {total:,}")
        return rental

    def cancel_rental(self, rental):
        """Bonus: drop an active rental and put the car back on the lot."""
        if rental not in self.rentals:
            raise NotRegisteredError(
                f"Rental {rental.rental_id} is not known to {self.name}."
            )
        rental.cancel()
        rental.vehicle.mark_as_available()
        print(f"Rental {rental.rental_id} cancelled; "
              f"{rental.vehicle.full_name} is available again.")
        return rental

    # --- money -----------------------------------------------------------

    def process_payment(self, payment):
        """Run the payment. Revenue only moves if the payment succeeds."""
        rental = payment.rental
        if rental not in self.rentals:
            raise NotRegisteredError(
                f"Rental {rental.rental_id} is not known to {self.name}."
            )
        if rental.status != "COMPLETED":
            raise RentalNotCompletedError(
                f"Rental {rental.rental_id} is {rental.status}; pay it after "
                "the vehicle is returned."
            )
        if rental.is_paid():
            raise AlreadyPaidError(
                f"Rental {rental.rental_id} has already been paid."
            )
        if payment.amount < 0:
            raise PaymentError("Payment amounts cannot be negative.")

        succeeded = payment.process_payment()
        if succeeded:
            rental.mark_as_paid()
            self.__revenue += payment.amount
            self.payments.append(payment)
        else:
            print(f"Rental {rental.rental_id} is still unpaid.")
        return succeeded

    # --- listings ---------------------------------------------------------

    def active_rentals(self):
        return [r for r in self.rentals if r.status == "ACTIVE"]

    def completed_rentals(self):
        return [r for r in self.rentals if r.status == "COMPLETED"]

    def cancelled_rentals(self):
        return [r for r in self.rentals if r.status == "CANCELLED"]

    def show_active_rentals(self):
        return self.__show_rentals("ACTIVE RENTALS", self.active_rentals())

    def show_completed_rentals(self):
        return self.__show_rentals("COMPLETED RENTALS",
                                   self.completed_rentals())

    def __show_rentals(self, heading, rentals):
        print(f"\n{heading}")
        if not rentals:
            print("  None.")
            return rentals
        for rental in rentals:
            print(f"  {rental.summary()}")
        return rentals

    # --- the report --------------------------------------------------------

    def generate_report(self):
        """Every figure here is counted from the objects in the lists."""
        economy = [v for v in self.vehicles if isinstance(v, EconomyCar)]
        suvs = [v for v in self.vehicles if isinstance(v, SUV)]
        luxury = [v for v in self.vehicles if isinstance(v, LuxuryCar)]
        maintenance = [v for v in self.vehicles if v.status == "MAINTENANCE"]

        print()
        print("=" * REPORT_WIDTH)
        title = f"{self.name.split()[0].upper()} MANAGEMENT REPORT"
        print(title.center(REPORT_WIDTH).rstrip())
        print("=" * REPORT_WIDTH)
        self.__count("Total Vehicles:", len(self.vehicles))
        self.__count("Available Vehicles:", len(self.available_vehicles()))
        self.__count("Rented Vehicles:", len(self.rented_vehicles()))
        if maintenance:
            self.__count("Under Maintenance:", len(maintenance))
        print()
        self.__count("Registered Customers:", len(self.customers))
        print()
        self.__count("Total Rentals:", len(self.rentals))
        self.__count("Active Rentals:", len(self.active_rentals()))
        self.__count("Completed Rentals:", len(self.completed_rentals()))
        if self.cancelled_rentals():
            self.__count("Cancelled Rentals:", len(self.cancelled_rentals()))
        print()
        print(f"{'Total Revenue:':<20}{'KSh ' + format(self.revenue, ','):>11}")
        print("-" * REPORT_WIDTH)
        print("VEHICLES BY CATEGORY")
        self.__count("Economy Cars:", len(economy))
        self.__count("SUVs:", len(suvs))
        self.__count("Luxury Cars:", len(luxury))
        print("=" * REPORT_WIDTH)

    @staticmethod
    def __count(label, value):
        print(f"{label:<22}{value:>9}")

    def __str__(self):
        return (f"{self.name}: {len(self.vehicles)} vehicles, "
                f"{len(self.customers)} customers, "
                f"KSh {self.revenue:,} revenue")
