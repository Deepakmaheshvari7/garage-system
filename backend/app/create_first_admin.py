"""
One-time setup script: creates the first Admin user.

The /api/auth/register endpoint requires an existing Admin to create new
accounts, which means the very first user has to be seeded directly.

Usage:
    cd backend
    python -m app.create_first_admin
"""
import getpass

from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models.user import User, RoleEnum

Base.metadata.create_all(bind=engine)


def main():
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.role == RoleEnum.ADMIN).first()
        if existing_admin:
            print(f"An admin already exists: '{existing_admin.username}'. Aborting.")
            return

        print("=== Create the first Admin account ===")
        username = input("Username: ").strip()
        if not username:
            print("Username cannot be empty.")
            return

        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords did not match.")
            return
        if len(password) < 8:
            print("Password should be at least 8 characters.")
            return

        admin = User(
            username=username,
            password_hash=hash_password(password),
            role=RoleEnum.ADMIN,
        )
        db.add(admin)
        db.commit()
        print(f"Admin user '{username}' created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
