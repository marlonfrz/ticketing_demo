import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    promoter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    platform_fee_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    platform_fee_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    promoter = relationship("User")
    ticket_types = relationship("TicketType", back_populates="event", cascade="all, delete-orphan")
    sessions = relationship("EventSession", back_populates="event", cascade="all, delete-orphan")
    public_relations = relationship("PublicRelations", back_populates="event", cascade="all, delete-orphan")

    @property
    def _first_session(self):
        return min(self.sessions, key=lambda session: session.starts_at) if self.sessions else None

    @property
    def location_name(self) -> str:
        session = self._first_session
        return session.location_name if session else ""

    @property
    def location_address(self) -> str | None:
        session = self._first_session
        return session.location_address if session else None

    @property
    def starts_at(self) -> datetime | None:
        session = self._first_session
        return session.starts_at if session else None

    @property
    def ends_at(self) -> datetime | None:
        values = [session.ends_at for session in self.sessions if session.ends_at]
        return max(values) if values else None

    @property
    def capacity(self) -> int:
        return sum(session.capacity or 0 for session in self.sessions)

    @property
    def tickets_publish_at(self) -> datetime | None:
        values = [session.tickets_publish_at for session in self.sessions if session.tickets_publish_at]
        return min(values) if values else None

    @property
    def tickets_activated_at(self) -> datetime | None:
        values = [session.tickets_activated_at for session in self.sessions if session.tickets_activated_at]
        return min(values) if values else None
