"""FastAPI server for PoCiv MVP."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from temporalio.client import Client

from src.config import config
from src.workflows import CivilityRatingWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PoCiv MVP API", version="0.1.0")


class RatingRequest(BaseModel):
    """Request model for submitting a rating."""

    validator_id: int = Field(..., description="Discord ID of the validator")
    target_message_id: int = Field(..., description="Discord message ID being rated")
    target_user_id: int = Field(..., description="Discord ID of the user whose message is being rated")
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


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize Temporal client on startup."""
    logger.info("Starting PoCiv MVP API server")
    # Temporal client will be created per-request or stored in app state
    # For MVP, we'll create it per request


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/submit-rating", response_model=RatingResponse)
async def submit_rating(rating: RatingRequest) -> RatingResponse:
    """
    Submit a civility rating and trigger the workflow.

    Args:
        rating: Rating request with validator, target, and metrics

    Returns:
        Response with workflow ID
    """
    logger.info(f"Received rating submission: {rating}")

    try:
        # Connect to Temporal
        temporal_client = await Client.connect(
            target_host=config.TEMPORAL_HOST,
            namespace=config.TEMPORAL_NAMESPACE,
        )

        # Start workflow
        workflow_handle = await temporal_client.start_workflow(
            CivilityRatingWorkflow.run,
            rating.model_dump(),
            id=f"civility-rating-{rating.target_message_id}",
            task_queue="civility-rating-queue",
        )

        logger.info(f"Workflow started: {workflow_handle.id}")

        return RatingResponse(
            workflow_id=workflow_handle.id,
            message="Rating submitted successfully. Workflow started.",
        )

    except Exception as e:
        logger.error(f"Error submitting rating: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit rating: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)

