"""Seed dummy inventory parts for local testing of the job-card workflow.

Inserts 12 realistic bike parts into the LOCAL garage_db only (never
production — uses the local DATABASE_URL from .env). Each part_number is
prefixed with 'TEST-' so the batch is easy to identify and remove.

Run from backend/:
    .\\.venv\\Scripts\\python.exe scripts\\seed_dummy_parts.py
"""
from app.core.database import SessionLocal
from app.models.inventory import InventoryItem

DUMMY_PARTS = [
    # part_number, name, category, brand, bike_model, cost, sell, stock, threshold
    ("TEST-OIL-001",  "Engine Oil 10W-30 (1L)",   "Engine",     "Motul",   "Universal",  280, 350, 40, 10),
    ("TEST-BRK-002",  "Front Brake Pads",          "Brakes",     "TVS",     "Apache",     180, 260, 25, 5),
    ("TEST-BRK-003",  "Rear Brake Shoe",           "Brakes",     "Hero",    "Splendor",   120, 180, 30, 5),
    ("TEST-CLU-004",  "Clutch Plate Set",          "Engine",     "Bajaj",   "Pulsar",     450, 620, 15, 4),
    ("TEST-ELC-005",  "Headlight Bulb H4",         "Electrical", "Philips", "Universal",   90, 150, 50, 12),
    ("TEST-ELC-006",  "Indicator Relay",           "Electrical", "Honda",   "Activa",      60, 110,  3, 5),  # low stock
    ("TEST-FLT-007",  "Air Filter",                "Engine",     "K&N",     "Pulsar",     220, 340, 20, 6),
    ("TEST-FLT-008",  "Oil Filter",                "Engine",     "Bosch",   "Universal",   80, 140, 35, 8),
    ("TEST-CHK-009",  "Chain Sprocket Kit",        "Drivetrain", "Rolon",   "Apache",     850, 1150, 10, 3),
    ("TEST-SUS-010",  "Rear Shock Absorber",       "Suspension", "Gabriel", "Splendor",  1100, 1450,  8, 2),
    ("TEST-TYR-011",  "Rear Tyre 90/90-12",        "Tyres",      "MRF",     "Activa",     950, 1250,  0, 2),  # out of stock
    ("TEST-WRN-012",  "Spark Plug",                "Engine",     "NGK",     "Universal",   70, 130, 60, 15),
]


def main() -> None:
    db = SessionLocal()
    added, skipped = 0, 0
    try:
        for pn, name, cat, brand, model, cost, sell, stock, thr in DUMMY_PARTS:
            exists = db.query(InventoryItem).filter(
                InventoryItem.part_number == pn).first()
            if exists:
                skipped += 1
                continue
            db.add(InventoryItem(
                part_number=pn, name=name, category=cat, brand=brand,
                bike_model=model, cost_price=cost, selling_price=sell,
                stock_quantity=stock, min_threshold=thr,
            ))
            added += 1
        db.commit()
        print(f"Done. Added {added} dummy parts, skipped {skipped} existing.")
        print("All part_numbers are prefixed 'TEST-' for easy cleanup.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
