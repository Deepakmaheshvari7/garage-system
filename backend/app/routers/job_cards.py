from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role, get_current_user
from app.models.job_card import JobCard, JobStatusEnum
from app.models.job_part import JobPart
from app.models.inventory import InventoryItem
from app.models.user import User, RoleEnum
from app.schemas.job_card import (
    JobCardCreate, JobCardUpdate, JobCardOut,
    JobCardStatusUpdate, JobCardLaborUpdate, JobPartAdd, JobPartOut,
)

router = APIRouter(prefix="/api/jobcards", tags=["job-cards"])


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


@router.get("")
def list_job_cards(db: Session = Depends(get_db),
                   _u: User = Depends(get_current_user)):
    return [_out(j) for j in db.query(JobCard).order_by(JobCard.job_id.desc()).all()]


@router.get("/{job_id}", response_model=JobCardOut)
def get_job_card(job_id: int, db: Session = Depends(get_db),
                 _u: User = Depends(get_current_user)):
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    return _out(job)


@router.post("", response_model=JobCardOut, status_code=201)
def create_job_card(payload: JobCardCreate, db: Session = Depends(get_db),
                    _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    if payload.mechanic_id:
        if not db.query(User).filter(User.user_id == payload.mechanic_id,
                                     User.role == RoleEnum.MECHANIC).first():
            raise HTTPException(400, "Invalid mechanic_id")
    job = JobCard(**payload.model_dump())
    db.add(job); db.commit(); db.refresh(job)
    return _out(job)


@router.patch("/{job_id}", response_model=JobCardOut)
def update_job_card(job_id: int, payload: JobCardUpdate,
                    db: Session = Depends(get_db),
                    _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(job, k, v)
    db.commit(); db.refresh(job)
    return _out(job)


@router.patch("/{job_id}/labor", response_model=JobCardOut)
def update_labor(job_id: int, payload: JobCardLaborUpdate,
                 db: Session = Depends(get_db),
                 _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    job.labor_charge = payload.labor_charge
    db.commit(); db.refresh(job)
    return _out(job)


@router.patch("/{job_id}/status", response_model=JobCardOut)
def update_status(job_id: int, payload: JobCardStatusUpdate,
                  db: Session = Depends(get_db),
                  _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK))):
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    job.status = payload.status
    db.commit(); db.refresh(job)
    return _out(job)


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
    db.refresh(job)
    return _out(job)


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
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    return _out(job)
