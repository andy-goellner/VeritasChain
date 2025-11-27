"""SQLAlchemy models for PoCiv MVP."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Float, ForeignKey, JSON, String, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class AttestationStatus(str, enum.Enum):
    """Attestation status enum."""

    PENDING = "PENDING"
    MINTED = "MINTED"
    FAILED = "FAILED"


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class User(Base):
    """User model representing Discord users."""

    __tablename__ = "users"

    discord_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    wallet_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    validations_as_validator: Mapped[list["Validation"]] = relationship(
        "Validation",
        foreign_keys="[Validation.validator_id]",
        back_populates="validator",
    )
    validations_as_target: Mapped[list["Validation"]] = relationship(
        "Validation",
        foreign_keys="[Validation.target_user_id]",
        back_populates="target_user",
    )


class Validation(Base):
    """Validation model representing civility ratings."""

    __tablename__ = "validations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), nullable=False)
    target_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.discord_id"), nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    calculated_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    validator: Mapped["User"] = relationship("User", foreign_keys=[validator_id], back_populates="validations_as_validator")
    target_user: Mapped["User"] = relationship("User", foreign_keys=[target_user_id], back_populates="validations_as_target")
    attestations: Mapped[list["Attestation"]] = relationship("Attestation", back_populates="validation")


class Attestation(Base):
    """Attestation model representing on-chain EAS attestations."""

    __tablename__ = "attestations"

    uid: Mapped[str] = mapped_column(String(66), primary_key=True)
    validation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("validations.id"), nullable=False
    )
    recipient_wallet: Mapped[str] = mapped_column(String(42), nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    status: Mapped[AttestationStatus] = mapped_column(
        SQLEnum(AttestationStatus), nullable=False, default=AttestationStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    validation: Mapped["Validation"] = relationship("Validation", back_populates="attestations")

