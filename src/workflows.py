"""Temporal workflows for PoCiv MVP."""

import logging
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from .activities import (
        calculate_and_store,
        check_eligibility,
        mint_attestation,
        notify_discord,
    )
    from .config import config
    from .data_models import (
        AttestationData,
        EligibilityCheckData,
        NotificationData,
        RatingData,
        WorkflowResult,
    )
    from .scoring import get_tier

logger = logging.getLogger(__name__)


@workflow.defn
class CivilityRatingWorkflow:
    """Workflow for processing civility ratings and minting attestations."""

    @workflow.run
    async def run(self, rating_data: RatingData) -> WorkflowResult:
        """
        Main workflow execution.

        Args:
            rating_data: RatingData object containing:
                - validator_id: int
                - target_message_id: int
                - target_user_id: int
                - channel_id: int
                - metrics: list[int] (5 metrics)

        Returns:
            WorkflowResult with workflow execution details
        """
        workflow.logger.info("Starting CivilityRatingWorkflow")
        workflow.logger.info(f"Rating data: {rating_data}")

        try:
            # Activity 1: Calculate and store
            calculation_result = await workflow.execute_activity(
                calculate_and_store,
                rating_data,
                start_to_close_timeout=timedelta(seconds=30),
            )

            workflow.logger.info(
                f"Calculation result: {calculation_result}, Type: {type(calculation_result)}"
            )
            validation_id = calculation_result.validation_id
            score = calculation_result.score
            metrics = rating_data.metrics

            workflow.logger.info(f"Validation stored: {validation_id}, score: {score}")

            # Activity 2: Check eligibility
            eligibility_data = EligibilityCheckData(
                target_user_id=rating_data.target_user_id,
                score=score,
            )
            eligibility_result = await workflow.execute_activity(
                check_eligibility,
                eligibility_data,
                start_to_close_timeout=timedelta(seconds=30),
            )

            if not eligibility_result.eligible:
                reason = eligibility_result.reason
                workflow.logger.info(f"Not eligible for attestation: {reason}")

                # If no wallet, we could trigger a DM here, but for MVP we'll just return
                return WorkflowResult(
                    success=False,
                    validation_id=validation_id,
                    score=score,
                    reason=reason,
                    attestation_uid=None,
                )

            recipient_wallet = eligibility_result.wallet_address
            tier = get_tier(score)

            if tier is None:
                workflow.logger.warning(f"Score {score} resulted in None tier")
                return WorkflowResult(
                    success=False,
                    validation_id=validation_id,
                    score=score,
                    reason="Score below threshold",
                    attestation_uid=None,
                )

            # Activity 3: Mint attestation (with retry policy)
            try:
                attestation_data = AttestationData(
                    validation_id=validation_id,
                    recipient_wallet=recipient_wallet,
                    score=score,
                    metrics=metrics,
                    channel_id=rating_data.channel_id,
                    message_id=rating_data.target_message_id,
                )
                attestation_result = await workflow.execute_activity(
                    mint_attestation,
                    attestation_data,
                    start_to_close_timeout=timedelta(
                        seconds=300
                    ),  # 5 minutes for blockchain operations
                    retry_policy=workflow.RetryPolicy(
                        initial_interval=timedelta(seconds=2),
                        backoff_coefficient=2.0,
                        maximum_attempts=5,
                    ),
                )

                eas_uid = attestation_result.uid
                tx_hash = attestation_result.tx_hash

                workflow.logger.info(f"Attestation minted: {eas_uid}")

            except Exception as e:
                workflow.logger.error(f"Failed to mint attestation: {e}")
                # Graceful degradation: continue to notification even if minting failed
                eas_uid = None
                tx_hash = None

            # Activity 4: Notify Discord
            api_base_url = f"http://{config.API_HOST}:{config.API_PORT}"
            try:
                notification_data = NotificationData(
                    channel_id=rating_data.channel_id,
                    message_id=rating_data.target_message_id,
                    target_user_id=rating_data.target_user_id,
                    tier=tier,
                    eas_uid=eas_uid,
                    api_base_url=api_base_url,
                )
                await workflow.execute_activity(
                    notify_discord,
                    notification_data,
                    start_to_close_timeout=timedelta(seconds=30),
                )
            except Exception as e:
                workflow.logger.error(f"Failed to notify Discord: {e}")
                # Don't fail the workflow if notification fails

            workflow.logger.info("CivilityRatingWorkflow completed successfully")

            return WorkflowResult(
                success=True,
                validation_id=validation_id,
                score=score,
                tier=tier,
                attestation_uid=eas_uid,
                tx_hash=tx_hash,
            )

        except Exception as e:
            workflow.logger.error(f"Workflow failed: {e}")
            return WorkflowResult(
                success=False,
                error=str(e),
            )
