from typing import Optional

from pydantic import BaseModel, ConfigDict


class InventoryItemCreate(BaseModel):
    part_number: Optional[str] = None
    name: str
    category: Optional[str] = None
    min_threshold: int = 5
    brand: Optional[str] = None
    bike_model: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: float
    stock_quantity: int = 0


class InventoryItemUpdate(BaseModel):
    part_number: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    min_threshold: Optional[int] = None
    brand: Optional[str] = None
    bike_model: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    stock_quantity: Optional[int] = None


class InventoryItemOut(BaseModel):
    """Full view — includes cost_price. Only ever returned to Admins."""
    model_config = ConfigDict(from_attributes=True)

    part_id: int
    part_number: Optional[str] = None
    name: str
    category: Optional[str] = None
    min_threshold: int
    brand: Optional[str] = None
    bike_model: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: float
    stock_quantity: int
    is_low_stock: bool


class InventoryItemPublicOut(BaseModel):
    """Restricted view — for Mechanic/Desk roles. No cost_price."""
    model_config = ConfigDict(from_attributes=True)

    part_id: int
    part_number: Optional[str] = None
    name: str
    category: Optional[str] = None
    brand: Optional[str] = None
    bike_model: Optional[str] = None
    selling_price: float
    stock_quantity: int
    is_low_stock: bool


class BulkImportResult(BaseModel):
    inserted: int
    skipped_rows: list[int]
    errors: list[str]
