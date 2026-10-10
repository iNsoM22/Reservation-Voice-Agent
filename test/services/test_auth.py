from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.patient import Base
from app.models.user import User
from app.services.auth import bootstrap_admin, hash_password, verify_password


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


def test_bootstrap_admin_loses_duplicate_email_race_without_resetting_password(
    tmp_path,
):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    Base.metadata.create_all(engine)

    class LosingBootstrapSession(Session):
        def add(self, instance, *, _warn=True):
            if isinstance(instance, User):
                with Session(engine) as competing_session:
                    competing_session.add(
                        User(
                            email=instance.email,
                            password_hash=hash_password("winning password"),
                            role="admin",
                        )
                    )
                    competing_session.commit()
            super().add(instance, _warn=_warn)

    with LosingBootstrapSession(engine) as session:
        assert not bootstrap_admin(session, "admin@example.com", "losing password")

    with Session(engine) as session:
        users = session.scalars(select(User)).all()
        assert len(users) == 1
        assert verify_password("winning password", users[0].password_hash)
        assert not verify_password("losing password", users[0].password_hash)
