"""Pydantic data models for Temporal workflows and activities."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RatingRequest(BaseModel):
    """Request model for submitting a rating."""

    validator_id: int = Field(..., description="Discord ID of the validator")
    target_message_id: int = Field(..., description="Discord message ID being rated")
    target_user_id: int = Field(
        ..., description="Discord ID of the user whose message is being rated"
    )
    channel_id: int = Field(..., description="Discord channel ID")
    metrics: list[int] = Field(..., description="List of 5 integer scores (0-5)")

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, v: list[int]) -> list[int]:
        """Validate that metrics list has exactly 5 elements, each 0-5."""
        if len(v) != 5:
            raise ValueError("Metrics must contain exactly 5 values")
        for i, metric in enumerate(v):
            if not isinstance(metric, int) or metric < 0 or metric > 5:
                raise ValueError(f"Metric {i} must be an integer between 0 and 5")
        return v


class RatingResponse(BaseModel):
    """Response model for rating submission."""

    workflow_id: str
    message: str


class RatingData(BaseModel):
    """Input data for civility rating workflow."""

    validator_id: int = Field(..., description="Discord ID of the validator")
    target_message_id: int = Field(..., description="Discord message ID being rated")
    target_user_id: int = Field(
        ..., description="Discord ID of the user whose message is being rated"
    )
    channel_id: int = Field(..., description="Discord channel ID")
    metrics: list[int] = Field(..., description="List of 5 integer scores (0-5)")


class CalculationResult(BaseModel):
    """Output from calculate_and_store activity."""

    validation_id: str = Field(..., description="UUID of the validation")
    score: float = Field(..., description="Calculated civility score")


class EligibilityCheckData(BaseModel):
    """Input data for check_eligibility activity."""

    target_user_id: int = Field(..., description="Discord ID of the target user")
    score: float = Field(..., description="Calculated civility score")


class EligibilityResult(BaseModel):
    """Output from check_eligibility activity."""

    eligible: bool = Field(..., description="Whether user is eligible for attestation")
    reason: Optional[str] = Field(None, description="Reason if not eligible")
    wallet_address: Optional[str] = Field(
        None, description="User's wallet address if eligible"
    )


class AttestationData(BaseModel):
    """Input data for mint_attestation activity."""

    validation_id: str = Field(..., description="UUID of the validation")
    recipient_wallet: str = Field(..., description="Wallet address of the recipient")
    score: float = Field(..., description="Calculated score")
    metrics: list[int] = Field(..., description="List of 5 metric ratings")
    channel_id: int = Field(..., description="Discord channel ID")
    message_id: int = Field(..., description="Discord message ID")


class AttestationResult(BaseModel):
    """Output from mint_attestation activity."""

    uid: str = Field(..., description="EAS attestation UID")
    tx_hash: str = Field(..., description="Transaction hash")


class NotificationData(BaseModel):
    """Input data for notify_discord activity."""

    channel_id: int = Field(..., description="Discord channel ID")
    message_id: int = Field(..., description="Discord message ID")
    target_user_id: int = Field(..., description="Discord ID of the target user")
    tier: str = Field(..., description="Tier name (Bronze, Silver, Gold)")
    eas_uid: Optional[str] = Field(None, description="EAS attestation UID")
    api_base_url: str = Field(..., description="Base URL for the API")


class NotificationResult(BaseModel):
    """Output from notify_discord activity."""

    success: bool = Field(..., description="Whether notification was successful")
    notification_data: Optional[dict] = Field(None, description="Notification data")


class WorkflowResult(BaseModel):
    """Final result of CivilityRatingWorkflow."""

    success: bool = Field(..., description="Whether workflow completed successfully")
    validation_id: Optional[str] = Field(None, description="UUID of the validation")
    score: Optional[float] = Field(None, description="Calculated score")
    tier: Optional[str] = Field(None, description="Awarded tier")
    attestation_uid: Optional[str] = Field(None, description="EAS attestation UID")
    tx_hash: Optional[str] = Field(None, description="Transaction hash")
    reason: Optional[str] = Field(None, description="Reason for failure")
    error: Optional[str] = Field(None, description="Error message if workflow failed")
