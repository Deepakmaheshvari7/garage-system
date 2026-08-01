from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role, get_current_user
from app.core.security import hash_password
from app.models.user import User, RoleEnum
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


class PasswordReset(BaseModel):
    new_password: str


@router.get("", response_model=list[UserOut])
def list_users(
    role: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    List users, optionally filtered by role.
    role param accepts: 'Admin', 'Mechanic', 'Desk' (case-sensitive).
    """
    query = db.query(User)
    if role:
        try:
            role_enum = RoleEnum(role)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role '{role}'. Use Admin, Mechanic, or Desk.",
            )
        query = query.filter(User.role == role_enum)
    return query.order_by(User.username).all()


@router.patch("/{user_id}/password", response_model=UserOut)
def reset_password(
    user_id: int,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role(RoleEnum.ADMIN)),
):
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_role(RoleEnum.ADMIN)),
):
    if user_id == current_admin.user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
