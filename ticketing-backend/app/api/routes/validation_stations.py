from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin, require_promoter_or_admin
from app.core.config import settings
from app.models.user import User
from app.schemas.ticket_validation import TicketValidationResponse
from app.schemas.validation_station import (
    ValidationQuotaRequestCreate,
    ValidationQuotaRequestResponse,
    ValidationQuotaRequestReview,
    ValidationSessionManagementResponse,
    ValidationStationActivate,
    ValidationStationActivityListResponse,
    ValidationStationActivityResponse,
    ValidationStationCreate,
    ValidationStationIncidentRequest,
    ValidationStationLinkResponse,
    ValidationStationResponse,
    ValidationStationScanRequest,
    ValidationStationSessionResponse,
)
from app.services.ticket_service import validate_ticket_by_qr
from app.services.validation_station_service import (
    VALIDATOR_STATION_COOKIE,
    activate_validation_station,
    create_validation_quota_request,
    create_validation_station,
    get_current_validation_station,
    get_validation_session_management,
    get_validation_station_activity,
    list_validation_quota_requests_admin,
    regenerate_validation_station_link,
    report_validation_station_incident,
    review_validation_quota_request,
    revoke_validation_station,
    serialize_validation_station,
)


router = APIRouter(tags=["validation-stations"])


def _set_station_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=VALIDATOR_STATION_COOKIE,
        value=token,
        max_age=settings.validation_station_session_expire_minutes * 60,
        httponly=True,
        secure=settings.validation_station_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post(
    "/validator-stations/activate",
    response_model=ValidationStationSessionResponse,
)
def activate_validation_station_route(
    data: ValidationStationActivate,
    response: Response,
    db: Session = Depends(get_db),
):
    station, access_token = activate_validation_station(db, data.token, data.responsible_name)
    _set_station_cookie(response, access_token)
    return {"station": station}


@router.get(
    "/validator-stations/me",
    response_model=ValidationStationSessionResponse,
)
def get_current_validation_station_route(
    request: Request,
    db: Session = Depends(get_db),
):
    station = get_current_validation_station(request, db)
    return {"station": serialize_validation_station(station)}


@router.post("/validator-stations/logout")
def logout_validation_station_route(response: Response):
    response.delete_cookie(VALIDATOR_STATION_COOKIE, path="/")
    return {"success": True}


@router.post(
    "/validator-stations/validate",
    response_model=TicketValidationResponse,
)
def validate_ticket_from_station_route(
    data: ValidationStationScanRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    station = get_current_validation_station(request, db)
    return validate_ticket_by_qr(
        db=db,
        qr_token=data.qr_token,
        validation_station=station,
        notes=data.notes,
    )


@router.post(
    "/validator-stations/incidents",
    response_model=ValidationStationActivityResponse,
)
def report_validation_station_incident_route(
    data: ValidationStationIncidentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    station = get_current_validation_station(request, db)
    return report_validation_station_incident(
        db,
        station,
        data.message,
        data.qr_token,
    )


@router.get(
    "/promoter/event-sessions/{session_id}/validation-stations",
    response_model=ValidationSessionManagementResponse,
)
def promoter_validation_session_management_route(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return get_validation_session_management(db, session_id, current_user)


@router.post(
    "/promoter/event-sessions/{session_id}/validation-quota-requests",
    response_model=ValidationQuotaRequestResponse,
)
def promoter_create_validation_quota_request_route(
    session_id: str,
    data: ValidationQuotaRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return create_validation_quota_request(
        db,
        session_id,
        current_user,
        data.requested_count,
        data.promoter_note,
    )


@router.post(
    "/promoter/event-sessions/{session_id}/validation-stations",
    response_model=ValidationStationLinkResponse,
)
def promoter_create_validation_station_route(
    session_id: str,
    data: ValidationStationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return create_validation_station(
        db,
        session_id,
        current_user,
        data.name,
        data.responsible_name,
        data.notes,
    )


@router.post(
    "/promoter/validation-stations/{station_id}/revoke",
    response_model=ValidationStationResponse,
)
def promoter_revoke_validation_station_route(
    station_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return revoke_validation_station(db, station_id, current_user)


@router.post(
    "/promoter/validation-stations/{station_id}/regenerate-link",
    response_model=ValidationStationLinkResponse,
)
def promoter_regenerate_validation_station_link_route(
    station_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return regenerate_validation_station_link(db, station_id, current_user)


@router.get(
    "/promoter/validation-stations/{station_id}/activity",
    response_model=ValidationStationActivityListResponse,
)
def promoter_validation_station_activity_route(
    station_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    result: str | None = None,
    ticket_code: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return get_validation_station_activity(
        db,
        station_id,
        current_user,
        limit,
        offset,
        result,
        ticket_code,
    )


@router.get(
    "/admin/event-sessions/{session_id}/validation-stations",
    response_model=ValidationSessionManagementResponse,
)
def admin_validation_session_management_route(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return get_validation_session_management(db, session_id, current_user)


@router.post(
    "/admin/event-sessions/{session_id}/validation-quota-requests",
    response_model=ValidationQuotaRequestResponse,
)
def admin_create_validation_quota_request_route(
    session_id: str,
    data: ValidationQuotaRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return create_validation_quota_request(
        db,
        session_id,
        current_user,
        data.requested_count,
        data.promoter_note,
    )


@router.post(
    "/admin/event-sessions/{session_id}/validation-stations",
    response_model=ValidationStationLinkResponse,
)
def admin_create_validation_station_route(
    session_id: str,
    data: ValidationStationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return create_validation_station(
        db,
        session_id,
        current_user,
        data.name,
        data.responsible_name,
        data.notes,
    )


@router.post(
    "/admin/validation-stations/{station_id}/revoke",
    response_model=ValidationStationResponse,
)
def admin_revoke_validation_station_route(
    station_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return revoke_validation_station(db, station_id, current_user)


@router.post(
    "/admin/validation-stations/{station_id}/regenerate-link",
    response_model=ValidationStationLinkResponse,
)
def admin_regenerate_validation_station_link_route(
    station_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return regenerate_validation_station_link(db, station_id, current_user)


@router.get(
    "/admin/validation-stations/{station_id}/activity",
    response_model=ValidationStationActivityListResponse,
)
def admin_validation_station_activity_route(
    station_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    result: str | None = None,
    ticket_code: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return get_validation_station_activity(
        db,
        station_id,
        current_user,
        limit,
        offset,
        result,
        ticket_code,
    )


@router.get(
    "/admin/validation-quota-requests",
    response_model=list[ValidationQuotaRequestResponse],
)
def admin_list_validation_quota_requests_route(
    request_status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return list_validation_quota_requests_admin(db, request_status)


@router.post(
    "/admin/validation-quota-requests/{quota_request_id}/review",
    response_model=ValidationQuotaRequestResponse,
)
def admin_review_validation_quota_request_route(
    quota_request_id: str,
    data: ValidationQuotaRequestReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return review_validation_quota_request(
        db,
        quota_request_id,
        current_user,
        data.status,
        data.approved_count,
        data.admin_note,
    )
