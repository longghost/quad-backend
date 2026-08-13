from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------- Auth ----------
class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    university: str
    date_of_birth: date
    password: str = Field(min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str
    university: str
    role: str
    avatar_url: str | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    user: UserOut
    token: str


# ---------- Listings ----------
class ListingCreate(BaseModel):
    title: str
    description: str | None = None
    price: float = Field(ge=0)
    condition: str
    pickup_location: str | None = None
    category: str


class ListingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, ge=0)
    condition: str | None = None
    pickup_location: str | None = None
    status: str | None = None


class ListingCard(BaseModel):
    id: int
    title: str
    price: float
    currency: str
    condition: str
    status: str
    created_at: datetime
    category: str
    seller_id: int
    seller_name: str
    seller_rating: float
    img: str | None = None


class ListingDetail(BaseModel):
    id: int
    title: str
    description: str | None
    price: float
    currency: str
    condition: str
    pickup_location: str | None
    status: str
    created_at: datetime
    category: str
    seller_id: int
    seller_name: str
    seller_avatar: str | None
    seller_rating: float
    review_count: int
    images: list[str]


# ---------- Categories ----------
class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# ---------- Reviews ----------
class ReviewCreate(BaseModel):
    seller_id: int
    listing_id: int | None = None
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewOut(BaseModel):
    id: int
    rating: int
    comment: str | None
    created_at: datetime
    reviewer_name: str


# ---------- Messages ----------
class MessageCreate(BaseModel):
    receiver_id: int
    body: str
    listing_id: int | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    listing_id: int | None
    sender_id: int
    receiver_id: int
    body: str
    read_at: datetime | None
    created_at: datetime


class ThreadOut(BaseModel):
    other_user_id: int
    other_user_name: str
    listing_id: int | None
    listing_title: str | None
    last_message: str
    last_message_at: datetime
    unread: bool


# ---------- Reports ----------
class ReportCreate(BaseModel):
    category: str
    description: str
    listing_id: int | None = None
    reported_user_id: int | None = None
    reporter_name: str | None = None
    reporter_email: EmailStr | None = None


class ReportCreated(BaseModel):
    id: int
    reference: str
    status: str
    created_at: datetime


class ReportStatusOut(BaseModel):
    reference: str
    category: str
    status: str
    created_at: datetime
    updated_at: datetime


# ---------- Public user profile ----------
class PublicUserOut(BaseModel):
    id: int
    full_name: str
    university: str
    avatar_url: str | None
    created_at: datetime
    rating: float
    review_count: int


# ---------- Payments ----------
class PaymentVerifyRequest(BaseModel):
    reference: str
    listing_id: int


class PaymentVerifyResponse(BaseModel):
    message: str
    listing_status: str
    transaction_id: int


# ---------- Admin ----------
class ReportAdminOut(BaseModel):
    id: int
    reference: str
    category: str
    description: str
    status: str
    reporter_name: str | None
    reporter_email: str | None
    created_at: datetime
    updated_at: datetime
    listing_id: int | None
    listing_title: str | None
    reported_user_id: int | None
    reported_user_name: str | None


class ReportUpdate(BaseModel):
    status: str | None = None
    resolution_note: str | None = None
