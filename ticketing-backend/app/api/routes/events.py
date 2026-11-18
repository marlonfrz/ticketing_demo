from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_admin, require_promoter_or_admin
from app.models.user import User
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.schemas.status_action import StatusActionResponse
from app.schemas.ticket import (
    ComplimentaryTicketBatchResponse,
    ComplimentaryTicketCreateRequest,
    ComplimentaryTicketSummaryResponse,
)
from app.services.event_service import (
    create_event,
    delete_unpublished_event,
    finish_event,
    get_event_financial_summary,
    get_event_by_id,
    get_event_detail_for_management,
    get_events_by_promoter,
    list_events,
    publish_event,
    submit_event_for_review,
    unpublish_event,
    update_event,
    get_event_ticket_capacity_summary,
)
from app.services.event_session_service import serialize_event_session
from app.services.ticket_service import (
    generate_complimentary_tickets,
    get_complimentary_order_tickets_pdf_for_manager,
    get_event_complimentary_tickets_summary,
)
from app.services.event_image_service import upload_event_image

router = APIRouter(prefix="/events", tags=["events"])

@router.post("", response_model=EventResponse)
def create_event_route(
    data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    event = create_event(db, current_user, data)
    return serialize_event_for_management(event)


@router.get("", response_model=list[EventResponse])
def list_events_route(db: Session = Depends(get_db)):
    events = list_events(db)
    return [serialize_event(event) for event in events]

@router.get("/me", response_model=list[EventResponse])
def my_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    events = get_events_by_promoter(db, current_user)
    return [serialize_event_for_management(event) for event in events]


@router.get("/{event_id}", response_model=EventResponse)
def get_event_route(event_id: str, db: Session = Depends(get_db)):
    event = get_event_by_id(db, event_id)
    return serialize_event(event)


@router.put("/{event_id}", response_model=EventResponse)
def update_event_route(
    event_id: str,
    data: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    event = update_event(db, event_id, current_user, data)
    return serialize_event_for_management(event)


@router.post("/{event_id}/image", response_model=EventResponse)
async def upload_event_image_route(
    event_id: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    event = await upload_event_image(db, event_id, current_user, image)
    return serialize_event_for_management(event)


@router.get("/{event_id}/manage", response_model=EventResponse)
def get_event_manage_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    event = get_event_detail_for_management(db, event_id, current_user)
    return serialize_event_for_management(
        event,
        financial_summary=get_event_financial_summary(db, event_id),
    )

def serialize_event(event):
    return _serialize_event(event, expose_financial_fields=False)


def serialize_event_for_management(event, financial_summary: dict | None = None):
    return _serialize_event(
        event,
        expose_financial_fields=True,
        financial_summary=financial_summary,
    )


def _serialize_event(event, expose_financial_fields: bool = False, financial_summary: dict | None = None):
    visible_sessions = list(event.sessions)
    if not expose_financial_fields:
        visible_sessions = [
            session
            for session in visible_sessions
            if session.status in {"published", "sold_out", "finished"}
        ]

    data = {
        "id": str(event.id),
        "promoter_id": str(event.promoter_id),
        "title": event.title,
        "description": event.description,
        "publish_at": event.publish_at,
        "status": event.status,
        "platform_fee_type": event.platform_fee_type if expose_financial_fields else None,
        "platform_fee_value": event.platform_fee_value if expose_financial_fields else None,
        "image_url": event.image_url,
        "financial_summary": financial_summary,
        "sessions": [
            serialize_event_session(session)
            for session in sorted(
                visible_sessions,
                key=lambda session: (
                    session.display_order is None,
                    session.display_order or 999999,
                    session.starts_at,
                ),
            )
        ],
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }
    return data

@router.post("/{event_id}/unpublish", response_model=StatusActionResponse)
def unpublish_event_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return unpublish_event(db, event_id, current_user)


@router.delete("/{event_id}", response_model=StatusActionResponse)
def delete_unpublished_event_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return delete_unpublished_event(db, event_id, current_user)


@router.post("/{event_id}/finish", response_model=StatusActionResponse)
def finish_event_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return finish_event(db, event_id, current_user)

@router.post("/{event_id}/publish", response_model=StatusActionResponse)
def publish_event_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return publish_event(db, event_id, current_user)


@router.post("/{event_id}/submit-review", response_model=StatusActionResponse)
def submit_event_review_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return submit_event_for_review(db, event_id, current_user)

@router.get("/{event_id}/ticket-capacity-summary")
def get_event_ticket_capacity_summary_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return get_event_ticket_capacity_summary(db, event_id, current_user)


@router.get("/{event_id}/complimentary-tickets", response_model=ComplimentaryTicketSummaryResponse)
def get_event_complimentary_tickets_route(
    event_id: str,
    session_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return get_event_complimentary_tickets_summary(db, event_id, current_user, session_id)


@router.post("/{event_id}/complimentary-tickets", response_model=ComplimentaryTicketBatchResponse)
def generate_event_complimentary_tickets_route(
    event_id: str,
    data: ComplimentaryTicketCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return generate_complimentary_tickets(db, event_id, current_user, data)


@router.get("/{event_id}/complimentary-tickets/orders/{order_id}/pdf")
def download_event_complimentary_tickets_pdf_route(
    event_id: str,
    order_id: str,
    session_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    pdf_bytes, filename = get_complimentary_order_tickets_pdf_for_manager(
        db,
        event_id,
        order_id,
        current_user,
        session_id,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
