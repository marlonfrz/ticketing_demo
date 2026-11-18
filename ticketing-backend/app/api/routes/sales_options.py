from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.sales_options_service import get_event_sales_options


router = APIRouter(tags=["sales-options"])


@router.get("/events/{event_id}/sales-options")
def get_event_sales_options_route(
    event_id: str,
    session_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return get_event_sales_options(db, event_id, session_id)
