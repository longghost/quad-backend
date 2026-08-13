import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Listing, ListingImage, Category, User, Review
from app.schemas import ListingCard, ListingDetail, ListingUpdate

router = APIRouter(prefix="/api/listings", tags=["listings"])

SORT_OPTIONS = {
    "newest": desc(Listing.created_at),
    "price_asc": asc(Listing.price),
    "price_desc": desc(Listing.price),
}


@router.get("", response_model=list[ListingCard])
def list_listings(
    search: str = "",
    category: str = "All",
    sort: str = "newest",
    seller_id: int | None = None,
    page: int = 1,
    limit: int = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    limit = min(max(limit, 1), 100)
    page = max(page, 1)
    search = search[:200]

    avg_rating = func.coalesce(func.avg(Review.rating), 0).label("seller_rating")
    first_image = (
        db.query(ListingImage.url)
        .filter(ListingImage.listing_id == Listing.id)
        .order_by(ListingImage.position.asc())
        .limit(1)
        .correlate(Listing)
        .scalar_subquery()
    )

    query = (
        db.query(
            Listing.id, Listing.title, Listing.price, Listing.currency,
            Listing.condition, Listing.status, Listing.created_at,
            Category.name.label("category"),
            User.id.label("seller_id"), User.full_name.label("seller_name"),
            avg_rating, first_image.label("img"),
        )
        .join(Category, Category.id == Listing.category_id)
        .join(User, User.id == Listing.seller_id)
        .outerjoin(Review, Review.seller_id == User.id)
        .filter(Listing.status == "active")
    )

    if search.strip():
        query = query.filter(Listing.title.ilike(f"%{search.strip()}%"))
    if category and category != "All":
        query = query.filter(Category.name == category)
    if seller_id is not None:
        query = query.filter(Listing.seller_id == seller_id)

    query = query.group_by(Listing.id, Category.name, User.id)
    query = query.order_by(SORT_OPTIONS.get(sort, SORT_OPTIONS["newest"]))
    query = query.limit(limit).offset((page - 1) * limit)

    return [ListingCard.model_validate(dict(row._mapping)) for row in query.all()]


@router.get("/{listing_id}", response_model=ListingDetail)
def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    avg_rating = func.coalesce(func.avg(Review.rating), 0).label("seller_rating")
    review_count = func.count(func.distinct(Review.id)).label("review_count")

    row = (
        db.query(
            Listing, Category.name.label("category"),
            User.id.label("seller_id"), User.full_name.label("seller_name"),
            User.avatar_url.label("seller_avatar"),
            avg_rating, review_count,
        )
        .join(Category, Category.id == Listing.category_id)
        .join(User, User.id == Listing.seller_id)
        .outerjoin(Review, Review.seller_id == User.id)
        .filter(Listing.id == listing_id)
        .group_by(Listing.id, Category.name, User.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    listing = row[0]
    images = [img.url for img in listing.images]

    return ListingDetail(
        id=listing.id, title=listing.title, description=listing.description,
        price=float(listing.price), currency=listing.currency, condition=listing.condition,
        pickup_location=listing.pickup_location, status=listing.status, created_at=listing.created_at,
        category=row.category, seller_id=row.seller_id, seller_name=row.seller_name,
        seller_avatar=row.seller_avatar, seller_rating=float(row.seller_rating),
        review_count=row.review_count, images=images,
    )


@router.post("", response_model=ListingDetail, status_code=201)
def create_listing(
    title: str = Form(...),
    category: str = Form(...),
    condition: str = Form(...),
    price: float = Form(...),
    description: str | None = Form(None),
    pickup_location: str | None = Form(None),
    photos: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cat = db.query(Category).filter(Category.name == category).first()
    if cat is None:
        raise HTTPException(status_code=400, detail="Unknown category")
    title = title.strip()
    if not title or len(title) > 160:
        raise HTTPException(status_code=400, detail="Title must be between 1 and 160 characters")
    if price < 0 or price > 10_000_000:
        raise HTTPException(status_code=400, detail="Price is outside the allowed range")
    if len(photos) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 photos")

    max_photo_bytes = 5 * 1024 * 1024
    total_photo_bytes = 0

    listing = Listing(
        seller_id=current_user.id, category_id=cat.id, title=title,
        description=description, price=price, condition=condition,
        pickup_location=pickup_location,
    )
    db.add(listing)
    db.flush()  # assigns listing.id without committing yet

    os.makedirs(settings.upload_dir, exist_ok=True)
    for position, photo in enumerate(photos):
        if photo.content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP, or GIF images are allowed")
        content = photo.file.read(max_photo_bytes + 1)
        if len(content) > max_photo_bytes:
            raise HTTPException(status_code=400, detail="Each photo must be 5 MB or smaller")
        total_photo_bytes += len(content)
        if total_photo_bytes > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Total photo upload must be 20 MB or smaller")
        signatures = {
            "image/jpeg": content[:3] == b"\xff\xd8\xff",
            "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/gif": content[:6] in {b"GIF87a", b"GIF89a"},
            "image/webp": content[:12].startswith(b"RIFF") and content[8:12] == b"WEBP",
        }
        if not signatures.get(photo.content_type, False):
            raise HTTPException(status_code=400, detail="The uploaded file is not a valid image")
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}[photo.content_type]
        filename = f"{uuid.uuid4().hex}{ext}"
        with open(os.path.join(settings.upload_dir, filename), "wb") as f:
            f.write(content)
        db.add(ListingImage(listing_id=listing.id, url=f"/uploads/{filename}", position=position))

    db.commit()
    return get_listing(listing.id, db, current_user)


@router.patch("/{listing_id}", response_model=ListingDetail)
def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this listing")

    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in {"active", "sold", "removed"}:
        raise HTTPException(status_code=400, detail="Invalid listing status")
    if "title" in changes and (not changes["title"] or len(changes["title"].strip()) > 160):
        raise HTTPException(status_code=400, detail="Title must be between 1 and 160 characters")
    for field, value in changes.items():
        setattr(listing, field, value)

    db.commit()
    return get_listing(listing_id, db, current_user)


@router.delete("/{listing_id}", status_code=204)
def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this listing")

    db.delete(listing)
    db.commit()
