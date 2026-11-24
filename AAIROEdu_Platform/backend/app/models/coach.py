import enum
import uuid
from typing import Optional
from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class MessageSender(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class CoachConversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "coach_conversations"

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="Career Strategy Session", nullable=False)

    # Relationships
    candidate_profile = relationship("CandidateProfile", back_populates="coach_conversations")
    messages = relationship("CoachMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="CoachMessage.created_at")


class CoachMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "coach_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coach_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sender: Mapped[MessageSender] = mapped_column(
        Enum(MessageSender, name="message_sender_enum", values_callable=lambda x: [e.value for e in x]),
        default=MessageSender.USER,
        nullable=False
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    conversation = relationship("CoachConversation", back_populates="messages")
