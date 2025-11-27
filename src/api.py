"""FastAPI server for PoCiv MVP."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from .config import config
from .data_models import RatingData, RatingRequest, RatingResponse
from .workflows import CivilityRatingWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context for FastAPI app startup/shutdown."""
    logger.info("Starting PoCiv MVP API server")
    # Temporal client will be created per-request or stored in app state
    # For MVP, we'll create it per request
    yield


app = FastAPI(title="PoCiv MVP API", version="0.1.0", lifespan=lifespan)


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
        # Convert RatingRequest to RatingData for workflow
        rating_data = RatingData(**rating.model_dump())

        # Connect to Temporal
        temporal_client = await Client.connect(
            target_host=f"{config.TEMPORAL_HOST}:{config.TEMPORAL_PORT}",
            namespace=config.TEMPORAL_NAMESPACE,
            data_converter=pydantic_data_converter,
        )

        # Start workflow
        workflow_handle = await temporal_client.start_workflow(
            CivilityRatingWorkflow.run,
            rating_data,
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
        raise HTTPException(
            status_code=500, detail=f"Failed to submit rating: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
