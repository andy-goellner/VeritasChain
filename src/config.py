"""Configuration management using environment variables.

This module provides sane defaults for local development (see `.env.example`
and `docker-compose.yml`). It uses python-dotenv to load a local `.env` file
if present.
"""

import os
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root if present
load_dotenv()


class Config:
    """Application configuration loaded from environment variables.

    Defaults are chosen to match the project's `docker-compose.yml` and
    `.env.example` for local development.
    """

    # Discord Configuration
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    DISCORD_GUILD_ID: Optional[str] = os.getenv("DISCORD_GUILD_ID")

    # Supabase / App Postgres Configuration
    # Default matches docker-compose: supabase-db mapped to localhost:5434
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "http://localhost:54321")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    # Backwards-compatible single key
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", SUPABASE_SERVICE_ROLE_KEY or "")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg:://supabase_admin:supabase_password@localhost:5434/veritaschain",
    )

    # Temporal Configuration
    # The compose file exposes the Temporal frontend on localhost:7233
    TEMPORAL_HOST: str = os.getenv("TEMPORAL_HOST", "localhost")
    TEMPORAL_PORT: int = int(os.getenv("TEMPORAL_PORT", "7233"))
    TEMPORAL_NAMESPACE: str = os.getenv("TEMPORAL_NAMESPACE", "default")
    # Computed endpoint used by clients expecting host:port
    TEMPORAL_ENDPOINT: str = os.getenv(
        "TEMPORAL_ENDPOINT", f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"
    )
    # DB URL for the Temporal DB (if you want to inspect or initialize it)
    TEMPORAL_DB_URL: str = os.getenv(
        "TEMPORAL_DB_URL",
        "postgresql+psycopg:://temporal:temporal@localhost:5433/temporal",
    )

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
        """Validate that required configuration variables are set.

        For local development we only require a `DATABASE_URL`. Other keys
        (Discord token, blockchain keys) are optional for development runs and
        tests; raise only if DATABASE_URL is missing to avoid blocking local
        testing.
        """
        required_vars = ["DATABASE_URL"]
        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


config = Config()
