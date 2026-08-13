from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut, ForgotPasswordRequest, ResetPasswordRequest
from app.security import hash_password, verify_password, create_access_token
from app.email_utils import send_password_reset_email
from app.limiter import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("5/hour")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    payload.full_name = payload.full_name.strip()
    payload.university = payload.university.strip()
    if not payload.full_name or len(payload.full_name) > 120:
        raise HTTPException(status_code=400, detail="Full name is required and must be 120 characters or fewer")
    if not payload.university or len(payload.university) > 160:
        raise HTTPException(status_code=400, detail="University is required and must be 160 characters or fewer")
    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        university=payload.university,
        date_of_birth=payload.date_of_birth,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with that email already exists")
    db.refresh(user)

    token = create_access_token(user.id, user.role)
    return TokenResponse(user=UserOut.model_validate(user), token=token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id, user.role)
    return TokenResponse(user=UserOut.model_validate(user), token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/forgot-password", status_code=200)
@limiter.limit("5/hour")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    # Always return the same generic message, whether or not the email exists —
    # this stops someone using this endpoint to check who has an account.
    generic_response = {"message": "If that email is registered, a reset link has been sent."}

    if user is None:
        return generic_response

    user.reset_token = secrets.token_urlsafe(32)
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    email_sent = send_password_reset_email(user.email, user.full_name, user.reset_token)

    # Do not reveal whether an account exists. If the provider rejects the
    # message, clear the token so the user can safely request another reset.
    if not email_sent:
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()

    return generic_response


@router.post("/reset-password", status_code=200)
@limiter.limit("10/hour")
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.token).first()

    if user is None or user.reset_token_expires is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has already been used.")

    expires = user.reset_token_expires
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This reset link has expired. Please request a new one.")

    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Password reset successfully. You can now log in with your new password."}
