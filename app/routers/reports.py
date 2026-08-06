import random

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import Report
from app.schemas import ReportCreate, ReportCreated, ReportStatusOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


def generate_reference() -> str:
    return f"QD-{random.randint(100000, 999999)}"


# Intentionally no auth dependency here — reporting must be barrier-free.
# Rate-limited instead, since anyone can call it without an account.
@router.post("", response_model=ReportCreated, status_code=201)
@limiter.limit("10/15minutes")
def create_report(request: Request, payload: ReportCreate, db: Session = Depends(get_db)):
    for _ in range(5):
        report = Report(
            reference=generate_reference(),
            listing_id=payload.listing_id,
            reported_user_id=payload.reported_user_id,
            reporter_name=payload.reporter_name,
            reporter_email=payload.reporter_email,
            category=payload.category,
            description=payload.description,
        )
        db.add(report)
        try:
            db.commit()
            db.refresh(report)
            return report
        except IntegrityError:
            db.rollback()
            continue  # reference collision, retry

    raise HTTPException(status_code=500, detail="Could not generate a unique report reference, please try again")


@router.get("/{reference}", response_model=ReportStatusOut)
def get_report_status(reference: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.reference == reference).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
