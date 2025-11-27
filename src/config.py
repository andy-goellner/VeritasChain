"""Configuration management using environment variables."""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Discord Configuration
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    DISCORD_GUILD_ID: Optional[str] = os.getenv("DISCORD_GUILD_ID")

    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Temporal Configuration
    TEMPORAL_HOST: str = os.getenv("TEMPORAL_HOST", "localhost:7233")
    TEMPORAL_NAMESPACE: str = os.getenv("TEMPORAL_NAMESPACE", "default")

    # Blockchain Configuration (Optimism Sepolia)
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    EAS_SCHEMA_UID: str = os.getenv("EAS_SCHEMA_UID", "")
    EAS_CONTRACT_ADDRESS: str = os.getenv(
        "EAS_CONTRACT_ADDRESS", "0x4200000000000000000000000000000000000021"
    )
    OPTIMISM_SEPOLIA_RPC_URL: str = os.getenv(
        "OPTIMISM_SEPOLIA_RPC_URL", "https://sepolia.optimism.io"
    )

    # FastAPI Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    @classmethod
    def validate(cls) -> None:
        """Validate that all required configuration variables are set."""
        required_vars = [
            "DISCORD_TOKEN",
            "DATABASE_URL",
            "PRIVATE_KEY",
            "EAS_SCHEMA_UID",
        ]
        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


config = Config()

