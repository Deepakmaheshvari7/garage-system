"""
JobParts table — bridge table mapping Inventory parts to JobCards.
Crucial for inventory reduction and billing calculations.
"""
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class JobPart(Base):
    __tablename__ = "job_parts"

    mapping_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_cards.job_id"), nullable=False)
    part_id = Column(Integer, ForeignKey("inventory.part_id"), nullable=False)
    quantity_used = Column(Integer, nullable=False)

    job = relationship("JobCard", back_populates="parts_used")
    part = relationship("InventoryItem", back_populates="job_links")
