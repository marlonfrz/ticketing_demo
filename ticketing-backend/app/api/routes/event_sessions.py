from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin, require_promoter_or_admin
from app.models.user import User
from app.schemas.event_session import (
    EventSessionCreate,
    EventSessionResponse,
    EventSessionUpdate,
)
from app.schemas.status_action import StatusActionResponse
from app.services.event_session_service import (
    create_event_session,
    delete_or_disable_event_session,
    duplicate_event_session,
    finish_event_session,
    list_event_sessions,
    publish_all_event_sessions,
    publish_event_session,
    serialize_event_session,
    submit_all_event_sessions_for_review,
    submit_event_session_for_review,
    unpublish_event_session,
    update_event_session,
)


router = APIRouter(tags=["event-sessions"])


@router.get("/events/{event_id}/sessions", response_model=list[EventSessionResponse])
def list_event_sessions_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return [
        serialize_event_session(session)
        for session in list_event_sessions(db, event_id, current_user)
    ]


@router.post("/events/{event_id}/sessions", response_model=EventSessionResponse)
def create_event_session_route(
    event_id: str,
    data: EventSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return serialize_event_session(create_event_session(db, event_id, current_user, data))


@router.post("/events/{event_id}/sessions/submit-review", response_model=StatusActionResponse)
def submit_all_event_sessions_review_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return submit_all_event_sessions_for_review(db, event_id, current_user)


@router.post("/events/{event_id}/sessions/publish", response_model=StatusActionResponse)
def publish_all_event_sessions_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return publish_all_event_sessions(db, event_id, current_user)


@router.put("/event-sessions/{session_id}", response_model=EventSessionResponse)
def update_event_session_route(
    session_id: str,
    data: EventSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return serialize_event_session(update_event_session(db, session_id, current_user, data))


@router.post("/event-sessions/{session_id}/duplicate", response_model=EventSessionResponse)
def duplicate_event_session_route(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return serialize_event_session(duplicate_event_session(db, session_id, current_user))


@router.post("/event-sessions/{session_id}/publish", response_model=EventSessionResponse)
def publish_event_session_route(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return serialize_event_session(publish_event_session(db, session_id, current_user))


@router.post("/event-sessions/{session_id}/unpublish", response_model=EventSessionResponse)
def unpublish_event_session_route(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return serialize_event_session(unpublish_event_session(db, session_id, current_user))


@router.post("/event-sessions/{session_id}/finish", response_model=EventSessionResponse)
def finish_event_session_route(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return serialize_event_session(finish_event_session(db, session_id, current_user))


@router.post("/event-sessions/{session_id}/submit-review", response_model=StatusActionResponse)
def submit_event_session_review_route(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return submit_event_session_for_review(db, session_id, current_user)


@router.delete("/event-sessions/{session_id}", response_model=StatusActionResponse)
def delete_event_session_route(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return delete_or_disable_event_session(db, session_id, current_user)
