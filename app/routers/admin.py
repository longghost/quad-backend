from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import Report, Listing, User
from app.schemas import ReportAdminOut, ReportUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

VALID_STATUSES = {"open", "in_review", "resolved", "dismissed"}


@router.get("/reports", response_model=list[ReportAdminOut])
def list_reports(status: str | None = None, page: int = 1, limit: int = 25, db: Session = Depends(get_db)):
    limit = min(limit, 100)
    page = max(page, 1)

    query = (
        db.query(
            Report, Listing.title.label("listing_title"), User.full_name.label("reported_user_name"),
        )
        .outerjoin(Listing, Listing.id == Report.listing_id)
        .outerjoin(User, User.id == Report.reported_user_id)
    )
    if status:
        query = query.filter(Report.status == status)

    rows = query.order_by(Report.created_at.desc()).limit(limit).offset((page - 1) * limit).all()

    return [
        ReportAdminOut(
            id=r.Report.id, reference=r.Report.reference, category=r.Report.category,
            description=r.Report.description, status=r.Report.status,
            reporter_name=r.Report.reporter_name, reporter_email=r.Report.reporter_email,
            created_at=r.Report.created_at, updated_at=r.Report.updated_at,
            listing_id=r.Report.listing_id, listing_title=r.listing_title,
            reported_user_id=r.Report.reported_user_id, reported_user_name=r.reported_user_name,
        )
        for r in rows
    ]


@router.patch("/reports/{report_id}")
def update_report(
    report_id: int,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(VALID_STATUSES)}")
        report.status = payload.status
        if payload.status in ("resolved", "dismissed"):
            report.resolved_by = current_admin.id

    if payload.resolution_note is not None:
        report.resolution_note = payload.resolution_note

    db.commit()
    db.refresh(report)
    return report
