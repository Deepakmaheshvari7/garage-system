"""
Demo Data Seeder
================
Populates the database with realistic fake data for a demo environment.
This script is SAFE to run — it only adds data and will SKIP seeding
if demo data already exists (idempotent).

Usage (from the `backend/` directory):
    python -m app.seed_demo_data

What it creates:
  - 1 Admin user         (username: demo_admin    / password: Demo@Admin1)
  - 2 Desk users         (username: demo_desk1    / password: Demo@Desk1)
                         (username: demo_desk2    / password: Demo@Desk2)
  - 2 Mechanic users     (username: demo_mech1    / password: Demo@Mech1)
                         (username: demo_mech2    / password: Demo@Mech2)
  - 30 Inventory parts   (various categories, brands, bike models)
  - 20 Job Cards         (mix of Open / In-Progress / Ready_For_Billing / Completed)
  - Job Parts linked to each job card (parts consumed per job)

WARN: Run this ONLY against a demo/staging database -- never against production.
"""

import sys
from datetime import datetime, timedelta, timezone
import random

from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models.user import User, RoleEnum
from app.models.inventory import InventoryItem
from app.models.job_card import JobCard, JobStatusEnum
from app.models.job_part import JobPart

# ── Demo users ────────────────────────────────────────────────────────────────
DEMO_USERS = [
    {"username": "demo_admin",  "password": "Demo@Admin1", "role": RoleEnum.ADMIN},
    {"username": "demo_desk1",  "password": "Demo@Desk1",  "role": RoleEnum.DESK},
    {"username": "demo_desk2",  "password": "Demo@Desk2",  "role": RoleEnum.DESK},
    {"username": "demo_mech1",  "password": "Demo@Mech1",  "role": RoleEnum.MECHANIC},
    {"username": "demo_mech2",  "password": "Demo@Mech2",  "role": RoleEnum.MECHANIC},
]

# ── Demo inventory parts ──────────────────────────────────────────────────────
DEMO_PARTS = [
    # Engine parts
    {"part_number": "DEMO-ENG-001", "name": "Piston Kit",         "category": "Engine",     "brand": "Bajaj",  "bike_model": "Pulsar 150",    "cost_price": 450,  "selling_price": 620,  "stock_quantity": 18, "min_threshold": 5},
    {"part_number": "DEMO-ENG-002", "name": "Engine Oil Filter",   "category": "Engine",     "brand": "Hero",   "bike_model": "Splendor Plus", "cost_price": 90,   "selling_price": 140,  "stock_quantity": 42, "min_threshold": 10},
    {"part_number": "DEMO-ENG-003", "name": "Cam Chain Tensioner", "category": "Engine",     "brand": "Honda",  "bike_model": "CB Shine",      "cost_price": 310,  "selling_price": 450,  "stock_quantity": 9,  "min_threshold": 5},
    {"part_number": "DEMO-ENG-004", "name": "Carburetor Assembly", "category": "Engine",     "brand": "TVS",    "bike_model": "Apache RTR 160","cost_price": 1200, "selling_price": 1650, "stock_quantity": 6,  "min_threshold": 3},
    {"part_number": "DEMO-ENG-005", "name": "Valve Set (In+Ex)",   "category": "Engine",     "brand": "Bajaj",  "bike_model": "Discover 125",  "cost_price": 380,  "selling_price": 530,  "stock_quantity": 12, "min_threshold": 4},
    {"part_number": "DEMO-ENG-006", "name": "Gasket Kit",          "category": "Engine",     "brand": "Hero",   "bike_model": "HF Deluxe",     "cost_price": 220,  "selling_price": 310,  "stock_quantity": 25, "min_threshold": 8},
    # Electrical parts
    {"part_number": "DEMO-ELE-001", "name": "CDI Unit",            "category": "Electrical", "brand": "Bajaj",  "bike_model": "Pulsar 150",    "cost_price": 890,  "selling_price": 1250, "stock_quantity": 5,  "min_threshold": 3},
    {"part_number": "DEMO-ELE-002", "name": "Rectifier / Regulator","category":"Electrical", "brand": "Honda",  "bike_model": "Activa 5G",     "cost_price": 480,  "selling_price": 680,  "stock_quantity": 7,  "min_threshold": 3},
    {"part_number": "DEMO-ELE-003", "name": "Self-Start Motor",    "category": "Electrical", "brand": "TVS",    "bike_model": "Jupiter",       "cost_price": 1350, "selling_price": 1900, "stock_quantity": 4,  "min_threshold": 2},
    {"part_number": "DEMO-ELE-004", "name": "Spark Plug (NGK)",    "category": "Electrical", "brand": None,     "bike_model": None,            "cost_price": 75,   "selling_price": 120,  "stock_quantity": 60, "min_threshold": 15},
    {"part_number": "DEMO-ELE-005", "name": "Headlight Bulb 35W",  "category": "Electrical", "brand": None,     "bike_model": None,            "cost_price": 55,   "selling_price": 90,   "stock_quantity": 35, "min_threshold": 10},
    {"part_number": "DEMO-ELE-006", "name": "Horn (Universal)",    "category": "Electrical", "brand": None,     "bike_model": None,            "cost_price": 110,  "selling_price": 180,  "stock_quantity": 22, "min_threshold": 8},
    # Brakes
    {"part_number": "DEMO-BRK-001", "name": "Front Brake Shoe Set","category": "Brakes",    "brand": "Hero",   "bike_model": "Passion Pro",   "cost_price": 200,  "selling_price": 290,  "stock_quantity": 20, "min_threshold": 6},
    {"part_number": "DEMO-BRK-002", "name": "Rear Drum Brake Kit", "category": "Brakes",    "brand": "TVS",    "bike_model": "Star City",     "cost_price": 185,  "selling_price": 265,  "stock_quantity": 16, "min_threshold": 5},
    {"part_number": "DEMO-BRK-003", "name": "Disc Brake Pads (F)", "category": "Brakes",    "brand": "Bajaj",  "bike_model": "Pulsar NS200",  "cost_price": 290,  "selling_price": 420,  "stock_quantity": 11, "min_threshold": 4},
    {"part_number": "DEMO-BRK-004", "name": "Tyre 90/90-17 Rear", "category": "Brakes",    "brand": None,     "bike_model": None,            "cost_price": 1100, "selling_price": 1480, "stock_quantity": 8,  "min_threshold": 3},
    # Body
    {"part_number": "DEMO-BDY-001", "name": "Front Mudguard",      "category": "Body",      "brand": "Hero",   "bike_model": "Splendor iSmart","cost_price": 310, "selling_price": 450,  "stock_quantity": 7,  "min_threshold": 3},
    {"part_number": "DEMO-BDY-002", "name": "Side Panel LH",       "category": "Body",      "brand": "Bajaj",  "bike_model": "CT 100",        "cost_price": 240,  "selling_price": 350,  "stock_quantity": 5,  "min_threshold": 2},
    {"part_number": "DEMO-BDY-003", "name": "Seat Assembly",       "category": "Body",      "brand": "Honda",  "bike_model": "CB Hornet 160R","cost_price": 950, "selling_price": 1350, "stock_quantity": 4,  "min_threshold": 2},
    {"part_number": "DEMO-BDY-004", "name": "Chain Guard",         "category": "Body",      "brand": "TVS",    "bike_model": "Apache RTR 200","cost_price": 130, "selling_price": 200,  "stock_quantity": 14, "min_threshold": 4},
    # Suspension
    {"part_number": "DEMO-SUS-001", "name": "Front Fork Oil Seal", "category": "Suspension","brand": "Bajaj",  "bike_model": "Avenger 220",   "cost_price": 420,  "selling_price": 580,  "stock_quantity": 10, "min_threshold": 4},
    {"part_number": "DEMO-SUS-002", "name": "Rear Shock Absorber", "category": "Suspension","brand": "Hero",   "bike_model": "Glamour",       "cost_price": 750,  "selling_price": 1050, "stock_quantity": 6,  "min_threshold": 2},
    {"part_number": "DEMO-SUS-003", "name": "Steering Ball Bearing","category":"Suspension","brand": None,     "bike_model": None,            "cost_price": 160,  "selling_price": 240,  "stock_quantity": 20, "min_threshold": 6},
    # Lubricants
    {"part_number": "DEMO-LUB-001", "name": "Engine Oil 1L (10W30)","category":"Lubricants","brand": None,     "bike_model": None,            "cost_price": 180,  "selling_price": 260,  "stock_quantity": 50, "min_threshold": 15},
    {"part_number": "DEMO-LUB-002", "name": "Gear Oil 90ML",       "category": "Lubricants","brand": None,     "bike_model": None,            "cost_price": 45,   "selling_price": 70,   "stock_quantity": 40, "min_threshold": 10},
    {"part_number": "DEMO-LUB-003", "name": "Chain Lube Spray",    "category": "Lubricants","brand": None,     "bike_model": None,            "cost_price": 90,   "selling_price": 140,  "stock_quantity": 30, "min_threshold": 8},
    # Transmission
    {"part_number": "DEMO-TRN-001", "name": "Drive Chain 428H",    "category":"Transmission","brand": None,    "bike_model": None,            "cost_price": 380,  "selling_price": 540,  "stock_quantity": 13, "min_threshold": 5},
    {"part_number": "DEMO-TRN-002", "name": "Sprocket Kit (F+R)",  "category":"Transmission","brand": "Bajaj", "bike_model": "Pulsar 220",    "cost_price": 520,  "selling_price": 720,  "stock_quantity": 8,  "min_threshold": 3},
    {"part_number": "DEMO-TRN-003", "name": "Clutch Plate Set",    "category":"Transmission","brand": "Hero",  "bike_model": "Splendor Plus", "cost_price": 340,  "selling_price": 480,  "stock_quantity": 9,  "min_threshold": 3},
    {"part_number": "DEMO-TRN-004", "name": "Primary Chain",       "category":"Transmission","brand": "Honda", "bike_model": "CB Unicorn",    "cost_price": 280,  "selling_price": 400,  "stock_quantity": 7,  "min_threshold": 3},
]

# ── Demo customers & vehicles ─────────────────────────────────────────────────
DEMO_CUSTOMERS = [
    ("Rajesh Kumar",    "9876543210", "MH12AB1234"),
    ("Priya Sharma",    "9123456789", "MH14CD5678"),
    ("Amit Patel",      "8800112233", "GJ01EF9012"),
    ("Sunita Verma",    "7711223344", "DL10GH3456"),
    ("Manoj Singh",     "9988776655", "UP32IJ7890"),
    ("Kavitha Nair",    "9090909090", "KA05KL2345"),
    ("Deepak Yadav",    "8877665544", "RJ14MN6789"),
    ("Anita Joshi",     "7766554433", "MP09OP0123"),
    ("Suresh Reddy",    "6655443322", "TN07QR4567"),
    ("Meena Iyer",      "9944332211", "MH01ST8901"),
    ("Vikram Bose",     "8833221100", "WB23UV2345"),
    ("Pooja Desai",     "9922110099", "GJ05WX6789"),
    ("Kiran Mehta",     "8811009988", "MH04YZ0123"),
    ("Ravi Pillai",     "7700998877", "KL08AB4567"),
    ("Lakshmi Rao",     "9600998877", "AP11CD8901"),
    ("Sanjay Gupta",    "9500887766", "HR26EF2345"),
    ("Neha Tiwari",     "9400776655", "UP16GH6789"),
    ("Arjun Chauhan",   "9300665544", "UK07IJ0123"),
    ("Rekha Pandey",    "9200554433", "BR01KL4567"),
    ("Ganesh Shinde",   "9100443322", "MH20MN8901"),
]


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _days_ago(n: int) -> datetime:
    return _utc_now() - timedelta(days=n)


def main() -> None:
    # Ensure all tables exist before seeding
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Idempotency check ─────────────────────────────────────────────────
        existing = db.query(User).filter(User.username == "demo_admin").first()
        if existing:
            print("Demo data already exists -- skipping. (Delete demo_admin user to re-seed)")
            sys.exit(0)

        print("Seeding demo data...")

        # ── 1. Users ──────────────────────────────────────────────────────────
        created_users: dict[str, User] = {}
        for u in DEMO_USERS:
            user = User(
                username=u["username"],
                password_hash=hash_password(u["password"]),
                role=u["role"],
            )
            db.add(user)
            created_users[u["username"]] = user

        db.flush()  # assign user_ids
        mechanics = [created_users["demo_mech1"], created_users["demo_mech2"]]
        print(f"  Created {len(DEMO_USERS)} users")

        # ── 2. Inventory ──────────────────────────────────────────────────────
        created_parts: list[InventoryItem] = []
        for p in DEMO_PARTS:
            part = InventoryItem(**p)
            db.add(part)
            created_parts.append(part)

        db.flush()
        print(f"  Created {len(DEMO_PARTS)} inventory items")

        # ── 3. Job Cards ──────────────────────────────────────────────────────
        statuses_weighted = (
            [JobStatusEnum.OPEN] * 4
            + [JobStatusEnum.IN_PROGRESS] * 5
            + [JobStatusEnum.READY_FOR_BILLING] * 4
            + [JobStatusEnum.COMPLETED] * 7
        )
        random.shuffle(statuses_weighted)

        created_jobs: list[JobCard] = []
        for i, (name, phone, reg) in enumerate(DEMO_CUSTOMERS):
            status = statuses_weighted[i]
            days_old = random.randint(0, 30)
            mechanic = random.choice(mechanics)
            labor = float(random.choice([300, 400, 500, 600, 700, 800, 1000, 1200]))

            job = JobCard(
                customer_name=name,
                customer_phone=phone,
                vehicle_reg=reg,
                mechanic_id=mechanic.user_id,
                status=status,
                labor_charge=labor,
                amount_paid=(labor + random.randint(200, 2000)) if status == JobStatusEnum.COMPLETED else None,
                created_at=_days_ago(days_old),
                updated_at=_days_ago(max(0, days_old - random.randint(0, days_old))),
            )
            db.add(job)
            created_jobs.append(job)

        db.flush()
        print(f"  Created {len(DEMO_CUSTOMERS)} job cards")

        # ── 4. Job Parts ──────────────────────────────────────────────────────
        job_parts_count = 0
        for job in created_jobs:
            num_parts = random.randint(1, 3)
            chosen_parts = random.sample(created_parts, k=min(num_parts, len(created_parts)))
            for part in chosen_parts:
                qty = random.randint(1, 2)
                if part.stock_quantity >= qty:
                    jp = JobPart(
                        job_id=job.job_id,
                        part_id=part.part_id,
                        quantity_used=qty,
                    )
                    part.stock_quantity -= qty  # mirrors real router behaviour
                    db.add(jp)
                    job_parts_count += 1

        db.commit()
        print(f"  Created {job_parts_count} job-part links")
        print()
        print("Demo data seeded successfully!")
        print()
        print("Demo login credentials:")
        print("-" * 52)
        print(f"  {'Username':<18} {'Password':<14} {'Role'}")
        print("-" * 52)
        for u in DEMO_USERS:
            print(f"  {u['username']:<18} {u['password']:<14} {u['role'].value}")
        print("-" * 52)

    except Exception as exc:
        db.rollback()
        print(f"Seeding failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
