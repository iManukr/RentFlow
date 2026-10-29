# RentFlow – Car Rental Management System

A Python OOP system for **SafariDrive Rentals**, a car rental company in Kenya.
RentFlow replaces the notebooks and spreadsheets the company used to track its
fleet, and answers the questions that were previously hard to answer: which
vehicles are free, who has which car, how long it has been out, what the
customer owes, whether the car came back late, and how much the business has
made.

Built as the Python OOP capstone project: abstraction, inheritance,
polymorphism and encapsulation in one working system.

---

## Quick start

No third-party packages are needed, only the standard library.

The project is managed with [uv](https://docs.astral.sh/uv/), so `uv run` picks
the right Python (3.14, pinned in `.python-version`) without activating anything:

```bash
uv sync                                          # create .venv (no dependencies to install)

uv run python main.py                            # the full guided demo
uv run python main.py --menu                     # the interactive terminal menu
uv run python -m unittest discover -s tests -t . # the test suite (52 tests)
```

Plain Python works just as well, since there is nothing to install:

```bash
python3 main.py
python3 main.py --menu
python3 -m unittest discover -s tests -t .
```

---

## Project structure

```text
rentflow/
│
├── main.py            # Demo walkthrough + interactive menu
├── vehicle.py         # Vehicle (abstract), EconomyCar, SUV, LuxuryCar
├── customer.py        # Customer
├── rental.py          # Rental
├── payment.py         # Payment (abstract), MpesaPayment, CardPayment, CashPayment
├── rental_system.py   # CarRentalSystem
├── exceptions.py      # RentFlow's own exception types
│
├── tests/
│   └── test_rentflow.py   # 52 unittest tests
│
├── pyproject.toml     # uv project metadata (no dependencies)
├── .python-version    # pinned interpreter (3.14)
├── sample_output.txt  # Captured output of `python3 main.py`
└── README.md
```

`exceptions.py` is the one addition to the structure in the brief. Every
exception in it inherits from `ValueError`, so calling code can catch the
precise problem (`except VehicleNotAvailableError`) or catch everything with a
plain `except ValueError`.

---

## Class diagram

```text
                      Vehicle  (abstract, ABC)
            registration_number, make, model, year, daily_rate
            __available, __under_maintenance        (private)
            is_available()  mark_as_rented()  mark_as_available()
            calculate_rental_cost(days)             (abstract)
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    EconomyCar                SUV               LuxuryCar
    rate × days        rate × days + 2,000    rate × days + 10%


                      Payment  (abstract, ABC)
                  rental, amount, __successful (private)
                  process_payment()            (abstract)
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
   MpesaPayment          CardPayment           CashPayment
   phone_number          card_last_four        amount_tendered
   transaction code      last 4 digits only    fails if short


   Customer                    Rental                  CarRentalSystem
   customer_id                 rental_id               name
   name, phone_number          customer  ──────────►   vehicles[]
   national_id                 vehicle   ──────────►   customers[]
   driving_licence             rental_days             rentals[]
   rentals[]  ─────────────►   actual_days             payments[]
                               status                  __revenue   (private)
                               base_cost               revenue     (property)
                               late_fee
                               damage_charge
                               __paid      (private)
```

**Relationships**

| From | To | Meaning |
|---|---|---|
| `Rental` | `Customer`, `Vehicle` | One rental links exactly one customer to one vehicle |
| `Customer` | `Rental` | A customer holds a list of their own rentals (history) |
| `Payment` | `Rental` | A payment settles exactly one rental's final bill |
| `CarRentalSystem` | everything | Holds the lists, enforces the rules, owns the revenue |

---

## Pricing rules

| Vehicle type | Cost of a rental |
|---|---|
| `EconomyCar` | `daily_rate × days` |
| `SUV` | `daily_rate × days` + KSh 2,000 service charge (once per rental) |
| `LuxuryCar` | `daily_rate × days` + 10% insurance on that amount |

Worked examples for 3 days, all verified by the test suite:

```text
Economy – Toyota Axio @ 4,000/day      4,000 × 3                 = KSh 12,000
SUV     – Toyota Prado @ 8,000/day     8,000 × 3 + 2,000         = KSh 26,000
Luxury  – Mercedes E-Class @ 15,000    45,000 + 4,500 insurance  = KSh 49,500
```

**Late returns.** The penalty is 20% of the daily rate for every extra day:

```text
John rents the Prado (8,000/day) for 4 days and brings it back after 6.

Late days          = 6 − 4           = 2
Daily late penalty = 20% × 8,000     = KSh 1,600
Late fee           = 1,600 × 2       = KSh 3,200

Base cost (4 days + service charge)  = KSh 34,000
Late fee                             = KSh  3,200
Final bill                           = KSh 37,200
```

The late fee is worked out from the daily rate only. It never adds a second
service charge or a second insurance premium.

---

## The complete workflow

```text
Register Customer → Search Vehicles → Rent (vehicle becomes unavailable)
   → Return (late + damage charges added, vehicle freed)
   → Process Payment (revenue increases only if the payment succeeds)
   → Generate Management Report
```

Payment happens **after** the return, so the customer pays one final bill that
already includes any late and damage charges. That ordering is enforced in
code: creating a `Payment` for a rental that is still `ACTIVE` raises
`RentalNotCompletedError`.

```python
from customer import Customer
from payment import MpesaPayment
from rental_system import CarRentalSystem
from vehicle import SUV

system = CarRentalSystem("SafariDrive Rentals")
prado = system.add_vehicle(SUV("KDJ 456B", "Toyota", "Prado", 2023, 8000))
john = system.register_customer(
    Customer("C001", "John Kamau", "0712345678", "12345678", "DL45821"))

rental = system.rent_vehicle(john, prado, 4)      # Prado is now unavailable
system.return_vehicle(rental, actual_days=6)      # 2 days late -> +3,200
system.process_payment(MpesaPayment(rental, john.phone_number))

print(system.revenue)                             # 37200
```

---

## Business rules enforced

| # | Rule | Exception raised |
|---|---|---|
| 1 | Daily rates cannot be negative | `ValueError` |
| 2 | A customer must have a driving licence | `ValueError` |
| 3 | A customer must be registered before renting | `NotRegisteredError` |
| 4 | A vehicle must be in the fleet before it is rented | `NotRegisteredError` |
| 5 | Rental days must be greater than zero | `InvalidRentalPeriodError` |
| 6 | A rented vehicle cannot be rented again | `VehicleNotAvailableError` |
| 7 | A vehicle cannot be returned unless it is out on rental | `VehicleNotRentedError` |
| 8 | A completed rental cannot be completed again | `RentalAlreadyCompletedError` |
| 9 | Payment amounts cannot be negative | `PaymentError` |
| 10 | A rental is paid once, and only after it is completed | `RentalNotCompletedError`, `AlreadyPaidError` |

Every one of these is raised with a readable message and caught in `main.py`,
so the program explains the problem instead of crashing:

```text
Error: Toyota Prado (KDJ 456B) is RENTED and cannot be rented.
```

---

## How the four pillars of OOP were used

### Abstraction

`Vehicle` and `Payment` are abstract base classes (`abc.ABC`). They declare
*what* every vehicle and every payment must be able to do (a vehicle can work
out the cost of a rental, a payment can take money) without saying *how*.
`calculate_rental_cost(days)` and `process_payment()` are decorated with
`@abstractmethod` and have no implementation at all in the parent. Because of
that, `Vehicle("KDK 123A", "Toyota", "Axio", 2022, 4000)` raises a `TypeError`:
there is no such thing as a generic vehicle in the business, only an economy
car, an SUV or a luxury car, and the code refuses to pretend otherwise. The
rest of the system is written against the abstraction, so `CarRentalSystem`
never needs to know which concrete classes exist.

### Inheritance

`EconomyCar`, `SUV` and `LuxuryCar` inherit everything a vehicle has
(registration number, make, model, year, daily rate, availability tracking,
`display_details()`) and add only what makes them different: a service charge,
an insurance percentage, or nothing at all. The same is true of
`MpesaPayment`, `CardPayment` and `CashPayment`, which inherit the link to the
rental, the amount and the success flag from `Payment`. Each child calls
`super().__init__(...)` so the parent still does the shared setup and
validation, then stores its own extra fields (a phone number, four card digits,
the cash handed over). Adding another vehicle type would mean writing one small
class, not touching the rest of the system.

### Polymorphism

Both hierarchies are used through the parent's interface, never by checking
types. `for car in [axio, prado, mercedes]: car.calculate_rental_cost(3)`
returns 12,000, 26,000 and 49,500: the same call, three different answers,
with no `if` statement deciding which rule applies. `CarRentalSystem.process_payment()`
likewise calls `payment.process_payment()` without caring whether it is M-Pesa,
card or cash; each class prints its own confirmation and returns `True` or
`False`, and the system only adds to revenue when the answer is `True`. The
receipt uses the same idea through `extra_charges()`: the vehicle itself
supplies the right extra line ("Service Charge" or "Insurance (10%)"), so
`Rental` prints a correct receipt without ever asking what kind of car it is
holding.

### Encapsulation

The three pieces of data that must never be edited casually are private.
`Vehicle.__available` and `Vehicle.__under_maintenance` can only change through
`mark_as_rented()`, `mark_as_available()` and the maintenance methods, and
`mark_as_rented()` itself refuses if the car is already out, so double-booking
is impossible even if a caller forgets to check. `Rental.__paid` can only be set
by `mark_as_paid()`, which first insists that the rental is completed and not
already paid. `CarRentalSystem.__revenue` is exposed through a read-only
`@property`, so `print(system.revenue)` works while `system.revenue = 10_000_000`
raises an `AttributeError`, and revenue only ever moves inside
`process_payment()` after a payment has actually succeeded. Writing
`system.__revenue = 10_000_000` from outside quietly creates a new, unrelated
attribute and leaves the real figure untouched. The demo prints both to show this.

---

## The real-world problem this solves

With notebooks and spreadsheets, the same car can be promised to two customers,
late returns get billed as if they were on time, and service charges or
insurance get left off bills.

RentFlow puts those rules in the code:

- A car that is out can't be rented again.
- Late fees are calculated when the car comes back.
- Each vehicle adds its own extra charges to the bill.
- Payment is taken once, after the return.
- The management report counts cars, rentals and revenue from the live objects.
- Card payments store only the last four digits.

---

## Sample data

Loaded by `build_system()` in `main.py`, and used by both the demo and the menu:

**6 vehicles:** Toyota Axio (KDK 123A, 4,000), Mazda Demio (KCZ 908A, 3,500),
Toyota Prado (KDJ 456B, 8,000), Nissan X-Trail (KDJ 672B, 6,500),
Mercedes-Benz E-Class (KDL 789C, 15,000), BMW 5 Series (KDM 112D, 13,000).

**3 customers:** John Kamau (C001), Mary Wanjiku (C002), Peter Otieno (C003).

**5 rentals** created during the demo:

| Rental | Customer | Vehicle | Story | Total |
|---|---|---|---|---|
| R001 | John Kamau | Toyota Prado | 4 days agreed, returned after 6 → late fee | KSh 37,200 |
| R002 | Mary Wanjiku | Toyota Axio | 3 days, returned with a scratch → damage charge | KSh 13,500 |
| R003 | Peter Otieno | Mercedes E-Class | 2 days, paid cash (short the first time) | KSh 33,000 |
| R004 | Mary Wanjiku | Nissan X-Trail | Cancelled, then the car went for service | - |
| R005 | John Kamau | Toyota Axio | Left active, to show payment being refused | KSh 8,000 |

Revenue after the demo: **KSh 83,700** (37,200 + 13,500 + 33,000).

---

## Example output

Full transcript in [`sample_output.txt`](sample_output.txt).

**Rental receipt** (the extra-charge line changes with the vehicle type):

```text
====================================
        SAFARIDRIVE RENTALS
====================================
Rental ID:        R001
Customer:         John Kamau
Vehicle:          Toyota Prado
Registration:     KDJ 456B
Rental Period:    4 days
Daily Rate:       KSh 8,000

Rental Charge:    KSh 32,000
Service Charge:   KSh  2,000
------------------------------------
TOTAL:            KSh 34,000
Status:           ACTIVE
Payment:          UNPAID
====================================
```

**A late return, paid by M-Pesa:**

```text
Toyota Prado returned after 6 day(s).
  Late by 2 day(s): late fee KSh 3,200
  Amount due: KSh 37,200

Processing M-Pesa payment...
Transaction: TJK34H8ABC
Payment of KSh 37,200 successful.
```

**Searching the fleet:**

```text
AVAILABLE SUVs

1. Toyota Prado
   Registration: KDJ 456B
   Rate: KSh 8,000/day

2. Nissan X-Trail
   Registration: KDJ 672B
   Rate: KSh 6,500/day
```

**Management report** (every figure is counted from the objects in the lists,
never typed in):

```text
=====================================
    SAFARIDRIVE MANAGEMENT REPORT
=====================================
Total Vehicles:               6
Available Vehicles:           5
Rented Vehicles:              1

Registered Customers:         3

Total Rentals:                5
Active Rentals:               1
Completed Rentals:            3
Cancelled Rentals:            1

Total Revenue:       KSh 83,700
-------------------------------------
VEHICLES BY CATEGORY
Economy Cars:                 2
SUVs:                         2
Luxury Cars:                  2
=====================================
```

---

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

52 tests covering the pricing of all three vehicle types, the late-fee worked
example from the brief (KSh 3,200), damage charges, the rental lifecycle, all
three payment types including a failed cash payment, each of the ten business
rules, the read-only revenue property, and the figures in the management report.

---

## Bonus features included

| Feature | Where |
|---|---|
| Automatic IDs (`C001…`, `R001…`) | class counters in `Customer` and `Rental` |
| Maintenance status | `Vehicle.send_for_maintenance()` / `return_from_maintenance()` |
| Damage charges on return | `return_vehicle(rental, actual_days, damage_charge)` |
| Cancellations | `CarRentalSystem.cancel_rental()` → frees the vehicle |
| Custom exception classes | `exceptions.py` |
| Interactive terminal menu | `python3 main.py --menu` |
| Timestamps | `Rental.started_at` / `returned_at` via `datetime` |

---

## OOP checklist

- [x] At least one abstract class: `Vehicle` and `Payment`
- [x] At least two parent classes: `Vehicle`, `Payment`
- [x] At least five child classes: `EconomyCar`, `SUV`, `LuxuryCar`, `MpesaPayment`, `CardPayment`, `CashPayment` (six)
- [x] `super().__init__()` used in every child that adds state
- [x] Methods overridden in child classes: `calculate_rental_cost()`, `extra_charges()`, `process_payment()`
- [x] Polymorphism with `calculate_rental_cost()` and `process_payment()`
- [x] Private attributes for availability, payment status and revenue
- [x] Lists of objects: `vehicles`, `customers`, `rentals`, `payments`, `Customer.rentals`
- [x] Loops and conditionals throughout
- [x] `try` / `except` around everything that can fail, in `main.py` and the menu
- [x] Methods that return values: `calculate_total()`, `find_vehicle()`, `search_vehicles()`
- [x] Methods that change state: `mark_as_rented()`, `complete_rental()`, `mark_as_paid()`
- [x] Code split across multiple files
