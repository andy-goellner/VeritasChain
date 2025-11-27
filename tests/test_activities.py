"""Tests for Temporal activities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.activities import (
    calculate_and_store,
    check_eligibility,
    mint_attestation,
    notify_discord,
)
from src.data_models import AttestationData, EligibilityCheckData, NotificationData, RatingData


@pytest.mark.asyncio
async def test_calculate_and_store() -> None:
    """Test calculate_and_store activity."""
    with patch("src.activities.AsyncSessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        # Mock user lookups
        mock_session.get.side_effect = [None, None]  # Both users don't exist
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        rating_data = RatingData(
            validator_id=123,
            target_message_id=456,
            target_user_id=789,
            channel_id=100,
            metrics=[5, 4, 3, 2, 1],
        )

        result = await calculate_and_store(rating_data)

        assert result.validation_id
        assert result.score == 3.0
        assert mock_session.add.call_count == 3  # 2 users + 1 validation


@pytest.mark.asyncio
async def test_check_eligibility_not_eligible_low_score() -> None:
    """Test check_eligibility with score below threshold."""
    with patch("src.activities.AsyncSessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        eligibility_data = EligibilityCheckData(target_user_id=789, score=2.5)
        result = await check_eligibility(eligibility_data)

        assert result.eligible is False
        assert result.reason == "Not Eligible"


@pytest.mark.asyncio
async def test_check_eligibility_no_wallet() -> None:
    """Test check_eligibility when user has no wallet."""
    with patch("src.activities.AsyncSessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        mock_user = MagicMock()
        mock_user.wallet_address = None
        mock_session.get.return_value = mock_user

        eligibility_data = EligibilityCheckData(target_user_id=789, score=4.0)
        result = await check_eligibility(eligibility_data)

        assert result.eligible is False
        assert result.reason == "No Wallet"


@pytest.mark.asyncio
async def test_check_eligibility_eligible() -> None:
    """Test check_eligibility when user is eligible."""
    with patch("src.activities.AsyncSessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        mock_user = MagicMock()
        mock_user.wallet_address = "0x1234567890123456789012345678901234567890"
        mock_session.get.return_value = mock_user

        eligibility_data = EligibilityCheckData(target_user_id=789, score=4.0)
        result = await check_eligibility(eligibility_data)

        assert result.eligible is True
        assert result.wallet_address == "0x1234567890123456789012345678901234567890"


@pytest.mark.asyncio
async def test_mint_attestation_success() -> None:
    """Test mint_attestation activity with successful minting."""
    with (
        patch("src.activities.EASClient") as mock_eas_client_class,
        patch("src.activities.AsyncSessionLocal") as mock_session_local,
    ):
        mock_eas_client = MagicMock()
        mock_eas_client.create_attestation.return_value = ("test_uid", "test_tx_hash")
        mock_eas_client_class.return_value = mock_eas_client

        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session
        mock_session.commit = AsyncMock()

        attestation_data = AttestationData(
            validation_id="test-validation-id",
            recipient_wallet="0x1234567890123456789012345678901234567890",
            score=4.0,
            metrics=[5, 4, 3, 4, 4],
            channel_id=100,
            message_id=456,
        )

        result = await mint_attestation(attestation_data)

        assert result.uid == "test_uid"
        assert result.tx_hash == "test_tx_hash"


@pytest.mark.asyncio
async def test_notify_discord() -> None:
    """Test notify_discord activity."""
    notification_data = NotificationData(
        channel_id=100,
        message_id=456,
        target_user_id=789,
        tier="Gold",
        eas_uid="test_uid",
        api_base_url="http://localhost:8000",
    )

    result = await notify_discord(notification_data)

    assert result.success is True
    assert result.notification_data is not None
    assert result.notification_data["tier"] == "Gold"
    assert result.notification_data["emoji"] == "🥇"
