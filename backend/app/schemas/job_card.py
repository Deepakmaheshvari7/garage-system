from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.job_card import JobStatusEnum


class JobCardCreate(BaseModel):
    customer_name:  Optional[str] = None
    customer_phone: Optional[str] = None
    vehicle_reg:    str
    mechanic_id:    Optional[int] = None
    labor_charge:   float = 0.0


class JobCardUpdate(BaseModel):
    customer_name:  Optional[str] = None
    customer_phone: Optional[str] = None
    vehicle_reg:    Optional[str] = None
    mechanic_id:    Optional[int] = None
    labor_charge:   Optional[float] = None
    amount_paid:    Optional[float] = None


class JobCardStatusUpdate(BaseModel):
    status: JobStatusEnum


class JobCardLaborUpdate(BaseModel):
    labor_charge: float


class JobPartAdd(BaseModel):
    part_id:       int
    quantity_used: int


class JobPartQuantityUpdate(BaseModel):
    quantity_used: int


class JobPartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    mapping_id:    int
    part_id:       int
    part_name:     str
    quantity_used: int
    selling_price: float
    line_total:    float


class JobCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    job_id:         int
    customer_name:  Optional[str] = None
    customer_phone: Optional[str] = None
    vehicle_reg:    str
    mechanic_id:    Optional[int] = None
    mechanic_name:  Optional[str] = None
    status:         JobStatusEnum
    labor_charge:   float
    amount_paid:    Optional[float] = None
    parts_used:     list[JobPartOut] = []
    parts_total:    float = 0.0
    grand_total:    float = 0.0
