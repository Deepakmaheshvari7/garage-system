"""
Import all models here so that Base.metadata picks them up in one place
(used by create_all on startup and by Alembic migrations later).
"""
from app.models.user import User, RoleEnum
from app.models.inventory import InventoryItem
from app.models.job_card import JobCard, JobStatusEnum
from app.models.job_part import JobPart

__all__ = [
    "User",
    "RoleEnum",
    "InventoryItem",
    "JobCard",
    "JobStatusEnum",
    "JobPart",
]
