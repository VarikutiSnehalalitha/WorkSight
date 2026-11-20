"""Authentication & Strict Role-Based Access Control (RBAC) Dependencies."""

from typing import Callable, Iterable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import User

bearer_scheme = HTTPBearer(auto_error=False)

ROLE_SUPER_ADMIN = "super_admin"
ROLE_HR_ADMIN = "hr_admin"
ROLE_DEPT_MANAGER = "dept_manager"
ROLE_EMPLOYEE = "employee"

ADMIN_AND_HR = (ROLE_SUPER_ADMIN, ROLE_HR_ADMIN)
MANAGEMENT_ROLES = (ROLE_SUPER_ADMIN, ROLE_HR_ADMIN, ROLE_DEPT_MANAGER)
ALL_ROLES = (ROLE_SUPER_ADMIN, ROLE_HR_ADMIN, ROLE_DEPT_MANAGER, ROLE_EMPLOYEE)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token.")

    user = db.query(User).filter(User.id == int(user_id_str), User.is_active == True).first()  # noqa: E712
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found or inactive.")
    return user


def require_roles(allowed_roles: Iterable[str]) -> Callable:
    allowed_set = set(allowed_roles)

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Role '{current_user.role}' is not authorized for this resource.",
            )
        return current_user

    return _checker


def require_cctv_access(current_user: User = Depends(get_current_user)) -> User:
    """Strictly restricts CCTV management and live video viewing to authorized roles."""
    if current_user.role not in (ROLE_SUPER_ADMIN, ROLE_HR_ADMIN) or not current_user.can_view_cctv:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CCTV access denied. Only specifically authorized Admin/HR personnel may access camera streams.",
        )
    return current_user


def resolve_department_scope(current_user: User, requested_department_id: Optional[int]) -> Optional[int]:
    """Enforce that Department Managers can ONLY access their assigned department."""
    if current_user.role == ROLE_DEPT_MANAGER:
        if current_user.managed_department_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department Manager has no assigned department.",
            )
        if (
            requested_department_id is not None
            and requested_department_id != current_user.managed_department_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department Managers cannot access data outside their assigned department.",
            )
        return current_user.managed_department_id
    return requested_department_id
