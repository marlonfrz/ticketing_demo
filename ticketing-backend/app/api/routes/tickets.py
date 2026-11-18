from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_optional_current_user, require_promoter, require_ticket_validator
from app.models.user import User
from app.schemas.ticket import TicketResponse
from app.schemas.ticket_validation import (
    TicketValidationItemResponse,
    TicketValidationRequest,
    TicketValidationResponse,
)
from app.schemas.ticket_delivery import TicketDeliveryResponse, TicketSendResponse
from app.services.ticket_service import (
    get_event_tickets_for_promoter,
    get_my_tickets,
    get_ticket_model_by_id_for_owner,
    get_order_tickets_pdf_for_owner,
    get_ticket_by_id,
    get_ticket_delivery_history,
    get_ticket_validations,
    get_tickets_by_order_id,
    send_ticket_email,
    validate_ticket_by_qr,
)
from app.utils.qr import generate_qr_png_bytes

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/my-tickets", response_model=list[TicketResponse])
def my_tickets_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_my_tickets(db, current_user)


@router.get("/order/{order_id}", response_model=list[TicketResponse])
def get_order_tickets_route(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_tickets_by_order_id(db, order_id, current_user)


@router.get("/order/{order_id}/pdf")
def download_order_tickets_pdf_route(
    order_id: str,
    x_guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    pdf_bytes, filename = get_order_tickets_pdf_for_owner(
        db,
        order_id,
        current_user,
        x_guest_token,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/validate", response_model=TicketValidationResponse)
def validate_ticket_route(
    data: TicketValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ticket_validator),
):
    return validate_ticket_by_qr(
        db=db,
        qr_token=data.qr_token,
        validator_user=current_user,
        device_id=data.device_id,
        notes=data.notes,
    )


@router.get("/event/{event_id}", response_model=list[TicketResponse])
def get_event_tickets_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter),
):
    return get_event_tickets_for_promoter(db, event_id, current_user)


@router.get("/{ticket_id}/validations", response_model=list[TicketValidationItemResponse])
def get_ticket_validations_route(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_ticket_validations(db, ticket_id, current_user)

@router.get("/{ticket_id}/qr-image")
def get_ticket_qr_image_route(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = get_ticket_model_by_id_for_owner(db, ticket_id, current_user)
    png_bytes = generate_qr_png_bytes(ticket.qr_token)
    return Response(content=png_bytes, media_type="image/png")

@router.post("/{ticket_id}/send", response_model=TicketSendResponse)
def send_ticket_route(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return send_ticket_email(db, ticket_id, current_user, force_resend=False)


@router.post("/{ticket_id}/resend", response_model=TicketSendResponse)
def resend_ticket_route(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return send_ticket_email(db, ticket_id, current_user, force_resend=True)


@router.get("/{ticket_id}/deliveries", response_model=list[TicketDeliveryResponse])
def get_ticket_deliveries_route(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_ticket_delivery_history(db, ticket_id, current_user)

@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket_route(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_ticket_by_id(db, ticket_id, current_user)
