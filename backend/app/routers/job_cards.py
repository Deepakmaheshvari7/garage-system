import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_role, get_current_user
from app.models.job_card import JobCard, JobStatusEnum
from app.models.job_part import JobPart
from app.models.inventory import InventoryItem
from app.models.user import User, RoleEnum
from app.schemas.job_card import (
    JobCardCreate, JobCardUpdate, JobCardOut,
    JobCardStatusUpdate, JobCardLaborUpdate, JobPartAdd, JobPartOut,
    JobPartQuantityUpdate,
)

logger = logging.getLogger("garage.jobcards")

router = APIRouter(prefix="/api/jobcards", tags=["job-cards"])


def _parts_total(job: JobCard) -> float:
    return round(sum(jp.quantity_used * jp.part.selling_price for jp in job.parts_used), 2)


def _summary(job: JobCard) -> dict:
    parts_total = _parts_total(job)
    return {
        "job_id": job.job_id,
        "customer_name": job.customer_name,
        "customer_phone": job.customer_phone,
        "vehicle_reg": job.vehicle_reg,
        "mechanic_id": job.mechanic_id,
        "mechanic_name": job.mechanic.username if job.mechanic else None,
        "status": job.status,
        "labor_charge": job.labor_charge,
        "parts_total": parts_total,
        "grand_total": round(parts_total + job.labor_charge, 2),
    }


def _out(job: JobCard) -> JobCardOut:
    parts, parts_total = [], 0.0
    for jp in job.parts_used:
        lt = round(jp.quantity_used * jp.part.selling_price, 2)
        parts_total += lt
        parts.append(JobPartOut(
            mapping_id=jp.mapping_id, part_id=jp.part_id,
            part_name=jp.part.name, quantity_used=jp.quantity_used,
            selling_price=jp.part.selling_price, line_total=lt,
        ))
    return JobCardOut(
        job_id=job.job_id,
        customer_name=job.customer_name,
        customer_phone=job.customer_phone,
        vehicle_reg=job.vehicle_reg,
        mechanic_id=job.mechanic_id,
        mechanic_name=job.mechanic.username if job.mechanic else None,
        status=job.status,
        labor_charge=job.labor_charge,
        parts_used=parts,
        parts_total=round(parts_total, 2),
        grand_total=round(parts_total + job.labor_charge, 2),
    )


def _detail_query(db: Session):
    """Build the complete job query used by detail and write responses.

    Write endpoints return JobCardOut. Loading its relationships explicitly
    keeps that response to a fixed number of queries rather than one query per
    part on the job card.
    """
    return db.query(JobCard).options(
        selectinload(JobCard.mechanic),
        selectinload(JobCard.parts_used).selectinload(JobPart.part),
    )


def _load_detail(db: Session, job_id: int) -> JobCard:
    return _detail_query(db).filter(JobCard.job_id == job_id).one()


@router.get("")
def list_job_cards(db: Session = Depends(get_db),
                   _u: User = Depends(get_current_user),
                   page: int = Query(1, ge=1),
                   page_size: int = Query(25, ge=1, le=200),
                   status: JobStatusEnum | None = None):
    query = (
        db.query(JobCard)
        .options(
            selectinload(JobCard.mechanic),
            selectinload(JobCard.parts_used).selectinload(JobPart.part),
        )
        .order_by(JobCard.job_id.desc())
    )
    if status is not None:
        query = query.filter(JobCard.status == status)
    total = query.count()
    offset = (page - 1) * page_size
    jobs = query.offset(offset).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if total else 1

    return {
        "items": [_summary(j) for j in jobs],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/{job_id}", response_model=JobCardOut)
def get_job_card(job_id: int, db: Session = Depends(get_db),
                 _u: User = Depends(get_current_user)):
    job = _detail_query(db).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    return _out(job)


@router.post("", response_model=JobCardOut, status_code=201)
def create_job_card(payload: JobCardCreate, db: Session = Depends(get_db),
                    _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    # Validate required field explicitly so the client gets a clear message
    # instead of a DB NOT NULL violation surfaced as a generic 500.
    if not payload.vehicle_reg or not payload.vehicle_reg.strip():
        raise HTTPException(400, "vehicle_reg is required.")
    payload.vehicle_reg = payload.vehicle_reg.strip().upper()

    # Validate the mechanic inside the SAME transaction that inserts the job,
    # so a mechanic deleted between page-load and submit can't slip through.
    if payload.mechanic_id:
        mechanic = db.query(User).filter(User.user_id == payload.mechanic_id,
                                         User.role == RoleEnum.MECHANIC).first()
        if not mechanic:
            raise HTTPException(
                400,
                "Selected mechanic no longer exists. Refresh the page and try again.",
            )

    job = JobCard(**payload.model_dump())
    db.add(job)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Job card create IntegrityError: %s", exc.orig)
        raise HTTPException(
            409,
            "Could not create job card: a database constraint was violated "
            "(often a stale mechanic selection). Refresh and try again.",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Job card create failed: %s", exc)
        raise HTTPException(
            500,
            "Could not create job card due to a database error. "
            "If this persists, check that the DB schema is up to date.",
        )
    return _out(_load_detail(db, job.job_id))


@router.patch("/{job_id}", response_model=JobCardOut)
def update_job_card(job_id: int, payload: JobCardUpdate,
                    db: Session = Depends(get_db),
                    _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(job, k, v)
    db.commit()
    return _out(_load_detail(db, job_id))


@router.patch("/{job_id}/labor", response_model=JobCardOut)
def update_labor(job_id: int, payload: JobCardLaborUpdate,
                 db: Session = Depends(get_db),
                 _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    job.labor_charge = payload.labor_charge
    db.commit()
    return _out(_load_detail(db, job_id))


@router.patch("/{job_id}/status", response_model=JobCardOut)
def update_status(job_id: int, payload: JobCardStatusUpdate,
                  db: Session = Depends(get_db),
                  _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    job.status = payload.status
    db.commit()
    return _out(_load_detail(db, job_id))


@router.post("/{job_id}/parts", response_model=JobCardOut)
def add_part(job_id: int, payload: JobPartAdd,
             db: Session = Depends(get_db),
             _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    if payload.quantity_used <= 0:
        raise HTTPException(400, "quantity_used must be positive")
    try:
        part = db.execute(
            select(InventoryItem).where(InventoryItem.part_id == payload.part_id).with_for_update()
        ).scalar_one_or_none()
        if not part:
            raise HTTPException(404, "Part not found")
        if part.stock_quantity < payload.quantity_used:
            raise HTTPException(409, f"Insufficient stock for '{part.name}': "
                                     f"{part.stock_quantity} available.")
        result = db.execute(
            InventoryItem.__table__.update()
            .where(InventoryItem.part_id == payload.part_id,
                   InventoryItem.stock_quantity >= payload.quantity_used)
            .values(stock_quantity=InventoryItem.stock_quantity - payload.quantity_used)
        )
        if result.rowcount == 0:
            raise HTTPException(409, f"Stock changed concurrently for '{part.name}', please retry.")
        existing = db.query(JobPart).filter(
            JobPart.job_id == job_id, JobPart.part_id == payload.part_id).first()
        if existing:
            existing.quantity_used += payload.quantity_used
        else:
            db.add(JobPart(job_id=job_id, part_id=payload.part_id,
                           quantity_used=payload.quantity_used))
        db.commit()
    except HTTPException:
        db.rollback(); raise
    except Exception:
        db.rollback(); raise
    return _out(_load_detail(db, job_id))


@router.patch("/{job_id}/parts/{mapping_id}", response_model=JobCardOut)
def update_part_quantity(job_id: int, mapping_id: int, payload: JobPartQuantityUpdate,
                         db: Session = Depends(get_db),
                         _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    """Change the quantity of a part already on the job.

    Inventory stays accurate because stock is adjusted by the *delta* between
    the old and new quantity (restock on decrease, deduct on increase) inside
    one transaction — no delete/re-add needed.
    """
    if payload.quantity_used <= 0:
        raise HTTPException(400, "quantity_used must be positive")
    jp = db.query(JobPart).filter(JobPart.mapping_id == mapping_id,
                                   JobPart.job_id == job_id).first()
    if not jp:
        raise HTTPException(404, "Part entry not found on this job")

    delta = payload.quantity_used - jp.quantity_used
    if delta == 0:
        return _out(_load_detail(db, job_id))

    try:
        if delta > 0:
            # Need more units: lock the row and deduct only if enough stock.
            part = db.execute(
                select(InventoryItem).where(InventoryItem.part_id == jp.part_id).with_for_update()
            ).scalar_one_or_none()
            if not part:
                raise HTTPException(404, "Part not found")
            if part.stock_quantity < delta:
                raise HTTPException(409, f"Insufficient stock for '{part.name}': "
                                         f"{part.stock_quantity} available.")
            result = db.execute(
                InventoryItem.__table__.update()
                .where(InventoryItem.part_id == jp.part_id,
                       InventoryItem.stock_quantity >= delta)
                .values(stock_quantity=InventoryItem.stock_quantity - delta)
            )
            if result.rowcount == 0:
                raise HTTPException(409, f"Stock changed concurrently for '{part.name}', please retry.")
        else:
            # Returning units to stock.
            db.execute(InventoryItem.__table__.update()
                       .where(InventoryItem.part_id == jp.part_id)
                       .values(stock_quantity=InventoryItem.stock_quantity - delta))  # delta is negative

        jp.quantity_used = payload.quantity_used
        db.commit()
    except HTTPException:
        db.rollback(); raise
    except Exception:
        db.rollback(); raise

    return _out(_load_detail(db, job_id))


@router.delete("/{job_id}/parts/{mapping_id}", response_model=JobCardOut)
def remove_part(job_id: int, mapping_id: int,
                db: Session = Depends(get_db),
                _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    jp = db.query(JobPart).filter(JobPart.mapping_id == mapping_id,
                                   JobPart.job_id == job_id).first()
    if not jp:
        raise HTTPException(404, "Part entry not found on this job")
    db.execute(InventoryItem.__table__.update()
               .where(InventoryItem.part_id == jp.part_id)
               .values(stock_quantity=InventoryItem.stock_quantity + jp.quantity_used))
    db.delete(jp); db.commit()
    return _out(_load_detail(db, job_id))
