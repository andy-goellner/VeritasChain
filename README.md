# VeritasChain - PoCiv MVP

Proof of Civility (PoCiv) MVP - A reputation infrastructure that validates "civility" in online discourse using Discord bot, Temporal workflows, and Ethereum Attestation Service (EAS) on Optimism Sepolia.

## Architecture

- **Discord Bot**: Python `discord.py` bot with message context menu for rating civility
- **FastAPI Server**: REST API endpoint for receiving ratings and triggering workflows
- **Temporal Workflows**: Durable workflow orchestration for rating processing
- **Supabase/PostgreSQL**: Database for users, validations, and attestations
- **EAS Integration**: On-chain attestations on Optimism Sepolia testnet

## Prerequisites

- Python 3.10+
- UV package manager (recommended) or venv
- Supabase account and database
- Temporal server (local or cloud)
- Optimism Sepolia testnet access
- Discord bot token

## Setup

### 1. Install Dependencies

#### Option A: Using UV (Recommended)

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### 2. Database Setup

1. Create a Supabase project and database
2. Run the schema migration:

```bash
psql -h <your-supabase-host> -U <user> -d <database> -f schema.sql
```

Or use the Supabase SQL editor to execute `schema.sql`.

### 3. Environment Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Fill in all required values:

- `DISCORD_TOKEN`: Your Discord bot token
- `DATABASE_URL`: PostgreSQL connection string (Supabase)
- `PRIVATE_KEY`: Ethereum private key for signing transactions (0x prefix)
- `EAS_SCHEMA_UID`: Your EAS schema UID (64 hex characters)
- `TEMPORAL_HOST`: Temporal server address (default: localhost:7233)
- Other configuration as needed

### 4. EAS Schema Setup

Before running, you need to create an EAS schema on Optimism Sepolia with the following structure:

```
uint16 scaledScore, uint8[] metricRatings, string sourceRef, string communityContext
```

Register this schema on EAS and use the returned schema UID in your `.env` file.

## Running the Application

**Important**: If using venv, make sure it's activated before running these commands.

### Start Temporal Worker

In one terminal:

```bash
# With UV:
uv run python src/worker.py

# With venv (after activation):
python src/worker.py
```

### Start FastAPI Server

In another terminal:

```bash
# With UV:
uv run python src/api.py
```

Or using uvicorn directly:

```bash
# With UV:
uv run uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### Start Discord Bot

In a third terminal:

```bash
# With UV:
uv run python src/bot.py
```

## Usage

1. Invite the Discord bot to your server
2. Right-click on any message
3. Select "Apps" → "Rate Civility"
4. Fill in the 5 metrics (0-5 each):
   - Clarity
   - Respectfulness
   - Relevance
   - Evidence / Substance
   - Constructiveness
5. Submit the rating

The workflow will:

1. Calculate and store the score
2. Check eligibility (score >= 3.0 and wallet linked)
3. Mint an EAS attestation on Optimism Sepolia (if eligible)
4. Notify the user via Discord

## Scoring System

- **Bronze**: 3.0 - 3.9
- **Silver**: 4.0 - 4.5
- **Gold**: 4.6 - 5.0

Scores below 3.0 are recorded but do not trigger attestations.

## Testing

Run tests with pytest:

```bash
# With UV:
uv run pytest
```

Run with coverage:

```bash
# With UV:
uv run pytest --cov=src tests/
```

## Linting

Check code style with Ruff:

```bash
# With UV:
uv run ruff check src/
```

Auto-fix issues:

```bash
# With UV:
uv run ruff check --fix src/
```

## Project Structure

```
VeritasChain/
├── src/
│   ├── bot.py              # Discord bot
│   ├── api.py              # FastAPI server
│   ├── workflows.py        # Temporal workflows
│   ├── activities.py       # Temporal activities
│   ├── worker.py           # Temporal worker
│   ├── scoring.py          # Scoring logic
│   ├── config.py           # Configuration
│   ├── database/           # Database models and connection
│   └── eas/                # EAS client
├── tests/                  # Test files
├── schema.sql              # Database schema
├── pyproject.toml          # UV project configuration
└── ruff.toml               # Ruff linting configuration
```

## Development

This project follows TDD principles. When adding features:

1. Write tests first
2. Implement the feature
3. Iterate until tests pass
4. Ensure all code has type hints
5. Run linter before committing

**Tip**: Add `venv/` to your `.gitignore` to avoid committing the virtual environment.

## License

[Add your license here]

## Docker (Local dependencies)

This repository depends on Temporal and a Postgres database (used with Supabase in production). The included `docker-compose.yml` provides a minimal local setup:

- `temporal` - Temporal server (exposes 7233)
- `temporal-db` - Postgres for Temporal (internal 5432, mapped to host 5433)
- `supabase-db` - Postgres for app data (internal 5432, mapped to host 5434)

Start the stack:

```bash
# (from repo root)
docker compose up -d
```

Stop the stack:

```bash
docker compose down -v
```

Notes:

- The compose file uses simple defaults and example passwords. For local development this is convenient, but do not use these credentials in production.
- The Temporal image used is `temporalio/auto-setup:1.20.0` which will attempt to initialize its schema against the `temporal-db` Postgres service. If you use a different Temporal version or remote Temporal service, update the `docker-compose.yml` accordingly.
- The `supabase-db` service is a plain Postgres instance suitable for local development and running migrations from `schema.sql`. If you want the full Supabase ecosystem (auth, realtime, storage), consider using the official Supabase docker setup or the Supabase CLI.

Ports (host -> container):

- Temporal frontend: `localhost:7233` -> `7233`
- Temporal Postgres: `localhost:5433` -> `5432` (temporal-db)
- Supabase/Postgres: `localhost:5434` -> `5432` (supabase-db)

After starting the stack, update your `.env` or `DATABASE_URL` for local testing if needed, for example:

```
DATABASE_URL=postgresql://supabase_admin:supabase_password@localhost:5434/veritaschain
TEMPORAL_HOST=localhost:7233
```
