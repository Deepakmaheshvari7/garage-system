"""
One-time cleanup script: deletes all dummy/transactional data before
deployment or a fresh start.

What it does:
    - Deletes ALL job parts, job cards, and inventory items.
    - By default KEEPS user accounts (so you don't lock yourself out).
    - Pass --wipe-users to also delete every user (you'll need to run
      create_first_admin again afterwards).

Usage:
    cd backend
    .\\.venv\\Scripts\\Activate
    python -m app.clear_data              # keep users
    python -m app.clear_data --wipe-users # delete everything

The script asks for confirmation before deleting anything.
"""
import sys

from app.core.database import SessionLocal
from app.models.job_card import JobCard
from app.models.job_part import JobPart
from app.models.inventory import InventoryItem
from app.models.user import User


def main():
    wipe_users = "--wipe-users" in sys.argv

    db = SessionLocal()
    try:
        counts = {
            "job_parts": db.query(JobPart).count(),
            "job_cards": db.query(JobCard).count(),
            "inventory": db.query(InventoryItem).count(),
            "users":     db.query(User).count(),
        }

        print("=== Current row counts ===")
        for table, n in counts.items():
            print(f"  {table:<12} {n}")

        target = "ALL data INCLUDING users" if wipe_users \
            else "job parts, job cards, and inventory (users kept)"
        answer = input(f"\nThis will permanently delete {target}.\n"
                       f"Type 'yes' to continue: ").strip().lower()
        if answer != "yes":
            print("Aborted. Nothing was deleted.")
            return

        # Order matters: children before parents.
        db.query(JobPart).delete(synchronize_session=False)
        db.query(JobCard).delete(synchronize_session=False)
        db.query(InventoryItem).delete(synchronize_session=False)
        if wipe_users:
            db.query(User).delete(synchronize_session=False)

        db.commit()
        print("\nDone. Dummy data cleared.")
        if wipe_users:
            print("All users deleted — run 'python -m app.create_first_admin' "
                  "to seed a new admin before logging in.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
