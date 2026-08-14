import enum
from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class JobStatusEnum(str, enum.Enum):
    OPEN = "Open"
    IN_PROGRESS = "In-Progress"
    READY_FOR_BILLING = "Ready_For_Billing"
    COMPLETED = "Completed"


class JobCard(Base):
    __tablename__ = "job_cards"

    job_id        = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=True)
    customer_phone= Column(String, nullable=True)
    vehicle_reg   = Column(String, nullable=False, index=True)
    mechanic_id   = Column(Integer, ForeignKey("users.user_id"), nullable=True, index=True)
    status        = Column(Enum(JobStatusEnum), default=JobStatusEnum.OPEN, nullable=False, index=True)

    # Labour charge entered manually by desk — no hourly calculation
    labor_charge  = Column(Float, default=0.0, nullable=False)

    created_at    = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)

    mechanic    = relationship("User", back_populates="job_cards")
    parts_used  = relationship("JobPart", back_populates="job", cascade="all, delete-orphan")
