from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User


def seed_roles(db: Session):
    existing_roles = {role.name for role in db.query(Role).all()}
    required_roles = {"buyer", "promoter", "admin"}

    for role_name in required_roles - existing_roles:
        db.add(Role(name=role_name))

    db.commit()


def seed_superadmin(db: Session):
    if not settings.superadmin_email or not settings.superadmin_password:
        return

    admin_role = db.query(Role).filter(Role.name == "admin").first()
    buyer_role = db.query(Role).filter(Role.name == "buyer").first()

    if not admin_role:
        return

    existing_superadmin = (
        db.query(User)
        .filter(User.is_superadmin == True)
        .first()
    )

    if existing_superadmin:
        return

    existing_user = (
        db.query(User)
        .filter(User.email == settings.superadmin_email)
        .first()
    )

    if existing_user:
        existing_user.is_superadmin = True
        existing_user.is_active = True
        existing_user.status = "active"

        current_roles = {role.name for role in existing_user.roles}

        if "admin" not in current_roles:
            existing_user.roles.append(admin_role)

        if buyer_role and "buyer" not in current_roles:
            existing_user.roles.append(buyer_role)

        db.commit()
        return

    superadmin = User(
        email=settings.superadmin_email,
        full_name=settings.superadmin_full_name or "Super Admin",
        password_hash=hash_password(settings.superadmin_password),
        is_active=True,
        status="active",
        is_superadmin=True,
    )

    superadmin.roles.append(admin_role)

    if buyer_role:
        superadmin.roles.append(buyer_role)

    db.add(superadmin)
    db.commit()
