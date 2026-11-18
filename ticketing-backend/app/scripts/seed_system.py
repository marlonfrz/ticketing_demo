from app.core.startup import seed_roles, seed_superadmin
from app.db.session import SessionLocal
from app.scripts.seed_demo import seed_demo_data


def main() -> None:
    with SessionLocal() as db:
        seed_roles(db)
        seed_superadmin(db)
        seed_demo_data(db)


if __name__ == "__main__":
    main()
