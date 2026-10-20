"""The Customer class."""


class Customer:
    """Someone who rents from SafariDrive, plus their rental history."""

    _counter = 0

    def __init__(self, customer_id, name, phone_number, national_id,
                 driving_licence):
        if not name:
            raise ValueError("A customer must have a name.")
        if not driving_licence:
            raise ValueError(f"{name} cannot rent without a driving licence.")

        if customer_id is None:          # bonus: automatic IDs (C001, C002...)
            Customer._counter += 1
            customer_id = f"C{Customer._counter:03d}"

        self.customer_id = customer_id
        self.name = name
        self.phone_number = phone_number
        self.national_id = national_id
        self.driving_licence = driving_licence
        self.rentals = []                # list of this customer's Rental objects

    def add_rental(self, rental):
        self.rentals.append(rental)

    def active_rentals(self):
        return [r for r in self.rentals if r.status == "ACTIVE"]

    def total_spent(self):
        return sum(r.calculate_total() for r in self.rentals
                   if r.status == "COMPLETED" and r.is_paid())

    def display_details(self):
        print(f"{self.customer_id}  {self.name}")
        print(f"  Phone: {self.phone_number}    National ID: {self.national_id}")
        print(f"  Licence: {self.driving_licence}    "
              f"Rentals: {len(self.rentals)}")

    def view_rental_history(self):
        print(f"\nRENTAL HISTORY - {self.name} ({self.customer_id})")
        if not self.rentals:
            print("  No rentals yet.")
            return
        for rental in self.rentals:
            days = rental.actual_days or rental.rental_days
            print(f"  {rental.rental_id}  {rental.vehicle.full_name:<22} "
                  f"{days} day(s)  KSh {rental.calculate_total():>8,}  "
                  f"{rental.status}"
                  f"{'  (PAID)' if rental.is_paid() else ''}")

    def __str__(self):
        return f"{self.name} ({self.customer_id})"
