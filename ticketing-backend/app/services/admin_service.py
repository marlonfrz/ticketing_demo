from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.order import Order
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.user import User
from app.models.ticket_type import TicketType
from app.schemas.admin import AdminUpdateEventRequest
from app.schemas.event import ALLOWED_EVENT_STATUSES
from app.core.security import hash_password
from app.services.auth_service import validate_password_strength


ALLOWED_ADMIN_ROLES = {"buyer", "promoter", "admin"}
ADMIN_SEARCH_PAGE_SIZE = 10


def _has_role(user: User, role_name: str) -> bool:
    return any(role.name == role_name for role in user.roles)


def _serialize_admin_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "country_code": user.country_code,
        "is_active": user.is_active,
        "status": user.status,
        "roles": [role.name for role in user.roles],
        "is_superadmin": user.is_superadmin,
    }


def _serialize_event_promoter(event: Event) -> dict | None:
    if not event.promoter:
        return None

    return {
        "id": str(event.promoter.id),
        "email": event.promoter.email,
        "full_name": event.promoter.full_name,
    }


def _event_total_session_capacity(event: Event) -> int:
    return sum(session.capacity or 0 for session in event.sessions)


def _serialize_review_event(event: Event, session: EventSession | None = None) -> dict:
    return {
        "id": str(event.id),
        "promoter_id": str(event.promoter_id),
        "promoter": _serialize_event_promoter(event),
        "review_entity_type": "session" if session else "event",
        "review_entity_id": str(session.id) if session else str(event.id),
        "session": {
            "id": str(session.id),
            "title": session.title,
            "location_name": session.location_name,
            "starts_at": session.starts_at,
            "status": session.status,
            "capacity": session.capacity,
        } if session else None,
        "title": event.title,
        "location_name": event.location_name,
        "starts_at": event.starts_at,
        "status": event.status,
        "capacity": _event_total_session_capacity(event),
        "platform_fee_type": event.platform_fee_type,
        "platform_fee_value": event.platform_fee_value,
        "created_at": event.created_at,
    }


def _serialize_admin_event(event: Event) -> dict:
    return {
        "id": str(event.id),
        "promoter_id": str(event.promoter_id),
        "promoter": _serialize_event_promoter(event),
        "title": event.title,
        "location_name": event.location_name,
        "starts_at": event.starts_at,
        "status": event.status,
        "capacity": _event_total_session_capacity(event),
        "platform_fee_type": event.platform_fee_type,
        "platform_fee_value": event.platform_fee_value,
        "created_at": event.created_at,
    }


def _pagination_response(items: list[dict], total: int, page: int, page_size: int) -> dict:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def _normalize_page(page: int) -> int:
    return max(1, page or 1)


def _normalize_page_size(page_size: int) -> int:
    if page_size <= 0:
        return ADMIN_SEARCH_PAGE_SIZE
    return min(page_size, ADMIN_SEARCH_PAGE_SIZE)


def _get_role_or_fail(db: Session, role_name: str) -> Role:
    role = db.query(Role).filter(Role.name == role_name).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rol {role_name} no configurado en base de datos",
        )

    return role


def get_admin_dashboard(db: Session) -> dict:
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_events = db.query(func.count(Event.id)).scalar() or 0
    pending_event_reviews = (
        db.query(func.count(Event.id))
        .filter(
            Event.status == "in_review",
            ~Event.sessions.any(EventSession.status == "in_review"),
        )
        .scalar()
        or 0
    )
    pending_session_reviews = (
        db.query(func.count(EventSession.id))
        .filter(EventSession.status == "in_review")
        .scalar()
        or 0
    )
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_paid_orders = db.query(func.count(Order.id)).filter(Order.status == "paid").scalar() or 0
    total_revenue = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status == "paid")
        .scalar()
        or Decimal("0.00")
    )
    total_tickets = db.query(func.count(Ticket.id)).scalar() or 0
    total_validated_tickets = (
        db.query(func.count(Ticket.id))
        .filter(Ticket.status == "used")
        .scalar()
        or 0
    )

    return {
        "total_users": int(total_users),
        "total_events": int(total_events),
        "pending_event_reviews": int(pending_event_reviews) + int(pending_session_reviews),
        "total_orders": int(total_orders),
        "total_paid_orders": int(total_paid_orders),
        "total_revenue": total_revenue,
        "total_tickets": int(total_tickets),
        "total_validated_tickets": int(total_validated_tickets),
    }


def list_users_admin(db: Session) -> list[dict]:
    users = (
        db.query(User)
        .options(joinedload(User.roles))
        .order_by(User.email.asc())
        .all()
    )

    return [_serialize_admin_user(user) for user in users]


def search_users_admin(
    db: Session,
    q: str | None = None,
    role: str | None = None,
    page: int = 1,
    page_size: int = ADMIN_SEARCH_PAGE_SIZE,
) -> dict:
    page = _normalize_page(page)
    page_size = _normalize_page_size(page_size)
    query = db.query(User).options(joinedload(User.roles))

    term = (q or "").strip()
    if term:
        pattern = f"%{term.lower()}%"
        query = query.filter(
            (User.email.ilike(pattern))
            | (User.full_name.ilike(pattern))
        )

    normalized_role = (role or "").strip().lower()
    if normalized_role:
        query = query.filter(User.roles.any(Role.name == normalized_role))

    total = query.count()
    users = (
        query.order_by(User.full_name.asc(), User.email.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return _pagination_response(
        [_serialize_admin_user(user) for user in users],
        total,
        page,
        page_size,
    )

def list_events_admin(db: Session) -> list[dict]:
    events = (
        db.query(Event)
        .options(joinedload(Event.promoter))
        .order_by(Event.created_at.desc())
        .all()
    )

    return [_serialize_admin_event(event) for event in events]


def search_events_admin(
    db: Session,
    q: str | None = None,
    event_status: str | None = None,
    page: int = 1,
    page_size: int = ADMIN_SEARCH_PAGE_SIZE,
) -> dict:
    page = _normalize_page(page)
    page_size = _normalize_page_size(page_size)
    query = db.query(Event).options(joinedload(Event.promoter))

    term = (q or "").strip()
    if term:
        query = query.filter(Event.title.ilike(f"%{term.lower()}%"))

    normalized_status = (event_status or "").strip().lower()
    if normalized_status:
        query = query.filter(Event.status == normalized_status)

    total = query.count()
    events = (
        query.order_by(Event.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return _pagination_response(
        [_serialize_admin_event(event) for event in events],
        total,
        page,
        page_size,
    )


def list_promoter_events_admin(db: Session, promoter_id: str) -> dict:
    promoter = (
        db.query(User)
        .options(joinedload(User.roles))
        .filter(User.id == promoter_id)
        .first()
    )

    if not promoter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotor no encontrado",
        )

    events = (
        db.query(Event)
        .options(joinedload(Event.promoter))
        .filter(Event.promoter_id == promoter.id)
        .order_by(Event.created_at.desc())
        .all()
    )

    return {
        "promoter": _serialize_admin_user(promoter),
        "events": [_serialize_admin_event(event) for event in events],
    }


def list_event_reviews_admin(db: Session) -> list[dict]:
    event_reviews = (
        db.query(Event)
        .options(joinedload(Event.promoter))
        .filter(
            Event.status == "in_review",
            ~Event.sessions.any(EventSession.status == "in_review"),
        )
        .order_by(Event.updated_at.desc())
        .all()
    )
    session_reviews = (
        db.query(EventSession)
        .join(Event, Event.id == EventSession.event_id)
        .options(joinedload(EventSession.event).joinedload(Event.promoter))
        .filter(EventSession.status == "in_review")
        .order_by(EventSession.updated_at.desc())
        .all()
    )

    event_items = [_serialize_review_event(event) for event in event_reviews]
    session_items = [_serialize_review_event(session.event, session) for session in session_reviews]
    return event_items + session_items


def update_user_roles_admin(db: Session, user_id: str, roles: list[str], acted_by_user: User) -> dict:
    user = (
        db.query(User)
        .options(joinedload(User.roles))
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    normalized_roles = {role.strip().lower() for role in roles if role.strip()}
    
    target_has_admin = any(role.name == "admin" for role in user.roles)
    wants_admin = "admin" in normalized_roles

    if (target_has_admin or wants_admin) and not acted_by_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el superadmin puede asignar o modificar roles de administradores",
        )

    if user.is_superadmin and user.id != acted_by_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes modificar el superadmin",
        )

    if user.is_superadmin and "admin" not in normalized_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El superadmin debe conservar el rol admin",
        )

    if not normalized_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes indicar al menos un rol",
        )

    invalid_roles = normalized_roles - ALLOWED_ADMIN_ROLES
    if invalid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Roles inválidos: {', '.join(sorted(invalid_roles))}",
        )

    role_models = db.query(Role).filter(Role.name.in_(normalized_roles)).all()

    if len(role_models) != len(normalized_roles):
        found = {role.name for role in role_models}
        missing = normalized_roles - found
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Roles no encontrados en base de datos: {', '.join(sorted(missing))}",
        )

    user.roles = role_models
    db.commit()
    db.refresh(user)

    return _serialize_admin_user(user)


def update_event_admin(db: Session, event_id: str, data: AdminUpdateEventRequest) -> dict:
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("capacity", None)

    if "status" in update_data and update_data["status"] not in ALLOWED_EVENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado de evento inválido",
        )

    starts_at = update_data.get("starts_at", event.starts_at)
    ends_at = update_data.get("ends_at", event.ends_at)

    if ends_at and ends_at < starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin no puede ser anterior a la de inicio",
        )

    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)

    return {
        "id": str(event.id),
        "promoter_id": str(event.promoter_id),
        "promoter": _serialize_event_promoter(event),
        "title": event.title,
        "location_name": event.location_name,
        "starts_at": event.starts_at,
        "status": event.status,
        "capacity": _event_total_session_capacity(event),
        "platform_fee_type": event.platform_fee_type,
        "platform_fee_value": event.platform_fee_value,
        "created_at": event.created_at,
    }
    
def create_user_admin(
    db: Session,
    acted_by_user: User,
    email: str,
    full_name: str,
    password: str,
    phone: str,
    country_code: str,
    role_names: list[str],
) -> dict:
    validate_password_strength(password)
    if not _has_role(acted_by_user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un admin puede crear usuarios",
        )

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese email",
        )

    normalized_roles = []
    for role_name in role_names:
        role_name = role_name.strip().lower()
        if role_name and role_name not in normalized_roles:
            normalized_roles.append(role_name)

    if "buyer" not in normalized_roles:
        normalized_roles.insert(0, "buyer")

    role_models = [_get_role_or_fail(db, role_name) for role_name in normalized_roles]

    user = User(
        email=email,
        full_name=full_name,
        phone=phone.strip(),
        country_code=country_code.strip().upper(),
        password_hash=hash_password(password),
        is_active=True,
        status="active",
        is_superadmin=False,
    )

    user.roles = role_models

    db.add(user)
    db.commit()
    db.refresh(user)

    return _serialize_admin_user(user)


def create_promoter_admin(
    db: Session,
    acted_by_user: User,
    email: str,
    full_name: str,
    password: str,
    phone: str,
    country_code: str,
) -> dict:
    return create_user_admin(
        db=db,
        acted_by_user=acted_by_user,
        email=email,
        full_name=full_name,
        password=password,
        phone=phone,
        country_code=country_code,
        role_names=["buyer", "promoter"],
    )


def create_admin_user(
    db: Session,
    acted_by_user: User,
    email: str,
    full_name: str,
    password: str,
    phone: str,
    country_code: str,
) -> dict:
    validate_password_strength(password)
    if not acted_by_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el superadmin puede crear otros admins",
        )

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese email",
        )

    buyer_role = _get_role_or_fail(db, "buyer")
    admin_role = _get_role_or_fail(db, "admin")

    user = User(
        email=email,
        full_name=full_name,
        phone=phone.strip(),
        country_code=country_code.strip().upper(),
        password_hash=hash_password(password),
        is_active=True,
        status="active",
        is_superadmin=False,
    )

    user.roles = [buyer_role, admin_role]

    db.add(user)
    db.commit()
    db.refresh(user)

    return _serialize_admin_user(user)
