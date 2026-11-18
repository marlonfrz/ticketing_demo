from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_promoter_or_admin
from app.models.user import User
from app.schemas.promoter import (
    EventOrderItemResponse,
    EventStatsResponse,
    EventValidationItemResponse,
    PromoterDashboardResponse,
)
from app.services.promoter_service import (
    get_event_orders,
    get_event_stats,
    get_event_validations,
    get_promoter_dashboard,
)

router = APIRouter(prefix="/promoter", tags=["promoter"])


@router.get("/dashboard", response_model=PromoterDashboardResponse)
def promoter_dashboard_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return get_promoter_dashboard(db, current_user)


@router.get("/events/{event_id}/stats", response_model=EventStatsResponse)
def event_stats_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return get_event_stats(db, event_id, current_user)


@router.get("/events/{event_id}/orders", response_model=list[EventOrderItemResponse])
def event_orders_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return get_event_orders(db, event_id, current_user)


@router.get("/events/{event_id}/validations", response_model=list[EventValidationItemResponse])
def event_validations_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return get_event_validations(db, event_id, current_user)

