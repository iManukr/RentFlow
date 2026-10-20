"""RentFlow - entry point.

    python3 main.py          runs the full demo
    python3 main.py --menu   runs the interactive terminal menu
"""

import sys

from customer import Customer
from payment import CardPayment, CashPayment, MpesaPayment
from rental_system import CarRentalSystem
from vehicle import EconomyCar, LuxuryCar, SUV


def banner(text):
    print()
    print("#" * 60)
    print(f"# {text}")
    print("#" * 60)


def build_system():
    """Create the system and load the sample data (6 vehicles, 3 customers)."""
    system = CarRentalSystem("SafariDrive Rentals")

    fleet = [
        EconomyCar("KDK 123A", "Toyota", "Axio", 2022, 4000),
        EconomyCar("KCZ 908A", "Mazda", "Demio", 2020, 3500),
        SUV("KDJ 456B", "Toyota", "Prado", 2023, 8000),
        SUV("KDJ 672B", "Nissan", "X-Trail", 2021, 6500),
        LuxuryCar("KDL 789C", "Mercedes-Benz", "E-Class", 2024, 15000),
        LuxuryCar("KDM 112D", "BMW", "5 Series", 2023, 13000),
    ]
    for vehicle in fleet:
        system.add_vehicle(vehicle)

    for customer in [
        Customer("C001", "John Kamau", "0712345678", "12345678", "DL45821"),
        Customer("C002", "Mary Wanjiku", "0723456789", "23456789", "DL77193"),
        Customer("C003", "Peter Otieno", "0734567890", "34567890", "DL30412"),
    ]:
        system.register_customer(customer)

    return system


# ----------------------------------------------------------------------
# The demo
# ----------------------------------------------------------------------

def demo():
    system = build_system()

    banner("1. THE FLEET (abstraction and inheritance)")
    for vehicle in system.vehicles:
        vehicle.display_details()

    print("\nA plain Vehicle cannot be created - it is abstract:")
    try:
        from vehicle import Vehicle
        Vehicle("KAA 000A", "Generic", "Car", 2020, 1000)
    except TypeError as error:
        print(f"  TypeError: {error}")

    banner("2. POLYMORPHISM - the same call, three different prices")
    axio = system.find_vehicle("KDK 123A")
    prado = system.find_vehicle("KDJ 456B")
    mercedes = system.find_vehicle("KDL 789C")
    for car in [axio, prado, mercedes]:
        print(f"  {car.CATEGORY:<8} {car.full_name:<22} 3 days = "
              f"KSh {car.calculate_rental_cost(3):>7,}")

    banner("3. THE DRIVING-LICENCE RULE")
    try:
        Customer("C004", "Grace Njeri", "0745678901", "45678901", "")
    except ValueError as error:
        print(f"  Error: {error}")

    banner("4. SEARCHING THE FLEET")
    system.show_available_vehicles()
    system.search_vehicles(vehicle_type="SUV")
    system.search_vehicles(vehicle_type="SUV", max_daily_rate=7000)

    banner("5. RENTAL R001 - John rents the Prado, returns it 2 days late")
    john = system.find_customer("C001")
    rental1 = system.rent_vehicle(john, prado, 4)
    print()
    rental1.display_rental_details()

    print("\nTrying to rent the same Prado again:")
    try:
        system.rent_vehicle(john, prado, 2)
    except ValueError as error:
        print(f"  Error: {error}")

    print()
    system.return_vehicle(rental1, actual_days=6)
    print()
    payment1 = MpesaPayment(rental1, john.phone_number)
    system.process_payment(payment1)
    print()
    rental1.display_rental_details()

    banner("6. RENTAL R002 - Mary rents the Axio, returns it with a scratch")
    mary = system.find_customer("C002")
    rental2 = system.rent_vehicle(mary, axio, 3)
    print()
    system.return_vehicle(rental2, actual_days=3, damage_charge=1500)
    print()
    system.process_payment(CardPayment(rental2, "4417"))
    print()
    rental2.display_rental_details()

    banner("7. RENTAL R003 - Peter pays cash, but not enough at first")
    peter = system.find_customer("C003")
    rental3 = system.rent_vehicle(peter, mercedes, 2)
    print()
    system.return_vehicle(rental3, actual_days=2)
    print()
    system.process_payment(CashPayment(rental3, 30000))
    print()
    system.process_payment(CashPayment(rental3, 35000))

    print("\nTrying to pay rental R003 a second time:")
    try:
        system.process_payment(CashPayment(rental3, 35000))
    except ValueError as error:
        print(f"  Error: {error}")

    banner("8. RENTAL R004 - cancelled, then the car goes for service")
    xtrail = system.find_vehicle("KDJ 672B")
    rental4 = system.rent_vehicle(mary, xtrail, 5)
    system.cancel_rental(rental4)
    xtrail.send_for_maintenance()
    print(f"{xtrail.full_name} status: {xtrail.status}")
    print("\nTrying to rent a car that is under maintenance:")
    try:
        system.rent_vehicle(mary, xtrail, 2)
    except ValueError as error:
        print(f"  Error: {error}")
    xtrail.return_from_maintenance()
    print(f"{xtrail.full_name} is back: {xtrail.status}")

    banner("9. THE OTHER BUSINESS RULES")
    checks = [
        ("Negative daily rate",
         lambda: EconomyCar("KBB 001A", "Toyota", "Vitz", 2019, -500)),
        ("Unregistered customer rents",
         lambda: system.rent_vehicle(
             Customer("C099", "Walk-in", "0700000000", "99999999", "DL99999"),
             axio, 2)),
        ("Vehicle not in the fleet",
         lambda: system.rent_vehicle(
             john, EconomyCar("KXX 999X", "Suzuki", "Alto", 2018, 3000), 2)),
        ("Zero rental days", lambda: system.rent_vehicle(john, axio, 0)),
        ("Returning a car that is not out",
         lambda: system.return_vehicle(rental2, actual_days=2)),
        ("Completing a finished rental",
         lambda: rental1.complete_rental(7)),
        ("Paying before the car comes back",
         lambda: MpesaPayment(
             system.rent_vehicle(john, axio, 2), john.phone_number)),
    ]
    for label, action in checks:
        try:
            action()
            print(f"  {label:<34} -> no error (check this!)")
        except (ValueError, TypeError) as error:
            print(f"  {label:<34} -> {type(error).__name__}: {error}")

    banner("10. ENCAPSULATION - revenue cannot be faked")
    print(f"  Real revenue:            KSh {system.revenue:,}")
    system.__revenue = 10_000_000          # creates an unrelated attribute
    print(f"  After system.__revenue = 10,000,000: KSh {system.revenue:,}")
    try:
        system.revenue = 10_000_000        # the property has no setter
    except AttributeError as error:
        print(f"  system.revenue = ... -> AttributeError: {error}")

    banner("11. HISTORY AND LISTINGS")
    for customer in system.customers:
        customer.view_rental_history()
    system.show_active_rentals()
    system.show_completed_rentals()

    banner("12. MANAGEMENT REPORT")
    system.generate_report()


# ----------------------------------------------------------------------
# The interactive menu (bonus)
# ----------------------------------------------------------------------

MENU = """
================================
     SAFARIDRIVE RENTALS
================================
1. Register Customer
2. Add Vehicle
3. View Available Vehicles
4. Rent Vehicle
5. Return Vehicle
6. Process Payment
7. View Active Rentals
8. View Completed Rentals
9. Generate Management Report
10. Exit
"""


def ask_int(prompt, minimum=0):
    while True:
        try:
            value = int(input(prompt).strip())
        except ValueError:
            print("  Please type a whole number.")
            continue
        if value < minimum:
            print(f"  Please type a number of at least {minimum}.")
            continue
        return value


def menu_register_customer(system):
    customer = Customer(
        input("Customer ID (blank for automatic): ").strip() or None,
        input("Name: ").strip(),
        input("Phone number: ").strip(),
        input("National ID: ").strip(),
        input("Driving licence: ").strip(),
    )
    system.register_customer(customer)
    print(f"Registered {customer}.")


def menu_add_vehicle(system):
    types = {"1": EconomyCar, "2": SUV, "3": LuxuryCar}
    choice = input("Type - 1 Economy, 2 SUV, 3 Luxury: ").strip()
    if choice not in types:
        raise ValueError("Pick 1, 2 or 3.")
    vehicle = types[choice](
        input("Registration number: ").strip(),
        input("Make: ").strip(),
        input("Model: ").strip(),
        ask_int("Year: ", minimum=1900),
        ask_int("Daily rate (KSh): "),
    )
    system.add_vehicle(vehicle)
    print(f"Added {vehicle}.")


def menu_rent_vehicle(system):
    customer = system.find_customer(input("Customer ID: ").strip())
    if customer is None:
        raise ValueError("No customer with that ID.")
    system.show_available_vehicles()
    vehicle = system.find_vehicle(input("Registration number: ").strip())
    if vehicle is None:
        raise ValueError("No vehicle with that registration number.")
    rental = system.rent_vehicle(customer, vehicle, ask_int("Days: ", 1))
    print()
    rental.display_rental_details()


def menu_return_vehicle(system):
    system.show_active_rentals()
    rental = system.find_rental(input("Rental ID: ").strip())
    if rental is None:
        raise ValueError("No rental with that ID.")
    actual_days = ask_int("Days actually kept: ", 1)
    damage = 0
    if input("Was the vehicle damaged? (y/n): ").strip().lower().startswith("y"):
        damage = ask_int("Damage charge (KSh): ")
    system.return_vehicle(rental, actual_days, damage)
    print()
    rental.display_rental_details()


def menu_process_payment(system):
    unpaid = [r for r in system.completed_rentals() if not r.is_paid()]
    print("\nUNPAID COMPLETED RENTALS")
    if not unpaid:
        print("  None.")
        return
    for rental in unpaid:
        print(f"  {rental.summary()}")
    rental = system.find_rental(input("Rental ID: ").strip())
    if rental is None:
        raise ValueError("No rental with that ID.")

    method = input("Method - 1 M-Pesa, 2 Card, 3 Cash: ").strip()
    if method == "1":
        payment = MpesaPayment(rental, input("Phone number: ").strip())
    elif method == "2":
        payment = CardPayment(rental, input("Last 4 card digits: ").strip())
    elif method == "3":
        print(f"Amount due: KSh {rental.calculate_total():,}")
        payment = CashPayment(rental, ask_int("Cash received (KSh): "))
    else:
        raise ValueError("Pick 1, 2 or 3.")
    system.process_payment(payment)


def run_menu():
    system = build_system()
    print("Sample data loaded: 6 vehicles, 3 customers.")

    actions = {
        "1": menu_register_customer,
        "2": menu_add_vehicle,
        "3": lambda s: s.show_available_vehicles(),
        "4": menu_rent_vehicle,
        "5": menu_return_vehicle,
        "6": menu_process_payment,
        "7": lambda s: s.show_active_rentals(),
        "8": lambda s: s.show_completed_rentals(),
        "9": lambda s: s.generate_report(),
    }

    while True:
        print(MENU)
        try:
            choice = input("Choose an option: ").strip()
            if choice == "10":
                break
            action = actions.get(choice)
            if action is None:
                print("  Please choose a number from 1 to 10.")
                continue
            action(system)
        except (ValueError, TypeError) as error:
            # A broken business rule should never stop the program.
            print(f"  Error: {error}")
        except (EOFError, KeyboardInterrupt):
            break

    print("\nGoodbye.")


if __name__ == "__main__":
    if "--menu" in sys.argv:
        run_menu()
    else:
        demo()
