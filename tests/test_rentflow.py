"""Tests for RentFlow.

Run from the project folder:

    python3 -m unittest discover -s tests -t .

The numbers checked here are the worked examples from the project brief, so a
passing run means the pricing, the late fee and the ten business rules all
behave as specified.
"""

import io
import unittest
from contextlib import redirect_stdout

from customer import Customer
from exceptions import (
    AlreadyPaidError,
    InvalidRentalPeriodError,
    NotRegisteredError,
    PaymentError,
    RentalAlreadyCompletedError,
    RentalNotCompletedError,
    VehicleNotAvailableError,
    VehicleNotRentedError,
)
from payment import CardPayment, CashPayment, MpesaPayment, Payment
from rental import Rental
from rental_system import CarRentalSystem
from vehicle import EconomyCar, LuxuryCar, SUV, Vehicle


def quiet(function, *args, **kwargs):
    """Call `function` with its printing swallowed, and return its result."""
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def output_of(function, *args, **kwargs):
    """Call `function` and return what it printed."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        function(*args, **kwargs)
    return buffer.getvalue()


class VehicleTests(unittest.TestCase):
    """Part 1 and Part 2: abstraction, inheritance and polymorphism."""

    def test_vehicle_is_abstract(self):
        with self.assertRaises(TypeError):
            Vehicle("KDK 123A", "Toyota", "Axio", 2022, 4000)

    def test_economy_cost_is_rate_times_days(self):
        axio = EconomyCar("KDK 123A", "Toyota", "Axio", 2022, 4000)
        self.assertEqual(axio.calculate_rental_cost(3), 12_000)

    def test_suv_adds_one_service_charge(self):
        prado = SUV("KDJ 456B", "Toyota", "Prado", 2023, 8000)
        self.assertEqual(prado.calculate_rental_cost(3), 26_000)
        self.assertEqual(prado.calculate_rental_cost(1), 10_000)

    def test_luxury_adds_ten_percent_insurance(self):
        mercedes = LuxuryCar("KDL 789C", "Mercedes-Benz", "E-Class", 2024, 15000)
        self.assertEqual(mercedes.calculate_rental_cost(3), 49_500)

    def test_same_call_three_different_prices(self):
        fleet = [
            EconomyCar("KDK 123A", "Toyota", "Axio", 2022, 4000),
            SUV("KDJ 456B", "Toyota", "Prado", 2023, 8000),
            LuxuryCar("KDL 789C", "Mercedes-Benz", "E-Class", 2024, 15000),
        ]
        costs = [car.calculate_rental_cost(3) for car in fleet]
        self.assertEqual(costs, [12_000, 26_000, 49_500])

    def test_negative_daily_rate_rejected(self):
        with self.assertRaises(ValueError):
            EconomyCar("KBB 001A", "Toyota", "Vitz", 2019, -500)

    def test_availability_only_changes_through_methods(self):
        axio = EconomyCar("KDK 123A", "Toyota", "Axio", 2022, 4000)
        self.assertTrue(axio.is_available())

        axio._Vehicle__available = axio._Vehicle__available  # no public setter
        axio.mark_as_rented()
        self.assertFalse(axio.is_available())
        self.assertEqual(axio.status, "RENTED")

        with self.assertRaises(VehicleNotAvailableError):
            axio.mark_as_rented()

        axio.mark_as_available()
        self.assertTrue(axio.is_available())

    def test_maintenance_blocks_renting(self):
        axio = EconomyCar("KDK 123A", "Toyota", "Axio", 2022, 4000)
        axio.send_for_maintenance()
        self.assertFalse(axio.is_available())
        self.assertEqual(axio.status, "MAINTENANCE")
        axio.return_from_maintenance()
        self.assertTrue(axio.is_available())


class CustomerTests(unittest.TestCase):
    """Part 3."""

    def test_driving_licence_is_required(self):
        with self.assertRaises(ValueError):
            Customer("C004", "Grace Njeri", "0745678901", "45678901", "")

    def test_automatic_ids(self):
        first = Customer(None, "A", "0700000001", "1", "DL1")
        second = Customer(None, "B", "0700000002", "2", "DL2")
        self.assertRegex(first.customer_id, r"^C\d{3}$")
        self.assertNotEqual(first.customer_id, second.customer_id)

    def test_rental_history_grows(self):
        customer = Customer("C001", "John Kamau", "0712345678", "1", "DL45821")
        self.assertEqual(customer.rentals, [])
        axio = EconomyCar("KDK 123A", "Toyota", "Axio", 2022, 4000)
        customer.add_rental(Rental(customer, axio, 2))
        self.assertEqual(len(customer.rentals), 1)


class RentalTests(unittest.TestCase):
    """Part 4: the bill and the lifecycle."""

    def setUp(self):
        self.customer = Customer("C001", "John Kamau", "0712345678", "1",
                                 "DL45821")
        self.prado = SUV("KDJ 456B", "Toyota", "Prado", 2023, 8000)
        self.rental = Rental(self.customer, self.prado, 4)

    def test_base_cost_comes_from_the_vehicle(self):
        self.assertEqual(self.rental.base_cost, 34_000)
        self.assertEqual(self.rental.status, "ACTIVE")
        self.assertFalse(self.rental.is_paid())

    def test_late_fee_worked_example(self):
        """Brief: 4 days agreed, 6 kept, Prado at 8,000 -> KSh 3,200 late fee."""
        self.rental.complete_rental(actual_days=6)
        self.assertEqual(self.rental.late_days(), 2)
        self.assertEqual(self.rental.late_fee, 3_200)
        self.assertEqual(self.rental.calculate_total(), 37_200)

    def test_no_late_fee_when_early_or_on_time(self):
        self.rental.complete_rental(actual_days=3)
        self.assertEqual(self.rental.late_fee, 0)
        self.assertEqual(self.rental.calculate_total(), 34_000)

    def test_late_fee_ignores_service_charge_and_insurance(self):
        mercedes = LuxuryCar("KDL 789C", "Mercedes-Benz", "E-Class", 2024, 15000)
        rental = Rental(self.customer, mercedes, 2)
        rental.complete_rental(actual_days=3)
        self.assertEqual(rental.late_fee, 3_000)          # 20% of 15,000 x 1
        self.assertEqual(rental.calculate_total(), 36_000)  # 33,000 + 3,000

    def test_damage_charge_is_added(self):
        self.rental.complete_rental(actual_days=4, damage_charge=1_500)
        self.assertEqual(self.rental.calculate_total(), 35_500)

    def test_zero_days_rejected(self):
        with self.assertRaises(InvalidRentalPeriodError):
            Rental(self.customer, self.prado, 0)

    def test_negative_damage_charge_rejected(self):
        with self.assertRaises(ValueError):
            self.rental.complete_rental(actual_days=4, damage_charge=-100)

    def test_cannot_complete_twice(self):
        self.rental.complete_rental(actual_days=4)
        with self.assertRaises(RentalAlreadyCompletedError):
            self.rental.complete_rental(actual_days=5)

    def test_cannot_pay_before_completion(self):
        with self.assertRaises(RentalNotCompletedError):
            self.rental.mark_as_paid()

    def test_cannot_pay_twice(self):
        self.rental.complete_rental(actual_days=4)
        self.rental.mark_as_paid()
        with self.assertRaises(AlreadyPaidError):
            self.rental.mark_as_paid()

    def test_cancelled_rental_cannot_be_returned(self):
        self.rental.cancel()
        self.assertEqual(self.rental.status, "CANCELLED")
        with self.assertRaises(ValueError):
            self.rental.complete_rental(actual_days=2)

    def test_receipt_shows_the_charges(self):
        self.rental.complete_rental(actual_days=6)
        receipt = output_of(self.rental.display_rental_details)
        self.assertIn("SAFARIDRIVE RENTALS", receipt)
        self.assertIn("Service Charge:", receipt)
        self.assertIn("Late Fee (2 days):", receipt)
        self.assertIn("37,200", receipt)


class PaymentTests(unittest.TestCase):
    """Part 5: polymorphic payments."""

    def setUp(self):
        self.customer = Customer("C001", "John Kamau", "0712345678", "1",
                                 "DL45821")
        self.prado = SUV("KDJ 456B", "Toyota", "Prado", 2023, 8000)
        self.rental = Rental(self.customer, self.prado, 4)
        self.rental.complete_rental(actual_days=6)      # bill is KSh 37,200

    def test_payment_is_abstract(self):
        with self.assertRaises(TypeError):
            Payment(self.rental)

    def test_amount_is_taken_from_the_rental(self):
        payment = MpesaPayment(self.rental, "0712345678")
        self.assertEqual(payment.amount, 37_200)

    def test_mpesa_generates_a_transaction_code(self):
        payment = MpesaPayment(self.rental, "0712345678")
        self.assertTrue(quiet(payment.process_payment))
        self.assertRegex(payment.transaction_code, r"^[A-Z0-9]{10}$")
        self.assertTrue(payment.was_successful())

    def test_card_stores_only_four_digits(self):
        payment = CardPayment(self.rental, "4417")
        self.assertEqual(payment.card_last_four, "4417")
        self.assertIn("Card ending 4417", output_of(payment.process_payment))
        with self.assertRaises(PaymentError):
            CardPayment(self.rental, "4111111111114417")

    def test_cash_fails_when_short(self):
        payment = CashPayment(self.rental, 30_000)
        self.assertFalse(quiet(payment.process_payment))
        self.assertFalse(payment.was_successful())

    def test_cash_gives_change(self):
        payment = CashPayment(self.rental, 40_000)
        self.assertTrue(quiet(payment.process_payment))
        self.assertEqual(payment.change_due, 2_800)

    def test_every_payment_type_answers_the_same_call(self):
        payments = [
            MpesaPayment(self.rental, "0712345678"),
            CardPayment(self.rental, "4417"),
            CashPayment(self.rental, 40_000),
        ]
        self.assertTrue(all(quiet(p.process_payment) for p in payments))

    def test_payment_needs_a_completed_rental(self):
        active = Rental(self.customer, SUV("KDJ 672B", "Nissan", "X-Trail",
                                           2021, 6500), 2)
        with self.assertRaises(RentalNotCompletedError):
            MpesaPayment(active, "0712345678")

    def test_negative_cash_rejected(self):
        with self.assertRaises(PaymentError):
            CashPayment(self.rental, -100)


class SystemTests(unittest.TestCase):
    """Part 6 to Part 9: the rules, the revenue and the report."""

    def setUp(self):
        self.system = CarRentalSystem("SafariDrive Rentals")
        self.axio = EconomyCar("KDK 123A", "Toyota", "Axio", 2022, 4000)
        self.prado = SUV("KDJ 456B", "Toyota", "Prado", 2023, 8000)
        self.xtrail = SUV("KDJ 672B", "Nissan", "X-Trail", 2021, 6500)
        self.mercedes = LuxuryCar("KDL 789C", "Mercedes-Benz", "E-Class",
                                  2024, 15000)
        for vehicle in [self.axio, self.prado, self.xtrail, self.mercedes]:
            self.system.add_vehicle(vehicle)
        self.john = Customer("C001", "John Kamau", "0712345678", "12345678",
                             "DL45821")
        self.system.register_customer(self.john)

    # --- lookups and search ---------------------------------------------

    def test_find_vehicle_and_customer(self):
        self.assertIs(self.system.find_vehicle("KDJ 456B"), self.prado)
        self.assertIsNone(self.system.find_vehicle("KZZ 000Z"))
        self.assertIs(self.system.find_customer("C001"), self.john)
        self.assertIsNone(self.system.find_customer("C999"))

    def test_search_by_type(self):
        found = quiet(self.system.search_vehicles, vehicle_type="SUV")
        self.assertEqual(found, [self.prado, self.xtrail])

    def test_search_by_type_and_budget(self):
        found = quiet(self.system.search_vehicles,
                      vehicle_type="SUV", max_daily_rate=7000)
        self.assertEqual(found, [self.xtrail])

    def test_unknown_search_type_rejected(self):
        with self.assertRaises(ValueError):
            quiet(self.system.search_vehicles, vehicle_type="Lorry")

    def test_rented_vehicle_leaves_the_available_list(self):
        quiet(self.system.rent_vehicle, self.john, self.prado, 4)
        self.assertNotIn(self.prado, self.system.available_vehicles())
        self.assertIn(self.prado, self.system.rented_vehicles())

    def test_duplicate_registration_rejected(self):
        with self.assertRaises(NotRegisteredError):
            self.system.add_vehicle(
                SUV("KDJ 456B", "Toyota", "Prado", 2023, 8000))

    def test_only_vehicles_join_the_fleet(self):
        with self.assertRaises(TypeError):
            self.system.add_vehicle("a car, honestly")

    # --- the ten business rules ------------------------------------------

    def test_rule_3_customer_must_be_registered(self):
        walk_in = Customer("C099", "Walk-in", "0700000000", "9", "DL99999")
        with self.assertRaises(NotRegisteredError):
            quiet(self.system.rent_vehicle, walk_in, self.axio, 2)

    def test_rule_4_vehicle_must_be_in_the_fleet(self):
        stranger = EconomyCar("KXX 999X", "Suzuki", "Alto", 2018, 3000)
        with self.assertRaises(NotRegisteredError):
            quiet(self.system.rent_vehicle, self.john, stranger, 2)

    def test_rule_5_days_must_be_positive(self):
        with self.assertRaises(InvalidRentalPeriodError):
            quiet(self.system.rent_vehicle, self.john, self.axio, 0)
        self.assertTrue(self.axio.is_available())   # nothing was changed

    def test_rule_6_no_double_booking(self):
        quiet(self.system.rent_vehicle, self.john, self.prado, 4)
        with self.assertRaises(VehicleNotAvailableError):
            quiet(self.system.rent_vehicle, self.john, self.prado, 2)
        self.assertEqual(len(self.system.rentals), 1)

    def test_rule_7_cannot_return_a_car_that_is_not_out(self):
        rental = quiet(self.system.rent_vehicle, self.john, self.prado, 4)
        quiet(self.system.return_vehicle, rental, 4)
        with self.assertRaises(VehicleNotRentedError):
            quiet(self.system.return_vehicle, rental, 4)

    def test_rule_10_payment_once_and_only_after_return(self):
        rental = quiet(self.system.rent_vehicle, self.john, self.prado, 4)
        with self.assertRaises(RentalNotCompletedError):
            MpesaPayment(rental, self.john.phone_number)

        quiet(self.system.return_vehicle, rental, 6)
        quiet(self.system.process_payment,
              MpesaPayment(rental, self.john.phone_number))
        self.assertTrue(rental.is_paid())

        with self.assertRaises(AlreadyPaidError):
            quiet(self.system.process_payment,
                  MpesaPayment(rental, self.john.phone_number))

    # --- returning, cancelling, revenue -----------------------------------

    def test_return_frees_the_vehicle_and_closes_the_rental(self):
        rental = quiet(self.system.rent_vehicle, self.john, self.prado, 4)
        quiet(self.system.return_vehicle, rental, 6)
        self.assertEqual(rental.status, "COMPLETED")
        self.assertTrue(self.prado.is_available())
        self.assertEqual(rental.calculate_total(), 37_200)

    def test_cancelling_frees_the_vehicle(self):
        rental = quiet(self.system.rent_vehicle, self.john, self.xtrail, 5)
        quiet(self.system.cancel_rental, rental)
        self.assertEqual(rental.status, "CANCELLED")
        self.assertTrue(self.xtrail.is_available())
        self.assertEqual(self.system.active_rentals(), [])

    def test_revenue_only_moves_on_a_successful_payment(self):
        rental = quiet(self.system.rent_vehicle, self.john, self.prado, 4)
        quiet(self.system.return_vehicle, rental, 6)

        self.assertFalse(quiet(self.system.process_payment,
                               CashPayment(rental, 10_000)))
        self.assertEqual(self.system.revenue, 0)
        self.assertFalse(rental.is_paid())
        self.assertEqual(self.system.payments, [])

        self.assertTrue(quiet(self.system.process_payment,
                              CashPayment(rental, 40_000)))
        self.assertEqual(self.system.revenue, 37_200)
        self.assertEqual(len(self.system.payments), 1)

    def test_revenue_is_read_only(self):
        with self.assertRaises(AttributeError):
            self.system.revenue = 10_000_000

    def test_faking_the_private_attribute_does_not_work(self):
        self.system.__revenue = 10_000_000      # a new, unrelated attribute
        self.assertEqual(self.system.revenue, 0)

    # --- the report --------------------------------------------------------

    def test_report_counts_come_from_the_lists(self):
        rental = quiet(self.system.rent_vehicle, self.john, self.prado, 4)
        quiet(self.system.return_vehicle, rental, 6)
        quiet(self.system.process_payment,
              MpesaPayment(rental, self.john.phone_number))
        quiet(self.system.rent_vehicle, self.john, self.mercedes, 2)

        report = output_of(self.system.generate_report)
        figures = dict(
            line.rsplit(None, 1) for line in report.splitlines()
            if line.endswith(tuple("0123456789")) and ":" in line
        )
        figures = {label.strip(): value for label, value in figures.items()}

        self.assertEqual(figures["Total Vehicles:"], "4")
        self.assertEqual(figures["Available Vehicles:"], "3")
        self.assertEqual(figures["Rented Vehicles:"], "1")
        self.assertEqual(figures["Registered Customers:"], "1")
        self.assertEqual(figures["Total Rentals:"], "2")
        self.assertEqual(figures["Active Rentals:"], "1")
        self.assertEqual(figures["Completed Rentals:"], "1")
        self.assertEqual(figures["Economy Cars:"], "1")
        self.assertEqual(figures["SUVs:"], "2")
        self.assertEqual(figures["Luxury Cars:"], "1")
        self.assertIn("KSh 37,200", report)

    def test_full_workflow(self):
        """Part 9: register, search, rent, return, pay, report."""
        mary = Customer(None, "Mary Wanjiku", "0723456789", "2", "DL77193")
        self.system.register_customer(mary)
        choices = quiet(self.system.search_vehicles, vehicle_type="Luxury")
        self.assertIn(self.mercedes, choices)

        rental = quiet(self.system.rent_vehicle, mary, self.mercedes, 3)
        self.assertEqual(rental.base_cost, 49_500)
        quiet(self.system.return_vehicle, rental, 4, 2_000)
        self.assertEqual(rental.calculate_total(), 49_500 + 3_000 + 2_000)
        quiet(self.system.process_payment, CardPayment(rental, "4417"))
        self.assertEqual(self.system.revenue, 54_500)
        self.assertEqual(mary.total_spent(), 54_500)
        self.assertTrue(self.mercedes.is_available())


if __name__ == "__main__":
    unittest.main(verbosity=2)
