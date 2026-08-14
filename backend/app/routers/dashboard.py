from datetime import date, timedelta
import calendar

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_role
from app.models.job_card import JobCard, JobStatusEnum
from app.models.job_part import JobPart
from app.models.inventory import InventoryItem
from app.models.user import User, RoleEnum

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _completed_jobs(db, date_filter=None):
    q = (
        db.query(JobCard)
        .options(
            selectinload(JobCard.parts_used).selectinload(JobPart.part),
            selectinload(JobCard.mechanic),
        )
        .filter(JobCard.status == JobStatusEnum.COMPLETED)
    )
    if date_filter:
        q = q.filter(func.date(JobCard.updated_at) >= date_filter)
    return q.all()


def _job_revenue(job: JobCard) -> float:
    parts = sum(jp.quantity_used * jp.part.selling_price for jp in job.parts_used)
    return round(parts + job.labor_charge, 2)


@router.get("/metrics")
def top_level_metrics(db: Session = Depends(get_db),
                      _admin: User = Depends(require_role(RoleEnum.ADMIN))):
    today = date.today()

    # Aggregate revenue directly in SQL to avoid loading every completed job into Python.
    parts_revenue_today = (
        db.query(func.coalesce(func.sum(JobPart.quantity_used * InventoryItem.selling_price), 0.0))
        .join(InventoryItem, InventoryItem.part_id == JobPart.part_id)
        .join(JobCard, JobCard.job_id == JobPart.job_id)
        .filter(JobCard.status == JobStatusEnum.COMPLETED)
        .filter(func.date(JobCard.updated_at) == today)
        .scalar() or 0.0
    )
    labor_revenue_today = (
        db.query(func.coalesce(func.sum(JobCard.labor_charge), 0.0))
        .filter(JobCard.status == JobStatusEnum.COMPLETED)
        .filter(func.date(JobCard.updated_at) == today)
        .scalar() or 0.0
    )

    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    parts_revenue_month = (
        db.query(func.coalesce(func.sum(JobPart.quantity_used * InventoryItem.selling_price), 0.0))
        .join(InventoryItem, InventoryItem.part_id == JobPart.part_id)
        .join(JobCard, JobCard.job_id == JobPart.job_id)
        .filter(JobCard.status == JobStatusEnum.COMPLETED)
        .filter(JobCard.updated_at >= first_day)
        .filter(JobCard.updated_at <= last_day)
        .scalar() or 0.0
    )
    labor_revenue_month = (
        db.query(func.coalesce(func.sum(JobCard.labor_charge), 0.0))
        .filter(JobCard.status == JobStatusEnum.COMPLETED)
        .filter(JobCard.updated_at >= first_day)
        .filter(JobCard.updated_at <= last_day)
        .scalar() or 0.0
    )

    active_jobs = db.query(JobCard).filter(
        JobCard.status.in_([JobStatusEnum.OPEN, JobStatusEnum.IN_PROGRESS])
    ).count()

    total_items = db.query(InventoryItem).count()
    low_stock = db.query(InventoryItem).filter(
        InventoryItem.stock_quantity <= InventoryItem.min_threshold
    ).count()

    return {
        "revenue_today": round(parts_revenue_today + labor_revenue_today, 2),
        "revenue_month": round(parts_revenue_month + labor_revenue_month, 2),
        "active_jobs": active_jobs,
        "total_items": total_items,
        "low_stock_count": low_stock,
        "month_name": today.strftime("%B %Y"),
    }


@router.get("/revenue-trend")
def revenue_trend_30_days(db: Session = Depends(get_db),
                          _admin: User = Depends(require_role(RoleEnum.ADMIN))):
    cutoff = date.today() - timedelta(days=30)
    daily: dict[str, float] = {}
    for job in _completed_jobs(db, cutoff):
        if not job.updated_at:
            continue
        day = job.updated_at.date().isoformat()
        daily[day] = daily.get(day, 0.0) + _job_revenue(job)
    return [{"date": d, "revenue": round(v, 2)} for d, v in sorted(daily.items())]


@router.get("/parts-usage-by-category")
def parts_usage_by_category(db: Session = Depends(get_db),
                             _admin: User = Depends(require_role(RoleEnum.ADMIN))):
    rows = (
        db.query(InventoryItem.category,
                 func.sum(JobPart.quantity_used).label("total_used"))
        .join(JobPart, JobPart.part_id == InventoryItem.part_id)
        .group_by(InventoryItem.category).all()
    )
    return [{"category": cat or "Uncategorized", "quantity_used": int(qty)}
            for cat, qty in rows]


@router.get("/inventory-by-category")
def inventory_by_category(db: Session = Depends(get_db),
                           _admin: User = Depends(require_role(RoleEnum.ADMIN))):
    """Item count per category for the dashboard pie chart."""
    rows = (
        db.query(InventoryItem.category, func.count(InventoryItem.part_id).label("count"))
        .group_by(InventoryItem.category).all()
    )
    return [{"category": cat or "Uncategorized", "count": int(c)} for cat, c in rows]


@router.get("/top-selling")
def top_selling(db: Session = Depends(get_db),
                _admin: User = Depends(require_role(RoleEnum.ADMIN))):
    """Top 5 best-selling parts by quantity in the last 30 days."""
    cutoff = date.today() - timedelta(days=30)
    # Get job_ids of completed jobs in the last 30 days
    recent_job_ids = [
        j.job_id for j in _completed_jobs(db, cutoff)
    ]
    if not recent_job_ids:
        return []

    rows = (
        db.query(InventoryItem.name,
                 func.sum(JobPart.quantity_used).label("total_sold"))
        .join(JobPart, JobPart.part_id == InventoryItem.part_id)
        .filter(JobPart.job_id.in_(recent_job_ids))
        .group_by(InventoryItem.name)
        .order_by(func.sum(JobPart.quantity_used).desc())
        .limit(5).all()
    )
    return [{"name": name, "quantity_sold": int(qty)} for name, qty in rows]
