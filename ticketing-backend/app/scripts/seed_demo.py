import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
import app.db.base  # noqa: F401
from app.models.event import Event
from app.models.event_session import EventSession
from app.models.ticket_sale_group import TicketSaleGroup
from app.models.ticket_type import TicketType
from app.models.user import User


DEMO_NAMESPACE = uuid.UUID("6fe1aa27-0ee4-4862-a105-e8d594c85628")


@dataclass(frozen=True)
class DemoEventSpec:
    slug: str
    title: str
    description: str
    image_filename: str
    location_name: str
    location_address: str
    session_count: int
    base_capacity: int
    base_price: Decimal


DEMO_EVENTS = (
    DemoEventSpec(
        slug="volcanic-sunset",
        title="Atardecer entre volcanes",
        description="Una experiencia musical al aire libre entre paisajes volcánicos. Evento ficticio creado para probar el carrusel, la venta y la gestión de sesiones.",
        image_filename="demo-coast.webp",
        location_name="Espacio Volcánico Demo",
        location_address="La Orotava, Tenerife",
        session_count=1,
        base_capacity=420,
        base_price=Decimal("22.00"),
    ),
    DemoEventSpec(
        slug="lake-nights",
        title="Noches del lago",
        description="Dos noches de música tranquila junto al agua con propuestas gastronómicas y una zona premium.",
        image_filename="demo-lake.webp",
        location_name="Auditorio del Lago Demo",
        location_address="Puerto de la Cruz, Tenerife",
        session_count=2,
        base_capacity=560,
        base_price=Decimal("28.00"),
    ),
    DemoEventSpec(
        slug="forest-sounds",
        title="Bosque sonoro",
        description="Tres sesiones de música, naturaleza y arte lumínico en un recinto rodeado de bosque.",
        image_filename="demo-forest.webp",
        location_name="Parque Cultural del Bosque",
        location_address="Teror, Gran Canaria",
        session_count=3,
        base_capacity=680,
        base_price=Decimal("19.50"),
    ),
    DemoEventSpec(
        slug="blue-horizon",
        title="Horizonte azul",
        description="Festival de cuatro jornadas con artistas emergentes, actividades diurnas y conciertos al atardecer.",
        image_filename="demo-valley.webp",
        location_name="Recinto Horizonte Demo",
        location_address="Las Palmas de Gran Canaria",
        session_count=4,
        base_capacity=900,
        base_price=Decimal("34.00"),
    ),
    DemoEventSpec(
        slug="summit-festival",
        title="Cumbre Festival",
        description="Cinco fechas para descubrir música en directo y gastronomía local con vistas a la montaña.",
        image_filename="demo-mountains.webp",
        location_name="Mirador Cultural Demo",
        location_address="Vilaflor, Tenerife",
        session_count=5,
        base_capacity=1150,
        base_price=Decimal("39.00"),
    ),
    DemoEventSpec(
        slug="living-valley",
        title="Valle Vivo",
        description="Seis sesiones de un encuentro cultural para todos los públicos con música, talleres y zona familiar.",
        image_filename="demo-meadow.webp",
        location_name="Finca Cultural del Valle",
        location_address="Arucas, Gran Canaria",
        session_count=6,
        base_capacity=1350,
        base_price=Decimal("17.00"),
    ),
)


def _demo_uuid(entity_type: str, slug: str) -> uuid.UUID:
    return uuid.uuid5(DEMO_NAMESPACE, f"{entity_type}:{slug}")


def _build_ticket_types(
    event: Event,
    session: EventSession,
    spec: DemoEventSpec,
    session_index: int,
    sale_starts_at: datetime,
) -> None:
    group_specs = (
        ("Acceso general", 1),
        ("Experiencias", 2),
    )
    groups: dict[str, TicketSaleGroup] = {}

    for group_name, display_order in group_specs:
        group_slug = f"{spec.slug}-{session_index}-{display_order}"
        group = TicketSaleGroup(
            id=_demo_uuid("sale-group", group_slug),
            event_id=event.id,
            session_id=session.id,
            name=group_name,
            strategy="stock_cascade",
            is_active=True,
            sale_starts_at=sale_starts_at,
            sale_ends_at=session.starts_at - timedelta(hours=1),
            status="published",
            display_order=display_order,
        )
        groups[group_name] = group
        session.sale_groups.append(group)

    capacity = session.capacity
    session_price_adjustment = Decimal(session_index - 1)
    ticket_specs = (
        (
            "Entrada lanzamiento",
            "Primer tramo promocional con stock limitado.",
            spec.base_price - Decimal("4.00") + session_price_adjustment,
            2,
            "Acceso general",
            1,
        ),
        (
            "Entrada general",
            "Segundo tramo de acceso general.",
            spec.base_price + session_price_adjustment,
            max(1, int(capacity * 0.45)),
            "Acceso general",
            2,
        ),
        (
            "Entrada último tramo",
            "Tramo final de acceso general.",
            spec.base_price + Decimal("5.00") + session_price_adjustment,
            max(1, int(capacity * 0.25)),
            "Acceso general",
            3,
        ),
        (
            "Experiencia premium lanzamiento",
            "Primer tramo promocional de la experiencia premium.",
            spec.base_price + Decimal("18.00") + session_price_adjustment,
            1,
            "Experiencias",
            1,
        ),
        (
            "Experiencia premium",
            "Acceso preferente y zona reservada.",
            spec.base_price + Decimal("24.00") + session_price_adjustment,
            max(1, int(capacity * 0.10)),
            "Experiencias",
            2,
        ),
    )

    for name, description, price, stock, group_name, sale_order in ticket_specs:
        ticket_slug = f"{spec.slug}-{session_index}-{group_name}-{sale_order}"
        session.ticket_types.append(
            TicketType(
                id=_demo_uuid("ticket-type", ticket_slug),
                event_id=event.id,
                session_id=session.id,
                sale_group_id=groups[group_name].id,
                sale_order=sale_order,
                display_order=sale_order,
                name=name,
                description=description,
                price=price,
                currency="EUR",
                stock=stock,
                sold_count=0,
                max_per_purchase=10,
                sale_starts_at=sale_starts_at,
                sale_ends_at=session.starts_at - timedelta(hours=1),
                is_active=True,
                status="published",
                sale_unlocked_at=(sale_starts_at if sale_order == 1 else None),
            )
        )


def seed_demo_data(db: Session) -> int:
    if not settings.demo_data_enabled:
        return 0

    promoter = db.query(User).filter(User.is_superadmin.is_(True)).first()
    if not promoter:
        raise RuntimeError("A superadmin is required before seeding demo data")

    now = datetime.now(timezone.utc)
    published_at = now - timedelta(days=1)
    created_events = 0

    for event_index, spec in enumerate(DEMO_EVENTS, start=1):
        event_id = _demo_uuid("event", spec.slug)
        if db.get(Event, event_id):
            continue

        event = Event(
            id=event_id,
            promoter_id=promoter.id,
            title=spec.title,
            description=spec.description,
            publish_at=published_at,
            status="published",
            platform_fee_type="percentage",
            platform_fee_value=Decimal("10.00"),
            image_url=f"/demo-media/events/{spec.image_filename}",
        )

        first_start = now + timedelta(days=12 + event_index * 16)
        for session_index in range(1, spec.session_count + 1):
            starts_at = first_start + timedelta(days=(session_index - 1) * 3)
            session = EventSession(
                id=_demo_uuid("session", f"{spec.slug}-{session_index}"),
                event_id=event.id,
                title=f"Sesión {session_index}",
                location_name=spec.location_name,
                location_address=spec.location_address,
                starts_at=starts_at,
                ends_at=starts_at + timedelta(hours=4),
                capacity=spec.base_capacity + (session_index - 1) * 40,
                status="published",
                publish_at=published_at,
                tickets_publish_at=published_at,
                tickets_activated_at=published_at,
                display_order=session_index,
            )
            _build_ticket_types(event, session, spec, session_index, published_at)
            event.sessions.append(session)

        db.add(event)
        created_events += 1

    db.commit()
    return created_events
