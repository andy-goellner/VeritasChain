"""Temporal activities for PoCiv workflow."""

import asyncio
import logging
import uuid

from temporalio import activity

from .data_models import (
    AttestationData,
    AttestationResult,
    CalculationResult,
    EligibilityCheckData,
    EligibilityResult,
    NotificationData,
    NotificationResult,
    RatingData,
)
from .database.connection import AsyncSessionLocal
from .database.models import Attestation, AttestationStatus, User, Validation
from .eas.client import EASClient
from .scoring import calculate_score, get_emoji, get_tier

logger = logging.getLogger(__name__)


@activity.defn
async def calculate_and_store(rating_data: RatingData) -> CalculationResult:
    """
    Activity 1: Calculate score and store validation in database.

    Args:
        rating_data: RatingData containing validator, target, and metrics information

    Returns:
        CalculationResult with validation_id (UUID string) and score (float)
    """
    logger.info(
        f"Calculating and storing validation for message {rating_data.target_message_id}"
    )

    # Validate and calculate score
    score = calculate_score(rating_data.metrics)

    # Store in database
    async with AsyncSessionLocal() as session:
        # Ensure users exist
        validator_user = await session.get(User, rating_data.validator_id)
        if validator_user is None:
            validator_user = User(
                discord_id=rating_data.validator_id, wallet_address=None
            )
            session.add(validator_user)
            await session.flush()

        target_user = await session.get(User, rating_data.target_user_id)
        if target_user is None:
            target_user = User(
                discord_id=rating_data.target_user_id, wallet_address=None
            )
            session.add(target_user)
            await session.flush()

        # Create validation record
        validation = Validation(
            validator_id=rating_data.validator_id,
            target_message_id=rating_data.target_message_id,
            target_user_id=rating_data.target_user_id,
            channel_id=rating_data.channel_id,
            metrics_json={"metrics": rating_data.metrics},
            calculated_score=score,
        )
        session.add(validation)
        await session.commit()
        await session.refresh(validation)

        validation_id = str(validation.id)
        logger.info(f"Validation stored: {validation_id} with score {score}")

        return CalculationResult(validation_id=validation_id, score=score)


@activity.defn
async def check_eligibility(
    eligibility_data: EligibilityCheckData,
) -> EligibilityResult:
    """
    Activity 2: Check if user is eligible for attestation.

    Args:
        eligibility_data: EligibilityCheckData containing target_user_id and score

    Returns:
        EligibilityResult with eligibility status and wallet_address if eligible
    """
    logger.info(
        f"Checking eligibility for user {eligibility_data.target_user_id} with score {eligibility_data.score}"
    )

    if eligibility_data.score < 3.0:
        logger.info(f"Score {eligibility_data.score} is below threshold, not eligible")
        return EligibilityResult(
            eligible=False, reason="Not Eligible", wallet_address=None
        )

    async with AsyncSessionLocal() as session:
        user = await session.get(User, eligibility_data.target_user_id)
        if user is None:
            logger.warning(
                f"User {eligibility_data.target_user_id} not found in database"
            )
            return EligibilityResult(
                eligible=False, reason="No Wallet", wallet_address=None
            )

        if not user.wallet_address:
            logger.info(f"User {eligibility_data.target_user_id} has no wallet linked")
            return EligibilityResult(
                eligible=False, reason="No Wallet", wallet_address=None
            )

        logger.info(
            f"User {eligibility_data.target_user_id} is eligible with wallet {user.wallet_address}"
        )
        return EligibilityResult(
            eligible=True, reason=None, wallet_address=user.wallet_address
        )


@activity.defn
async def mint_attestation(attestation_data: AttestationData) -> AttestationResult:
    """
    Activity 3: Mint EAS attestation on-chain with retry logic.

    Args:
        attestation_data: AttestationData containing validation, wallet, score, and metrics

    Returns:
        AttestationResult with uid and tx_hash
    """
    logger.info(f"Minting attestation for validation {attestation_data.validation_id}")

    # Prepare EAS data
    scaled_score = int(attestation_data.score * 100)
    source_ref = f"discord:{attestation_data.channel_id}:{attestation_data.message_id}"

    # Retry logic with exponential backoff
    max_attempts = 5
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            eas_client = EASClient()
            uid, tx_hash = eas_client.create_attestation(
                recipient=attestation_data.recipient_wallet,
                scaled_score=scaled_score,
                metric_ratings=attestation_data.metrics,
                source_ref=source_ref,
            )

            # Store attestation in database
            async with AsyncSessionLocal() as session:
                # Accept both UUID and string for validation_id (for tests)
                try:
                    val_id = uuid.UUID(attestation_data.validation_id)
                except (ValueError, AttributeError, TypeError):
                    val_id = attestation_data.validation_id
                attestation = Attestation(
                    uid=uid,
                    validation_id=val_id,
                    recipient_wallet=attestation_data.recipient_wallet,
                    tx_hash=tx_hash,
                    status=AttestationStatus.MINTED,
                )
                session.add(attestation)
                await session.commit()

            logger.info(f"Attestation minted successfully: {uid}")
            return AttestationResult(uid=uid, tx_hash=tx_hash)

        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e}")

            if attempt < max_attempts:
                # Exponential backoff: 2^attempt seconds
                wait_time = 2**attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                # Store failed attestation
                async with AsyncSessionLocal() as session:
                    # Accept both UUID and string for validation_id (for tests)
                    try:
                        val_id = uuid.UUID(attestation_data.validation_id)
                    except (ValueError, AttributeError, TypeError):
                        val_id = attestation_data.validation_id
                    # Create a placeholder UID for failed attestations
                    failed_uid = f"failed_{attestation_data.validation_id}"
                    attestation = Attestation(
                        uid=failed_uid,
                        validation_id=val_id,
                        recipient_wallet=attestation_data.recipient_wallet,
                        tx_hash="",
                        status=AttestationStatus.FAILED,
                    )
                    session.add(attestation)
                    await session.commit()

                logger.error(
                    f"Failed to mint attestation after {max_attempts} attempts: {last_error}"
                )
                raise Exception(
                    f"Failed to mint attestation: {last_error}"
                ) from last_error

    raise Exception("Unexpected error in mint_attestation")


@activity.defn
async def notify_discord(notification_data: NotificationData) -> NotificationResult:
    """
    Activity 4: Notify Discord user and react to message.

    Args:
        notification_data: NotificationData containing channel, message, user, tier, and EAS info

    Returns:
        NotificationResult with success status and notification data
    """
    logger.info(
        f"Notifying Discord for user {notification_data.target_user_id}, tier {notification_data.tier}"
    )

    # This activity will be called by the workflow, but actual Discord operations
    # should be done via the bot or a Discord webhook
    # For now, we'll return the notification data
    # In a full implementation, this would make HTTP calls to Discord API or use bot client

    emoji = get_emoji(notification_data.tier)

    # Construct EAS explorer link
    eas_link = (
        f"https://optimism-sepolia.easscan.org/attestation/view/{notification_data.eas_uid}"
        if notification_data.eas_uid
        else "N/A"
    )

    notification_result_data = {
        "channel_id": notification_data.channel_id,
        "message_id": notification_data.message_id,
        "target_user_id": notification_data.target_user_id,
        "emoji": emoji,
        "tier": notification_data.tier,
        "eas_link": eas_link,
        "message": f"You earned a {notification_data.tier} Civility Stamp! View on EAS: {eas_link}",
    }

    logger.info(f"Discord notification prepared: {notification_result_data}")

    # Note: Actual Discord API calls would be made here
    # For MVP, the workflow will handle this via the bot client

    return NotificationResult(success=True, notification_data=notification_result_data)
