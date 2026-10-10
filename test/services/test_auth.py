from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.patient import Base
from app.models.user import User
from app.services.auth import bootstrap_admin, verify_password


def test_bootstrap_admin_is_idempotent_and_does_not_reset_password(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        assert bootstrap_admin(session, "Admin@Example.com", "first password")
        assert not bootstrap_admin(session, "admin@example.com", "second password")
        users = session.scalars(select(User)).all()
        assert len(users) == 1
        assert users[0].email == "admin@example.com"
        assert users[0].role == "admin"
        assert users[0].password_hash != "first password"
        assert verify_password("first password", users[0].password_hash)
        assert not verify_password("second password", users[0].password_hash)
        assert users[0].created_at.tzinfo is not None
        assert users[0].updated_at.tzinfo is not None


def test_admin_is_not_created_without_both_credentials(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        assert not bootstrap_admin(session, "", "password")
        assert not bootstrap_admin(session, "admin@example.com", "")
        assert session.scalars(select(User)).all() == []
