"""
Inventory table — the parts catalog (SKUs) tracked in the garage.
"""
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship

from app.core.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory"

    part_id = Column(Integer, primary_key=True, index=True)

    # Basic details
    part_number = Column(String, unique=True, nullable=True, index=True)  # unique SKU / OEM number
    name = Column(String, nullable=False)
    category = Column(String, index=True)          # Engine, Body, Electrical, etc.
    min_threshold = Column(Integer, default=5, nullable=False)

    # Fits which bikes
    brand = Column(String, nullable=True)          # Bajaj, TVS, Hero, Honda, etc.
    bike_model = Column(String, nullable=True)     # Splendor, Passion, Pulsar, etc.

    # Price & Quantity
    cost_price = Column(Float, nullable=True)      # Admin-only, never exposed to Mechanic/Desk
    selling_price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)

    job_links = relationship("JobPart", back_populates="part")

    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.min_threshold
