from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Review, User
from app.schemas import PublicUserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{user_id}", response_model=PublicUserOut)
def get_public_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    avg_rating, review_count = (
        db.query(func.coalesce(func.avg(Review.rating), 0), func.count(Review.id))
        .filter(Review.seller_id == user_id)
        .first()
    )

    return PublicUserOut(
        id=user.id,
        full_name=user.full_name,
        university=user.university,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        rating=float(avg_rating or 0),
        review_count=review_count or 0,
    )
