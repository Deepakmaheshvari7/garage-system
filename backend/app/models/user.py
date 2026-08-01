"""
Users table — authentication & role-based access control (RBAC).
"""
import enum

from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship

from app.core.database import Base


class RoleEnum(str, enum.Enum):
    ADMIN = "Admin"
    MECHANIC = "Mechanic"
    DESK = "Desk"


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)

    # A mechanic can have many job cards assigned to them.
    job_cards = relationship("JobCard", back_populates="mechanic")
