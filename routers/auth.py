import os
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient
from pydantic import BaseModel
from supabase import create_client
from fastapi.responses import HTMLResponse
from fastapi import Response, Request

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
def login(body: LoginRequest, response: Response):
    try:
        session = _supabase().auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception:
        return HTMLResponse(
            content='<p class="error-message">Invalid email or password</p>',
            status_code=401,
        )

    if not session.session:
        return HTMLResponse(
            content='<p class="error-message">Invalid email or password</p>',
            status_code=401,
        )
    
    response.set_cookie(
        key="access_token",
        value=session.session.access_token,
        httponly=True,      # JS can't read it — mitigates XSS token theft
        secure=False,       # set True once you're on https in prod
        samesite="lax",
        max_age=60 * 60,    # match Supabase token expiry
        path="/",
    )

    # redirects to admin-panel after successfull auth
    response.headers["HX-Redirect"] = "/admin-panel"

    return TokenResponse(
        access_token=session.session.access_token,
        refresh_token=session.session.refresh_token,
    )

# --- JWT verification dependency ---
JWKS_URL = "http://127.0.0.1:54321/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(JWKS_URL)

def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

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