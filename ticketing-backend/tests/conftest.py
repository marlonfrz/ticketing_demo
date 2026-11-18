import os
import re
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.config import settings
from app.db.session import Base
from app.main import app
from app.models.role import Role
from app.models.event import Event
from app.models.event_session import EventSession
from app.models.user import User
from app.core.security import hash_password


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://ticketing:ticketing@postgres:5432/ticketing_test",
)


def _prepare_test_database() -> None:
    test_url = make_url(TEST_DATABASE_URL)
    app_url = make_url(settings.database_url)
    if test_url.set(password=None) == app_url.set(password=None):
        raise RuntimeError(
            "TEST_DATABASE_URL no puede apuntar a la base de datos de la aplicacion"
        )

    database_name = test_url.database or ""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", database_name):
        raise RuntimeError("El nombre de la base de datos de pruebas no es valido")

    admin_url = test_url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": database_name},
            ).scalar()
            if not exists:
                connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
    finally:
        admin_engine.dispose()


_prepare_test_database()
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def disable_email_delivery():
    original_value = settings.email_delivery_enabled
    settings.email_delivery_enabled = False
    yield
    settings.email_delivery_enabled = original_value


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # crea tablas al inicio de la sesión
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(bind=engine)

    yield

    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


@pytest.fixture(autouse=True)
def clean_db():
    # limpia datos entre tests
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))
    yield


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def create_roles(db):
    role_names = ["buyer", "promoter", "admin"]
    existing = {r.name for r in db.query(Role).all()}

    for role_name in role_names:
        if role_name not in existing:
            db.add(Role(name=role_name))

    db.commit()


def create_user_with_roles(db, email: str, password: str, full_name: str, roles: list[str]) -> User:
    create_roles(db)

    role_models = db.query(Role).filter(Role.name.in_(roles)).all()

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        is_active=True,
        status="active",
    )
    user.roles = role_models

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_event_with_session(
    db,
    promoter_id,
    *,
    title,
    description,
    location_name,
    location_address,
    starts_at,
    ends_at,
    capacity,
    status,
):
    event = Event(
        promoter_id=promoter_id,
        title=title,
        description=description,
        status=status,
    )
    db.add(event)
    db.flush()
    db.add(
        EventSession(
            event_id=event.id,
            location_name=location_name,
            location_address=location_address,
            starts_at=starts_at,
            ends_at=ends_at,
            capacity=capacity,
            status=status,
            display_order=1,
        )
    )
    db.commit()
    db.refresh(event)
    return event


def approve_event_for_test(event_id):
    with TestingSessionLocal() as db:
        event = db.query(Event).filter(Event.id == event_id).first()
        event.status = "draft"
        for session in event.sessions:
            if session.status == "not_reviewed":
                session.status = "draft"
        db.commit()


@pytest.fixture
def buyer_user(db):
    return create_user_with_roles(
        db=db,
        email="buyer@test.com",
        password="123456",
        full_name="Buyer Test",
        roles=["buyer"],
    )


@pytest.fixture
def promoter_user(db):
    return create_user_with_roles(
        db=db,
        email="promoter@test.com",
        password="123456",
        full_name="Promoter Test",
        roles=["promoter"],
    )


@pytest.fixture
def admin_user(db):
    return create_user_with_roles(
        db=db,
        email="admin@test.com",
        password="123456",
        full_name="Admin Test",
        roles=["admin"],
    )


@pytest.fixture
def buyer_token(client, buyer_user):
    res = client.post(
        "/auth/login",
        data={
            "username": "buyer@test.com",
            "password": "123456",
        },
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture
def promoter_token(client, promoter_user):
    res = client.post(
        "/auth/login",
        data={
            "username": "promoter@test.com",
            "password": "123456",
        },
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture
def admin_token(client, admin_user):
    res = client.post(
        "/auth/login",
        data={
            "username": "admin@test.com",
            "password": "123456",
        },
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]
