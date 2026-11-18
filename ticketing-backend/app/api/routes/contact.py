from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.rate_limit import contact_rate_limit
from app.schemas.contact import ContactMessageResponse, OrganizerContactRequest
from app.services.contact_service import send_organizer_contact_email


router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("/organizer", response_model=ContactMessageResponse)
def contact_organizer(
    data: OrganizerContactRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(contact_rate_limit),
):
    if data.website:
        return {
            "success": True,
            "message": "Hemos recibido tu solicitud.",
        }

    background_tasks.add_task(send_organizer_contact_email, data)
    return {
        "success": True,
        "message": "Hemos recibido tu solicitud. Contactaremos contigo lo antes posible.",
    }
