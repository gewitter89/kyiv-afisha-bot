import hashlib
from datetime import datetime, timedelta
from typing import Union, Any, Optional
import jwt
import bcrypt
from app.core.config import settings


ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[str]:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token["sub"] if datetime.utcnow().timestamp() < decoded_token["exp"] else None
    except jwt.PyJWTError:
        return None

def compute_raw_item_hash(text: str, url: Optional[str] = None) -> str:
    """
    Computes a unique SHA-256 hash for raw content to identify duplicate items before inserting.
    """
    content = f"{url or ''}:{text}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
