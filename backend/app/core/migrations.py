import os
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import engine


def _index_sql(table_name: str, index_name: str, column_expr: str) -> str:
    return (
        f"CREATE INDEX IF NOT EXISTS {index_name} "
        f"ON {table_name} ({column_expr});"
    )


def run_database_migrations() -> list[str]:
    """Apply lightweight production-safe schema checks/migrations.

    This project is still in a single-database setup, so startup migrations are
    intentionally conservative: we only create indexes and fill schema gaps that
    are required for the app's performance and data integrity.
    """
    if settings.ENV != "production" and os.getenv("RUN_DB_MIGRATIONS", "false").lower() not in {"1", "true", "yes"}:
        return []

    statements = [
        _index_sql("inventory", "ix_inventory_name", "name"),
        _index_sql("inventory", "ix_inventory_category", "category"),
        _index_sql("inventory", "ix_inventory_brand", "brand"),
        _index_sql("inventory", "ix_inventory_bike_model", "bike_model"),
        _index_sql("job_cards", "ix_job_cards_status", "status"),
        _index_sql("job_cards", "ix_job_cards_created_at", "created_at"),
        _index_sql("job_cards", "ix_job_cards_updated_at", "updated_at"),
        _index_sql("job_cards", "ix_job_cards_mechanic_id", "mechanic_id"),
        _index_sql("job_parts", "ix_job_parts_job_id", "job_id"),
        _index_sql("job_parts", "ix_job_parts_part_id", "part_id"),
    ]

    applied = []
    with engine.begin() as conn:
        inspector = inspect(conn)
        existing_tables = set(inspector.get_table_names())
        for statement in statements:
            table_name = statement.split("ON ", 1)[1].split(" ", 1)[0]
            if table_name not in existing_tables:
                continue
            try:
                conn.execute(text(statement))
                applied.append(statement)
            except Exception:
                # Ignore failures from partially applied states and let the app continue.
                continue

    return applied
