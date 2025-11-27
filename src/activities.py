"""Temporal activities for PoCiv workflow."""

import logging
import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio import activity

from src.database.connection import AsyncSessionLocal
from src.database.models import Attestation, AttestationStatus, User, Validation
from src.eas.client import EASClient
from src.scoring import calculate_score, get_emoji, get_tier

logger = logging.getLogger(__name__)


@activity.defn
async def calculate_and_store(
    validator_id: int,
    target_message_id: int,
    target_user_id: int,
    channel_id: int,
    metrics: list[int],
) -> dict[str, Any]:
    """
    Activity 1: Calculate score and store validation in database.

    Args:
        validator_id: Discord ID of the validator
        target_message_id: Discord message ID being rated
        target_user_id: Discord ID of the user whose message is being rated
        channel_id: Discord channel ID
        metrics: List of 5 integer scores (0-5)

    Returns:
        Dictionary with validation_id (UUID string) and score (float)
    """
    logger.info(f"Calculating and storing validation for message {target_message_id}")

    # Validate and calculate score
    score = calculate_score(metrics)

    # Store in database
    async with AsyncSessionLocal() as session:
        # Ensure users exist
        validator_user = await session.get(User, validator_id)
        if validator_user is None:
            validator_user = User(discord_id=validator_id, wallet_address=None)
            session.add(validator_user)
            await session.flush()

        target_user = await session.get(User, target_user_id)
        if target_user is None:
            target_user = User(discord_id=target_user_id, wallet_address=None)
            session.add(target_user)
            await session.flush()

        # Create validation record
        validation = Validation(
            validator_id=validator_id,
            target_message_id=target_message_id,
            target_user_id=target_user_id,
            channel_id=channel_id,
            metrics_json={"metrics": metrics},
            calculated_score=score,
        )
        session.add(validation)
        await session.commit()
        await session.refresh(validation)

        validation_id = str(validation.id)
        logger.info(f"Validation stored: {validation_id} with score {score}")

        return {"validation_id": validation_id, "score": score}


@activity.defn
async def check_eligibility(target_user_id: int, score: float) -> dict[str, Any]:
    """
    Activity 2: Check if user is eligible for attestation.

    Args:
        target_user_id: Discord ID of the target user
        score: Calculated score

    Returns:
        Dictionary with eligibility status and wallet_address if eligible
    """
    logger.info(f"Checking eligibility for user {target_user_id} with score {score}")

    if score < 3.0:
        logger.info(f"Score {score} is below threshold, not eligible")
        return {"eligible": False, "reason": "Not Eligible", "wallet_address": None}

    async with AsyncSessionLocal() as session:
        user = await session.get(User, target_user_id)
        if user is None:
            logger.warning(f"User {target_user_id} not found in database")
            return {"eligible": False, "reason": "No Wallet", "wallet_address": None}

        if not user.wallet_address:
            logger.info(f"User {target_user_id} has no wallet linked")
            return {"eligible": False, "reason": "No Wallet", "wallet_address": None}

        logger.info(f"User {target_user_id} is eligible with wallet {user.wallet_address}")
        return {"eligible": True, "reason": None, "wallet_address": user.wallet_address}


@activity.defn
async def mint_attestation(
    validation_id: str,
    recipient_wallet: str,
    score: float,
    metrics: list[int],
    channel_id: int,
    message_id: int,
) -> dict[str, Any]:
    """
    Activity 3: Mint EAS attestation on-chain with retry logic.

    Args:
        validation_id: UUID of the validation
        recipient_wallet: Wallet address of the recipient
        score: Calculated score
        metrics: List of 5 metric ratings
        channel_id: Discord channel ID
        message_id: Discord message ID

    Returns:
        Dictionary with uid and tx_hash
    """
    logger.info(f"Minting attestation for validation {validation_id}")

    # Prepare EAS data
    scaled_score = int(score * 100)
    source_ref = f"discord:{channel_id}:{message_id}"

    # Retry logic with exponential backoff
    max_attempts = 5
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            eas_client = EASClient()
            uid, tx_hash = eas_client.create_attestation(
                recipient=recipient_wallet,
                scaled_score=scaled_score,
                metric_ratings=metrics,
                source_ref=source_ref,
            )

            # Store attestation in database
            async with AsyncSessionLocal() as session:
                attestation = Attestation(
                    uid=uid,
                    validation_id=uuid.UUID(validation_id),
                    recipient_wallet=recipient_wallet,
                    tx_hash=tx_hash,
                    status=AttestationStatus.MINTED,
                )
                session.add(attestation)
                await session.commit()

            logger.info(f"Attestation minted successfully: {uid}")
            return {"uid": uid, "tx_hash": tx_hash}

        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e}")

            if attempt < max_attempts:
                # Exponential backoff: 2^attempt seconds
                import asyncio

                wait_time = 2**attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                # Store failed attestation
                async with AsyncSessionLocal() as session:
                    # Create a placeholder UID for failed attestations
                    failed_uid = f"failed_{validation_id}"
                    attestation = Attestation(
                        uid=failed_uid,
                        validation_id=uuid.UUID(validation_id),
                        recipient_wallet=recipient_wallet,
                        tx_hash="",
                        status=AttestationStatus.FAILED,
                    )
                    session.add(attestation)
                    await session.commit()

                logger.error(f"Failed to mint attestation after {max_attempts} attempts: {last_error}")
                raise Exception(f"Failed to mint attestation: {last_error}") from last_error

    raise Exception("Unexpected error in mint_attestation")


@activity.defn
async def notify_discord(
    channel_id: int,
    message_id: int,
    target_user_id: int,
    tier: str,
    eas_uid: str | None,
    api_base_url: str,
) -> dict[str, Any]:
    """
    Activity 4: Notify Discord user and react to message.

    Args:
        channel_id: Discord channel ID
        message_id: Discord message ID
        target_user_id: Discord ID of the target user
        tier: Tier name ("Bronze", "Silver", "Gold")
        eas_uid: EAS attestation UID (optional)
        api_base_url: Base URL for the API (to construct Discord webhook or bot endpoint)

    Returns:
        Dictionary with success status
    """
    logger.info(f"Notifying Discord for user {target_user_id}, tier {tier}")

    # This activity will be called by the workflow, but actual Discord operations
    # should be done via the bot or a Discord webhook
    # For now, we'll return the notification data
    # In a full implementation, this would make HTTP calls to Discord API or use bot client

    emoji = get_emoji(tier)

    # Construct EAS explorer link
    eas_link = f"https://optimism-sepolia.easscan.org/attestation/view/{eas_uid}" if eas_uid else "N/A"

    notification_data = {
        "channel_id": channel_id,
        "message_id": message_id,
        "target_user_id": target_user_id,
        "emoji": emoji,
        "tier": tier,
        "eas_link": eas_link,
        "message": f"You earned a {tier} Civility Stamp! View on EAS: {eas_link}",
    }

    logger.info(f"Discord notification prepared: {notification_data}")

    # Note: Actual Discord API calls would be made here
    # For MVP, the workflow will handle this via the bot client

    return {"success": True, "notification_data": notification_data}

