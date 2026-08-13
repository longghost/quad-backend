import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Listing, Transaction, User
from app.schemas import PaymentVerifyRequest, PaymentVerifyResponse

router = APIRouter(prefix="/api/payments", tags=["payments"])

PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/{reference}"


@router.post("/verify", response_model=PaymentVerifyResponse)
def verify_payment(
    payload: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = db.query(Listing).filter(Listing.id == payload.listing_id).with_for_update().first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status == "sold":
        raise HTTPException(status_code=400, detail="This listing has already been sold")
    if listing.seller_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot buy your own listing")

    if not settings.paystack_secret_key:
        raise HTTPException(status_code=500, detail="Payment verification is not configured on the server")

    # Always re-verify server-side with Paystack — never trust the front-end alone.
    resp = requests.get(
        PAYSTACK_VERIFY_URL.format(reference=payload.reference),
        headers={"Authorization": f"Bearer {settings.paystack_secret_key}"},
        timeout=15,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Could not verify payment with Paystack")

    data = resp.json()
    txn_data = data.get("data") or {}
    if not data.get("status") or txn_data.get("status") != "success":
        raise HTTPException(status_code=400, detail="Payment was not successful")

    # Paystack amounts are in the smallest currency unit (pesewas for GHS).
    paid_amount = txn_data.get("amount", 0)
    expected_amount = int(round(float(listing.price) * 100))
    if paid_amount < expected_amount:
        raise HTTPException(status_code=400, detail="Paid amount does not match the listing price")

    existing = db.query(Transaction).filter(Transaction.paystack_reference == payload.reference).first()
    if existing:
        raise HTTPException(status_code=409, detail="This transaction has already been recorded")

    txn = Transaction(
        listing_id=listing.id,
        buyer_id=current_user.id,
        seller_id=listing.seller_id,
        amount=listing.price,
        currency=listing.currency,
        paystack_reference=payload.reference,
        status="success",
    )
    db.add(txn)
    listing.status = "sold"
    db.commit()
    db.refresh(txn)

    return PaymentVerifyResponse(
        message="Payment verified — listing marked as sold",
        listing_status=listing.status,
        transaction_id=txn.id,
    )
