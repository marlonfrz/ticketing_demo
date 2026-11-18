from datetime import datetime, timedelta, timezone

from app.models.event import Event
from app.models.order import Order
from app.models.ticket import Ticket
from app.models.ticket_type import TicketType
from app.models.ticket_validation import TicketValidation
import app.services.event_service as event_service_module
from app.services.event_notification_service import build_event_status_email_html
from conftest import create_event_with_session


def create_draft_event(db, promoter_user, title="Evento Estado", capacity=500, starts_in_days=10):
    starts_at = datetime.now(timezone.utc) + timedelta(days=starts_in_days)
    ends_at = starts_at + timedelta(hours=5)

    event = create_event_with_session(
        db,
        promoter_user.id,
        title=title,
        description="Evento de prueba para estados",
        location_name="Sala Estados",
        location_address="Calle Estados 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=capacity,
        status="draft",
    )

    return {"id": str(event.id)}


def test_promoter_cannot_publish_draft_event(client, db, promoter_user, promoter_token):
    event = create_draft_event(db, promoter_user)

    response = client.post(
        f"/events/{event['id']}/publish",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 403, response.text
    assert "administrador" in response.json()["detail"].lower()


def test_promoter_can_submit_event_for_review_after_tickets(client, db, promoter_user, promoter_token):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento para revisar",
        description="Listo para revisión",
        location_name="Sala Review",
        location_address="Calle Review 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="not_reviewed",
    )
    ticket_type = TicketType(
        event_id=event.id,
        name="General",
        description="Entrada general",
        price=20,
        currency="EUR",
        stock=100,
        sold_count=0,
        max_per_purchase=4,
        is_active=True,
        status="draft",
    )
    db.add(ticket_type)
    db.commit()

    response = client.post(
        f"/events/{event.id}/submit-review",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "in_review"


def test_admin_can_approve_event_review_to_draft(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento en revisión",
        description="Admin debe aprobar",
        location_name="Sala Admin Review",
        location_address="Calle Admin Review 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="in_review",
    )
    response = client.post(
        f"/admin/events/{event.id}/approve-review",
        json={
            "platform_fee_type": "percentage",
            "platform_fee_value": "10.00",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "draft"


def test_admin_can_approve_session_review_with_existing_event_fee(
    client,
    db,
    admin_token,
    promoter_user,
):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento con sesion en revision",
        description="Admin aprueba la sesion desde la gestion",
        location_name="Sala Sesion Review",
        location_address="Calle Sesion Review 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="draft",
    )
    event.platform_fee_type = "percentage"
    event.platform_fee_value = 10
    session = event.sessions[0]
    session.status = "in_review"
    db.commit()

    response = client.post(
        f"/admin/event-sessions/{session.id}/approve-review",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "draft"


def test_promoter_cannot_publish_other_promoter_event(client, db, promoter_user, admin_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    event = create_event_with_session(
        db,
        admin_user.id,
        title="Evento ajeno",
        description="No debería publicarlo otro promoter",
        location_name="Sala Ajena",
        location_address="Calle Ajena 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="draft",
    )
    login_response = client.post(
        "/auth/login",
        data={
            "username": "promoter@test.com",
            "password": "123456",
        },
    )
    assert login_response.status_code == 200, login_response.text
    promoter_token = login_response.json()["access_token"]

    response = client.post(
        f"/events/{event.id}/publish",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 403, response.text


def test_admin_can_publish_other_promoter_event(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicable por admin",
        description="Admin puede publicarlo",
        location_name="Sala Admin",
        location_address="Calle Admin 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="draft",
    )
    published_after = datetime.now(timezone.utc)
    response = client.post(
        f"/events/{event.id}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "published"
    db.refresh(event)
    assert event.publish_at is not None
    assert event.publish_at >= published_after


def test_cannot_publish_event_that_is_not_draft(client, db, promoter_user, admin_token):
    event = create_draft_event(db, promoter_user)

    first_publish = client.post(
        f"/events/{event['id']}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert first_publish.status_code == 200, first_publish.text

    second_publish = client.post(
        f"/events/{event['id']}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert second_publish.status_code == 400, second_publish.text
    assert "draft" in second_publish.json()["detail"].lower()


def test_promoter_cannot_publish_single_approved_session(client, db, promoter_user, promoter_token):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado con sesion aprobada",
        description="El promotor no debe publicar sesiones",
        location_name="Sala Sesion",
        location_address="Calle Sesion 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    session = event.sessions[0]
    session.status = "draft"
    db.commit()

    response = client.post(
        f"/event-sessions/{session.id}/publish",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 403, response.text
    assert "administrador" in response.json()["detail"].lower()


def test_promoter_cannot_publish_all_approved_sessions(client, db, promoter_user, promoter_token):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado con sesiones aprobadas",
        description="El promotor no debe publicar sesiones aprobadas",
        location_name="Sala Sesiones",
        location_address="Calle Sesiones 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    event.sessions[0].status = "draft"
    db.commit()

    response = client.post(
        f"/events/{event.id}/sessions/publish",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 403, response.text
    assert "administrador" in response.json()["detail"].lower()


def test_promoter_cannot_unpublish_published_event_without_activity(client, db, promoter_user, promoter_token):
    event = create_draft_event(db, promoter_user)
    event_model = db.query(Event).filter(Event.id == event["id"]).first()
    event_model.status = "published"
    db.commit()

    unpublish_response = client.post(
        f"/events/{event['id']}/unpublish",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert unpublish_response.status_code == 403, unpublish_response.text
    assert "administrador" in unpublish_response.json()["detail"].lower()


def test_cannot_unpublish_event_that_has_already_started(client, db, promoter_user):
    starts_at = datetime.now(timezone.utc) - timedelta(hours=1)
    ends_at = datetime.now(timezone.utc) + timedelta(hours=4)

    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento empezado",
        description="No debería despublicarse",
        location_name="Sala Empezada",
        location_address="Calle Empezada 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="published",
    )
    login_response = client.post(
        "/auth/login",
        data={
            "username": "promoter@test.com",
            "password": "123456",
        },
    )
    assert login_response.status_code == 200, login_response.text
    promoter_token = login_response.json()["access_token"]

    response = client.post(
        f"/events/{event.id}/unpublish",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 403, response.text
    assert "administrador" in response.json()["detail"].lower()


def test_cannot_unpublish_event_with_paid_orders(client, db, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento con ventas",
        description="No debería despublicarse",
        location_name="Sala Ventas",
        location_address="Calle Ventas 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="published",
    )
    order = Order(
        buyer_id=promoter_user.id,
        event_id=event.id,
        status="paid",
        total_amount=100,
        currency="EUR",
    )
    db.add(order)
    db.commit()

    login_response = client.post(
        "/auth/login",
        data={
            "username": "promoter@test.com",
            "password": "123456",
        },
    )
    assert login_response.status_code == 200, login_response.text
    promoter_token = login_response.json()["access_token"]

    response = client.post(
        f"/events/{event.id}/unpublish",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 403, response.text
    assert "administrador" in response.json()["detail"].lower()


def test_cannot_archive_published_event(client, db, promoter_user, admin_token, promoter_token):
    event = create_draft_event(db, promoter_user)

    publish_response = client.post(
        f"/events/{event['id']}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response.status_code == 200, publish_response.text

    archive_response = client.delete(
        f"/admin/events/{event['id']}",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    # Si esta ruta es solo admin, puede responder 403.
    assert archive_response.status_code in (400, 403), archive_response.text


def test_promoter_cannot_delete_approved_draft_event(client, db, promoter_user, promoter_token):
    event = create_draft_event(db, promoter_user)

    response = client.delete(
        f"/events/{event['id']}",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 403, response.text
    assert "aprobados" in response.json()["detail"].lower()


def test_promoter_can_permanently_delete_unreviewed_event(
    client,
    db,
    promoter_user,
    promoter_token,
    monkeypatch,
):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento preliminar borrable",
        description="Todavia no ha sido revisado",
        location_name="Sala preliminar",
        location_address="Calle preliminar 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="not_reviewed",
    )
    event_id = str(event.id)
    sent_notifications = []
    monkeypatch.setattr(
        event_service_module,
        "send_event_status_email",
        lambda deleted_event: sent_notifications.append(deleted_event.id),
    )

    response = client.delete(
        f"/events/{event_id}",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "deleted"
    assert db.query(Event).filter(Event.id == event_id).first() is None
    assert sent_notifications == []


def test_promoter_can_delete_unreviewed_event_after_its_planned_start(
    client,
    db,
    promoter_user,
    promoter_token,
):
    starts_at = datetime.now(timezone.utc) - timedelta(days=2)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento preliminar caducado",
        description="Nunca se publico",
        location_name="Sala preliminar",
        location_address="Calle preliminar 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="not_reviewed",
    )
    event_id = str(event.id)

    response = client.delete(
        f"/events/{event_id}",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    assert db.query(Event).filter(Event.id == event_id).first() is None


def test_deleted_event_email_does_not_expose_archived_status(db, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento borrado",
        description="Evento aprobado que se conserva internamente",
        location_name="Sala borrada",
        location_address="Calle borrada 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="archived",
    )

    html = build_event_status_email_html(event, promoter_user.full_name)

    assert "ha sido borrado" in html
    assert "archivad" not in html.lower()
    assert f"/events/{event.id}/manage" not in html


def test_cannot_delete_session_when_event_is_not_draft(client, db, promoter_user, promoter_token):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento con sesion no borrable",
        description="La sesion no debe poder borrarse",
        location_name="Sala no borrable",
        location_address="Calle no borrable 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    session_id = event.sessions[0].id

    response = client.delete(
        f"/event-sessions/{session_id}",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 400, response.text
    assert "draft" in response.json()["detail"].lower()


def test_promoter_cannot_edit_finished_session(
    client,
    db,
    promoter_user,
    promoter_token,
):
    starts_at = datetime.now(timezone.utc) - timedelta(days=2)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento con sesion finalizada",
        description="La sesion no debe poder editarse",
        location_name="Sala finalizada",
        location_address="Calle finalizada 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    session = event.sessions[0]
    session.status = "finished"
    db.commit()

    response = client.put(
        f"/event-sessions/{session.id}",
        headers={"Authorization": f"Bearer {promoter_token}"},
        json={"location_name": "Lugar modificado"},
    )

    assert response.status_code == 403, response.text
    assert "finalizada" in response.json()["detail"].lower()


def test_promoter_can_edit_cancelled_session(
    client,
    db,
    promoter_user,
    promoter_token,
):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento con sesion corregible",
        description="La sesion cancelada se puede corregir",
        location_name="Sala corregible",
        location_address="Calle corregible 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="draft",
    )
    session = event.sessions[0]
    session.status = "cancelled"
    db.commit()

    response = client.put(
        f"/event-sessions/{session.id}",
        headers={"Authorization": f"Bearer {promoter_token}"},
        json={"location_name": "Lugar corregido"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["location_name"] == "Lugar corregido"


def test_promoter_can_resubmit_cancelled_session_for_review(
    client,
    db,
    promoter_user,
    promoter_token,
):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento con sesion reenviable",
        description="La sesion cancelada puede volver a revision",
        location_name="Sala reenviable",
        location_address="Calle reenviable 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="draft",
    )
    session = event.sessions[0]
    session.status = "cancelled"
    ticket_type = TicketType(
        event_id=event.id,
        session_id=session.id,
        name="General",
        description="Entrada general",
        price=20,
        currency="EUR",
        stock=100,
        sold_count=0,
        max_per_purchase=4,
        is_active=True,
        status="draft",
    )
    db.add(ticket_type)
    db.commit()

    response = client.post(
        f"/event-sessions/{session.id}/submit-review",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "in_review"


def test_promoter_created_session_in_draft_event_requires_review(
    client,
    db,
    promoter_user,
    promoter_token,
):
    event = create_draft_event(db, promoter_user)
    starts_at = datetime.now(timezone.utc) + timedelta(days=20)

    response = client.post(
        f"/events/{event['id']}/sessions",
        headers={"Authorization": f"Bearer {promoter_token}"},
        json={
            "location_name": "Nueva fecha",
            "location_address": "Calle nueva 123",
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=5)).isoformat(),
            "capacity": 300,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "not_reviewed"


def test_finished_session_can_be_duplicated_as_a_new_unreviewed_session(
    client,
    db,
    promoter_user,
    promoter_token,
):
    starts_at = datetime.now(timezone.utc) - timedelta(days=2)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento finalizado para nueva fecha",
        description="Debe poder recuperar una nueva sesion",
        location_name="Sala original",
        location_address="Calle original 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="finished",
    )
    source = event.sessions[0]
    source.publish_at = starts_at - timedelta(days=5)
    source.tickets_publish_at = starts_at - timedelta(days=5)
    ticket_type = TicketType(
        event_id=event.id,
        session_id=source.id,
        name="General",
        price=20,
        currency="EUR",
        stock=100,
        sold_count=25,
        max_per_purchase=4,
        is_active=True,
        status="published",
        sale_starts_at=starts_at - timedelta(days=5),
        sale_ends_at=starts_at + timedelta(hours=5),
    )
    db.add(ticket_type)
    db.commit()

    response = client.post(
        f"/event-sessions/{source.id}/duplicate",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    duplicated = response.json()
    assert duplicated["status"] == "not_reviewed"
    assert duplicated["publish_at"] is None
    assert duplicated["tickets_publish_at"] is None

    db.refresh(event)
    assert event.status == "draft"
    copied_ticket = (
        db.query(TicketType)
        .filter(TicketType.session_id == duplicated["id"])
        .one()
    )
    assert copied_ticket.status == "draft"
    assert copied_ticket.sold_count == 0
    assert copied_ticket.sale_starts_at is None
    assert copied_ticket.sale_ends_at is None


def test_admin_cannot_archive_published_event(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado",
        description="No debería archivarse",
        location_name="Sala Publicada",
        location_address="Calle Publicada 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="published",
    )
    response = client.delete(
        f"/admin/events/{event.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400, response.text
    assert "publicado" in response.json()["detail"].lower()


def test_admin_can_archive_safe_draft_event(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento archivable",
        description="Debería archivarse",
        location_name="Sala Archivo",
        location_address="Calle Archivo 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="draft",
    )
    response = client.delete(
        f"/admin/events/{event.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "deleted"
    assert data["entity_type"] == "event"
    db.refresh(event)
    assert event.status == "archived"


def test_admin_can_archive_never_published_draft_after_planned_start(
    client,
    db,
    admin_token,
    promoter_user,
):
    starts_at = datetime.now(timezone.utc) - timedelta(days=2)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Borrador con fecha pasada",
        description="Nunca se publico",
        location_name="Sala Archivo",
        location_address="Calle Archivo 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="draft",
    )

    response = client.delete(
        f"/events/{event.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    db.refresh(event)
    assert event.status == "archived"


def test_admin_cannot_archive_started_event_that_was_unpublished(
    client,
    db,
    admin_token,
    promoter_user,
):
    starts_at = datetime.now(timezone.utc) - timedelta(days=2)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento despublicado iniciado",
        description="Estuvo publicado",
        location_name="Sala Archivo",
        location_address="Calle Archivo 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="unpublished",
    )

    response = client.delete(
        f"/events/{event.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400, response.text
    assert "empezado" in response.json()["detail"].lower()


def test_admin_cannot_archive_event_with_tickets(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento con tickets",
        description="No debería archivarse",
        location_name="Sala Tickets",
        location_address="Calle Tickets 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="draft",
    )
    ticket_type = TicketType(
        event_id=event.id,
        name="General",
        description="Entrada general",
        price=20,
        currency="EUR",
        stock=100,
        sold_count=0,
        max_per_purchase=4,
        is_active=True,
        status="active",
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(ticket_type)

    order = Order(
        buyer_id=promoter_user.id,
        event_id=event.id,
        status="pending",
        total_amount=20,
        currency="EUR",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    ticket = Ticket(
        order_id=order.id,
        event_id=event.id,
        ticket_type_id=ticket_type.id,
        owner_user_id=promoter_user.id,
        ticket_code="TEST-CODE-001",
        qr_token="TEST-QR-001",
        status="active",
        is_valid=True,
    )
    db.add(ticket)
    db.commit()

    response = client.delete(
        f"/admin/events/{event.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400, response.text
    assert "tickets" in response.json()["detail"].lower()
