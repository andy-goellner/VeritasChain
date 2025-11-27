"""Temporal worker for PoCiv MVP."""

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from src.activities import (
    calculate_and_store,
    check_eligibility,
    mint_attestation,
    notify_discord,
)
from src.config import config
from src.workflows import CivilityRatingWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the Temporal worker."""
    logger.info("Starting Temporal worker...")

    # Connect to Temporal
    client = await Client.connect(
        target_host=config.TEMPORAL_HOST,
        namespace=config.TEMPORAL_NAMESPACE,
    )

    logger.info(f"Connected to Temporal at {config.TEMPORAL_HOST}")

    # Create worker
    worker = Worker(
        client,
        task_queue="civility-rating-queue",
        workflows=[CivilityRatingWorkflow],
        activities=[
            calculate_and_store,
            check_eligibility,
            mint_attestation,
            notify_discord,
        ],
    )

    logger.info("Worker created. Starting...")

    # Run worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

