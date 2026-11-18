from conftest import create_roles
from app.models.user import User


def test_login_ok(client, buyer_user):
    response = client.post(
        "/auth/login",
        data={
            "username": "buyer@test.com",
            "password": "123456",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_fails_with_wrong_password(client, buyer_user):
    response = client.post(
        "/auth/login",
        data={
            "username": "buyer@test.com",
            "password": "bad-password",
        },
    )

    assert response.status_code in (401, 403), response.text


def test_me_returns_current_user(client, buyer_token, buyer_user):
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "buyer@test.com"
    assert "buyer" in data["roles"]


def test_public_registration_stores_contact_data(client, db):
    create_roles(db)
    response = client.post(
        "/auth/register",
        json={
            "email": "NewBuyer@Example.com",
            "full_name": "New Buyer",
            "phone": "+34 600 123 456",
            "country_code": "es",
            "password": "SecurePass!123",
            "accept_terms": True,
            "accept_privacy": True,
            "marketing_consent": True,
            "registration_source": "registration",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "newbuyer@example.com"
    assert data["phone"] == "+34600123456"
    assert data["country_code"] == "ES"
    assert data["marketing_consent"] is True
    assert data["roles"] == ["buyer"]

    user = db.query(User).filter(User.email == "newbuyer@example.com").one()
    assert user.accepted_terms_at is not None
    assert user.accepted_privacy_at is not None
    assert user.marketing_consent_at is not None
    assert user.marketing_consent_source == "registration"


def test_account_status_detects_existing_email_case_insensitively(
    client,
    buyer_user,
):
    existing_response = client.post(
        "/auth/account-status",
        json={"email": "BUYER@TEST.COM"},
    )
    missing_response = client.post(
        "/auth/account-status",
        json={"email": "missing@example.com"},
    )

    assert existing_response.status_code == 200, existing_response.text
    assert existing_response.json() == {"exists": True, "can_login": True}
    assert missing_response.status_code == 200, missing_response.text
    assert missing_response.json() == {"exists": False, "can_login": False}


def test_account_status_does_not_offer_login_for_deactivated_account(
    client,
    db,
    buyer_user,
):
    buyer_user.is_active = False
    buyer_user.status = "deactivated"
    db.commit()

    response = client.post(
        "/auth/account-status",
        json={"email": "buyer@test.com"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"exists": True, "can_login": False}


def test_forgot_password_does_not_reveal_whether_account_exists(client, buyer_user):
    existing_response = client.post(
        "/auth/forgot-password",
        json={"email": "buyer@test.com"},
    )
    missing_response = client.post(
        "/auth/forgot-password",
        json={"email": "missing@example.com"},
    )

    assert existing_response.status_code == 200, existing_response.text
    assert missing_response.status_code == 200, missing_response.text
    assert existing_response.json() == missing_response.json()


def test_public_registration_requires_phone(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "without-phone@example.com",
            "full_name": "Buyer Without Phone",
            "password": "SecurePass!123",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )

    assert response.status_code == 422, response.text


def test_public_registration_rejects_missing_legal_consent(client, db):
    create_roles(db)
    response = client.post(
        "/auth/register",
        json={
            "email": "no-consent@example.com",
            "full_name": "Buyer Without Consent",
            "phone": "+34600111222",
            "country_code": "ES",
            "password": "SecurePass!123",
            "accept_terms": False,
            "accept_privacy": True,
        },
    )

    assert response.status_code == 400, response.text
    assert "condiciones de uso" in response.json()["detail"]


def test_public_registration_does_not_enable_marketing_by_default(client, db):
    create_roles(db)
    response = client.post(
        "/auth/register",
        json={
            "email": "no-marketing@example.com",
            "full_name": "Buyer No Marketing",
            "phone": "+34600333444",
            "country_code": "ES",
            "password": "SecurePass!123",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )

    assert response.status_code == 200, response.text
    user = db.query(User).filter(User.email == "no-marketing@example.com").one()
    assert user.marketing_consent is False
    assert user.marketing_consent_at is None
    assert user.marketing_consent_source is None
