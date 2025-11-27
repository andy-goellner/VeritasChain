"""Tests for Discord bot."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

from src.bot import RatingModal, bot


@pytest.mark.asyncio
async def test_rating_modal_validation() -> None:
    """Test RatingModal input validation."""
    mock_message = MagicMock()
    mock_message.id = 456
    mock_message.author.id = 789
    mock_message.channel.id = 100

    modal = RatingModal(target_message=mock_message)

    # Set invalid values
    modal.clarity.value = "6"  # Out of range
    modal.respectfulness.value = "4"
    modal.relevance.value = "3"
    modal.evidence.value = "4"
    modal.constructiveness.value = "5"

    mock_interaction = AsyncMock()
    mock_interaction.user.id = 123
    mock_interaction.response.send_message = AsyncMock()

    with patch("src.bot.httpx.AsyncClient") as mock_client_class:
        await modal.on_submit(mock_interaction)

        # Should send error message
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert "must be between 0 and 5" in call_args


@pytest.mark.asyncio
async def test_rating_modal_success() -> None:
    """Test RatingModal successful submission."""
    mock_message = MagicMock()
    mock_message.id = 456
    mock_message.author.id = 789
    mock_message.channel.id = 100

    modal = RatingModal(target_message=mock_message)

    # Set valid values
    modal.clarity.value = "5"
    modal.respectfulness.value = "4"
    modal.relevance.value = "3"
    modal.evidence.value = "4"
    modal.constructiveness.value = "5"

    mock_interaction = AsyncMock()
    mock_interaction.user.id = 123
    mock_interaction.response.send_message = AsyncMock()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"workflow_id": "test-workflow-id"}

    with patch("src.bot.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response

        await modal.on_submit(mock_interaction)

        # Should send success message
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args[0][0]
        assert "submitted successfully" in call_args

