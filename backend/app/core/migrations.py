import os
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine


def _index_sql(table_name: str, index_name: str, column_expr: str) -> str:
    return (
        f"CREATE INDEX IF NOT EXISTS {index_name} "
        f"ON {table_name} ({column_expr});"
    )


def run_database_migrations() -> list[str]:
    """Apply lightweight production-safe schema checks/migrations.
    
    Ensures all table columns and indexes exist across environments safely.
    """
    statements = [
        # 1. Job Cards columns
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS amount_paid FLOAT;",
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS labor_charge FLOAT DEFAULT 0.0 NOT NULL;",
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS customer_name VARCHAR;",
        "ALTER TABLE job_cards ADD COLUMN IF NOT EXISTS customer_phone VARCHAR;",

        # 2. Inventory columns
        "ALTER TABLE inventory ADD COLUMN IF NOT EXISTS part_number VARCHAR;",
        "ALTER TABLE inventory ADD COLUMN IF NOT EXISTS brand VARCHAR;",
        "ALTER TABLE inventory ADD COLUMN IF NOT EXISTS bike_model VARCHAR;",
        "ALTER TABLE inventory ADD COLUMN IF NOT EXISTS min_threshold INTEGER DEFAULT 5;",

        # 3. Indexes
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
        for statement in statements:
            try:
                conn.execute(text(statement))
                applied.append(statement)
            except Exception:
                continue

    return applied
