"""Create an isolated garage_test database for safe local testing.

Uses the postgres maintenance DB to CREATE DATABASE if it doesn't exist.
The connection comes from DATABASE_URL; the script refuses non-local hosts.
"""
import psycopg2
from sqlalchemy.engine import make_url

TEST_DB = "garage_test"


def main() -> None:
    from app.core.config import settings

    db_url = make_url(settings.DATABASE_URL)
    if db_url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Refusing to create a test database on a non-local host.")
    admin_dsn = db_url.set(database="postgres").render_as_string(hide_password=False)
    conn = psycopg2.connect(admin_dsn)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,))
    if cur.fetchone():
        print(f"'{TEST_DB}' already exists.")
    else:
        cur.execute(f'CREATE DATABASE "{TEST_DB}"')
        print(f"Created '{TEST_DB}'.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
