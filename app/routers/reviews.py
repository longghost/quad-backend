from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Review, User
from app.schemas import ReviewCreate, ReviewOut
from app.limiter import limiter

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("", status_code=201)
@limiter.limit("5/hour")
def create_review(
    request: Request,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.seller_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot review yourself")

    review = Review(
        seller_id=payload.seller_id,
        reviewer_id=current_user.id,
        listing_id=payload.listing_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return {
        "id": review.id, "seller_id": review.seller_id, "reviewer_id": review.reviewer_id,
        "listing_id": review.listing_id, "rating": review.rating, "comment": review.comment,
        "created_at": review.created_at,
    }


@router.get("/seller/{seller_id}", response_model=list[ReviewOut])
def reviews_for_seller(seller_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Review, User.full_name.label("reviewer_name"))
        .join(User, User.id == Review.reviewer_id)
        .filter(Review.seller_id == seller_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return [
        ReviewOut(
            id=r.Review.id, rating=r.Review.rating, comment=r.Review.comment,
            created_at=r.Review.created_at, reviewer_name=r.reviewer_name,
        )
        for r in rows
    ]
