from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class BookingEvent(Base):
    __tablename__ = "booking_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    invitee_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True, index=True)
    event_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    old_invitee_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    new_invitee_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    scheduled_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    canceled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class EmailOutbox(Base):
    __tablename__ = "email_outbox"
    __table_args__ = (
        UniqueConstraint("event_id", "kind", name="uq_email_outbox_event_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), index=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    recipient: Mapped[str] = mapped_column(String(320), default="")
    invitee_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    event_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    dead_letter: Mapped[bool] = mapped_column(Boolean, default=False)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def build_database(database_url: str):
    database_url = normalize_database_url(database_url)
    if database_url.startswith("sqlite:///./"):
        Path(database_url.removeprefix("sqlite:///./")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    )
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def check_database(engine) -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def event_exists(session_factory, event_id: str) -> bool:
    with session_factory() as session:
        return session.scalar(select(BookingEvent.id).where(BookingEvent.event_id == event_id)) is not None
