from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings, is_admin_email
from app.database import get_db
from app.models import User

security = HTTPBearer(auto_error=False)
settings = get_settings()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # Keep configured admin emails elevated in every environment
    if is_admin_email(user.email) and not user.is_admin:
        user.is_admin = True
        db.commit()
        db.refresh(user)
    return user


def get_optional_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    if not creds:
        return None
    try:
        payload = jwt.decode(creds.credentials, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
        return db.query(User).filter(User.id == user_id).first()
    except (JWTError, ValueError):
        return None


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def get_or_create_user_by_email(
    db: Session,
    email: str,
    name: str = "",
    picture: str = "",
    google_id: str | None = None,
) -> User:
    email_l = email.lower().strip()
    user = db.query(User).filter(User.email == email_l).first()
    if user:
        if name and not user.name:
            user.name = name
        if picture:
            user.picture = picture
        if google_id and not user.google_id:
            user.google_id = google_id
        if is_admin_email(email_l):
            user.is_admin = True
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=email_l,
        name=name or email_l.split("@")[0],
        picture=picture,
        google_id=google_id,
        is_admin=is_admin_email(email_l),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
