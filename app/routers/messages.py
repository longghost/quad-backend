from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Message, User
from app.schemas import MessageCreate, MessageOut, ThreadOut

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("/threads", response_model=list[ThreadOut])
def list_threads(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sql = text("""
        SELECT DISTINCT ON (other_user_id, listing_id)
          other_user_id, listing_id, body AS last_message, m.created_at AS last_message_at,
          ou.full_name AS other_user_name, l.title AS listing_title,
          (sender_id != :uid AND read_at IS NULL) AS unread
        FROM (
          SELECT
            CASE WHEN sender_id = :uid THEN receiver_id ELSE sender_id END AS other_user_id,
            listing_id, body, sender_id, read_at, created_at
          FROM messages
          WHERE sender_id = :uid OR receiver_id = :uid
        ) m
        JOIN users ou ON ou.id = m.other_user_id
        LEFT JOIN listings l ON l.id = m.listing_id
        ORDER BY other_user_id, listing_id, m.created_at DESC
    """)
    rows = db.execute(sql, {"uid": current_user.id}).mappings().all()
    threads = [dict(r) for r in rows]
    threads.sort(key=lambda t: t["last_message_at"], reverse=True)
    return threads


@router.get("/thread/{other_user_id}", response_model=list[MessageOut])
def thread_detail(
    other_user_id: int,
    listing_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uid = current_user.id
    listing_clause = "AND listing_id = :listing_id" if listing_id is not None else "AND listing_id IS NULL"
    params = {"uid": uid, "other": other_user_id, "listing_id": listing_id}

    rows = db.execute(text(f"""
        SELECT * FROM messages
        WHERE ((sender_id = :uid AND receiver_id = :other) OR (sender_id = :other AND receiver_id = :uid))
        {listing_clause}
        ORDER BY created_at ASC
    """), params).mappings().all()

    db.execute(text(f"""
        UPDATE messages SET read_at = now()
        WHERE sender_id = :other AND receiver_id = :uid AND read_at IS NULL
        {listing_clause}
    """), params)
    db.commit()

    return [dict(r) for r in rows]


@router.post("", response_model=MessageOut, status_code=201)
def send_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot message yourself")

    message = Message(
        listing_id=payload.listing_id,
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        body=payload.body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
