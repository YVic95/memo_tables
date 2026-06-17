import os
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient
from pydantic import BaseModel
from supabase import create_client

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()

def _supabase():
    return create_client(
        os.environ["SUPABASE_PROJECT_URL_LOCAL"],
        os.environ["SUPABASE_SECRET_KEY_LOCAL"],
    )


# --- Schemas ---

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# --- Login endpoint ---

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    try:
        session = _supabase().auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not session.session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(
        access_token=session.session.access_token,
        refresh_token=session.session.refresh_token,
    )


# --- JWT verification dependency ---

JWKS_URL = "http://127.0.0.1:54321/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(JWKS_URL)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return payload


def require_admin(user: dict = Depends(get_current_user)):
    role = user.get("app_metadata", {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
