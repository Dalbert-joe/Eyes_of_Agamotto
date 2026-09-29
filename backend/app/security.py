import hashlib, hmac, os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import User

SECRET=os.getenv("JWT_SECRET","local-development-only-change-this-secret")
ALGORITHM="HS256"
ACCESS_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES","15"))
REFRESH_DAYS=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS","7"))
bearer=HTTPBearer(auto_error=False)

def hash_password(password:str)->str:
    salt=os.urandom(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,200_000)
    return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"

def verify_password(password:str, encoded:str)->bool:
    try:
        _,iters,salt_hex,digest_hex=encoded.split("$")
        digest=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt_hex),int(iters))
        return hmac.compare_digest(digest.hex(),digest_hex)
    except Exception: return False

def _token(user:User, kind:str, lifetime:timedelta)->str:
    payload={"sub":user.id,"role":user.role,"type":kind,"exp":datetime.now(timezone.utc)+lifetime}
    return jwt.encode(payload,SECRET,algorithm=ALGORITHM)

def create_token(user:User)->str:
    return _token(user,"access",timedelta(minutes=ACCESS_MINUTES))

def create_refresh_token(user:User)->str:
    return _token(user,"refresh",timedelta(days=REFRESH_DAYS))

def decode_refresh_token(token:str)->dict:
    try:
        payload=jwt.decode(token,SECRET,algorithms=[ALGORITHM])
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,"Invalid or expired refresh token") from e
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,"Invalid refresh token")
    return payload

def current_user(credentials=Depends(bearer), db:Session=Depends(get_db)):
    if not credentials: raise HTTPException(status.HTTP_401_UNAUTHORIZED,"Authentication required")
    try: payload=jwt.decode(credentials.credentials,SECRET,algorithms=[ALGORITHM])
    except jwt.PyJWTError as e: raise HTTPException(status.HTTP_401_UNAUTHORIZED,"Invalid or expired token") from e
    if payload.get("type") != "access": raise HTTPException(status.HTTP_401_UNAUTHORIZED,"Invalid access token")
    user=db.get(User,payload.get("sub"))
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED,"User not found")
    return user

def require_role(*roles):
    def dep(user=Depends(current_user)):
        if user.role not in roles: raise HTTPException(status.HTTP_403_FORBIDDEN,"Permission denied")
        return user
    return dep
