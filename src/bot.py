"""Discord bot for PoCiv MVP."""

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands
import httpx

from src.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


class RatingModal(discord.ui.Modal, title="Rate Civility"):
    """Modal for rating civility metrics."""

    clarity = discord.ui.TextInput(
        label="Clarity (0-5)",
        placeholder="Rate the clarity of the message",
        required=True,
        max_length=1,
    )

    respectfulness = discord.ui.TextInput(
        label="Respectfulness (0-5)",
        placeholder="Rate the respectfulness of the message",
        required=True,
        max_length=1,
    )

    relevance = discord.ui.TextInput(
        label="Relevance (0-5)",
        placeholder="Rate the relevance of the message",
        required=True,
        max_length=1,
    )

    evidence = discord.ui.TextInput(
        label="Evidence / Substance (0-5)",
        placeholder="Rate the evidence/substance of the message",
        required=True,
        max_length=1,
    )

    constructiveness = discord.ui.TextInput(
        label="Constructiveness (0-5)",
        placeholder="Rate the constructiveness of the message",
        required=True,
        max_length=1,
    )

    def __init__(self, target_message: discord.Message) -> None:
        """Initialize modal with target message."""
        super().__init__()
        self.target_message = target_message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission."""
        try:
            # Validate and parse inputs
            metrics = []
            metric_names = [
                "Clarity",
                "Respectfulness",
                "Relevance",
                "Evidence / Substance",
                "Constructiveness",
            ]

            for i, metric_input in enumerate(
                [
                    self.clarity,
                    self.respectfulness,
                    self.relevance,
                    self.evidence,
                    self.constructiveness,
                ]
            ):
                try:
                    value = int(metric_input.value.strip())
                    if value < 0 or value > 5:
                        await interaction.response.send_message(
                            f"❌ {metric_names[i]} must be between 0 and 5. You entered: {value}",
                            ephemeral=True,
                        )
                        return
                    metrics.append(value)
                except ValueError:
                    await interaction.response.send_message(
                        f"❌ {metric_names[i]} must be a number between 0 and 5. You entered: {metric_input.value}",
                        ephemeral=True,
                    )
                    return

            # Prepare payload
            payload = {
                "validator_id": interaction.user.id,
                "target_message_id": self.target_message.id,
                "target_user_id": self.target_message.author.id,
                "channel_id": self.target_message.channel.id,
                "metrics": metrics,
            }

            # Send to FastAPI
            api_url = f"http://{config.API_HOST}:{config.API_PORT}/submit-rating"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, json=payload)

            if response.status_code == 200:
                result = response.json()
                await interaction.response.send_message(
                    f"✅ Rating submitted successfully! Workflow ID: `{result['workflow_id']}`",
                    ephemeral=True,
                )
                logger.info(f"Rating submitted: {result['workflow_id']}")
            else:
                error_msg = response.text
                logger.error(f"API error: {error_msg}")
                await interaction.response.send_message(
                    f"❌ Failed to submit rating: {error_msg}",
                    ephemeral=True,
                )

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            await interaction.response.send_message(
                "❌ Failed to connect to API server. Please try again later.",
                ephemeral=True,
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await interaction.response.send_message(
                f"❌ An unexpected error occurred: {str(e)}",
                ephemeral=True,
            )


@bot.event
async def on_ready() -> None:
    """Called when the bot is ready."""
    logger.info(f"{bot.user} has connected to Discord!")
    logger.info(f"Bot is in {len(bot.guilds)} guild(s)")

    # Sync commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")


@bot.tree.context_menu(name="Rate Civility")
async def rate_civility(interaction: discord.Interaction, message: discord.Message) -> None:
    """Context menu command to rate a message's civility."""
    # Validate that the message is not from a bot
    if message.author.bot:
        await interaction.response.send_message(
            "❌ Cannot rate messages from bots.",
            ephemeral=True,
        )
        return

    # Validate that the user is not rating their own message
    if message.author.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Cannot rate your own message.",
            ephemeral=True,
        )
        return

    # Show modal
    modal = RatingModal(target_message=message)
    await interaction.response.send_modal(modal)


def run_bot() -> None:
    """Run the Discord bot."""
    if not config.DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is not set")

    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    run_bot()

