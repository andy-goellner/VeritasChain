# PROMPT.md - PoCiv MVP Construction

## Role & Objective
You are a Senior Full-Stack Web3 Engineer. Your objective is to build the Phase 2 Technical MVP for **PoCiv (Proof of Civility)**.

[cite_start]**Context:** PoCiv is a reputation infrastructure that validates "civility" in online discourse[cite: 35]. [cite_start]This MVP uses a "Human-in-the-Loop" architecture where trusted validators manually score Discord messages, triggering an automated on-chain attestation via the Ethereum Attestation Service (EAS)[cite: 124, 181].

---

## 1. Technical Stack Constraints
You must strictly adhere to this stack:
* **Interface:** Discord Bot (Python `discord.py` or `pycord`).
* **Backend API:** Python FastAPI.
* **Orchestration:** Temporal.io (Python SDK) for durable workflow execution.
* **Database:** Supabase (PostgreSQL) interacting via `sqlalchemy` or `prisma-client-python`.
* **Blockchain:** EAS SDK / `web3.py` (Target Network: Optimism Sepolia or Base Sepolia).
* **Environment:** Python 3.10+. Use the latest stable that supports our dependencies.
* **Testing:** Use pytest

---

## 2. Rules & Behavioral Guidelines for the Agent
**Code Quality:**
1.  **Async First:** Discord and FastAPI are async. Ensure database calls and blocking I/O (like blockchain transactions) are handled correctly (e.g., run synchronous web3 calls in executors or Temporal activities).
2.  **Type Hinting:** All Python functions must have full type hints (`def func(a: int) -> str:`).
3.  **Modular Structure:** Do not dump everything into one file. Separate `bot`, `api`, `workflows`, `activities`, and `database` logic.
4.  **Configuration:** NEVER hardcode credentials. Use `python-dotenv` to load `DISCORD_TOKEN`, `SUPABASE_KEY`, `PRIVATE_KEY`, etc.

**Error Handling:**
1.  **Graceful Degradation:** If the blockchain mint fails, the Discord user should still receive a notification (e.g., "Rating saved, but on-chain minting failed. Retrying...").
2.  **Logging:** Use the standard `logging` library. Log entry and exit of workflows.

**Security:**
1.  **Input Validation:** Sanitize all inputs coming from Discord interactions.
2.  **Wallet Safety:** Never expose the signer's private key in logs.

**Testing**
1. Take a test first approach (follow TDD principles). Build the tests for the functionality being built then implement the feature. Iterating on it until the tests pass.

**Other Rules**
1. Ask for clarification if needed.

---

## 3. Data Models (Supabase/PostgreSQL)
Generate a `schema.sql` file with these tables:

**1. `users`**
* `discord_id` (Primary Key, BigInt)
* `wallet_address` (String, Nullable - must be 0x hex)
* `created_at` (Timestamp)

**2. `validations`**
* `id` (Primary Key, UUID)
* `validator_id` (BigInt, FK to users)
* `target_message_id` (BigInt)
* `target_user_id` (BigInt, FK to users)
* `channel_id` (BigInt)
* `metrics_json` (JSONB) - Stores the array of 5 scores.
* `calculated_score` (Float) - The average 0-5 score.
* `created_at` (Timestamp)

**3. `attestations`**
* `uid` (Primary Key, String - The EAS UID)
* `validation_id` (UUID, FK to validations)
* `recipient_wallet` (String)
* `tx_hash` (String)
* `status` (Enum: 'PENDING', 'MINTED', 'FAILED')

---

## 4. Business Logic & Scoring
[cite_start]Implement the scoring logic based on the PoCiv Business Plan[cite: 37]:

**The 5 Metrics:**
1.  Clarity
2.  Respectfulness
3.  Relevance
4.  Evidence / Substance
5.  Constructiveness

**The Formula:**
* Inputs: 5 integers (Scale 0-5).
* [cite_start]Weighting: Equal weighting for MVP (20% each)[cite: 38].
* Calculation: `Final Score = Sum(Metric_i) / 5`.

[cite_start]**Thresholds[cite: 14]:**
* **Bronze:** 3.0 - 3.9
* **Silver:** 4.0 - 4.5
* **Gold:** 4.6 - 5.0
* *Note: Scores below 3.0 are recorded in the DB but DO NOT trigger an attestation.*

---

## 5. Workflow Architecture

### A. Discord Interaction (The Trigger)
1.  Validator right-clicks a message -> Apps -> **"Rate Civility"**.
2.  Bot opens a **Modal** with 5 input fields (Integer 0-5) corresponding to the metrics above.
3.  On Submit: Bot sends a payload to FastAPI endpoint `/submit-rating`.

### B. Temporal Workflow (`CivilityRatingWorkflow`)
The API triggers this workflow. It must contain these activities:

* **Activity 1: `calculate_and_store`**
    * Validate inputs (0-5 range).
    * Calculate average.
    * Insert record into `validations` table.
    * Return the `validation_id` and `score`.

* **Activity 2: `check_eligibility`**
    * If `score < 3.0`, return "Not Eligible" and end workflow.
    * Fetch `wallet_address` for the `target_user_id` from DB.
    * If no wallet is linked, return "No Wallet" (Trigger a bot DM to the user asking them to link wallet).

* **Activity 3: `mint_attestation`**
    * *Retry Policy:* exponential backoff (max 5 attempts).
    * Construct the EAS payload (see Appendix).
    * Sign and broadcast transaction.
    * Wait for receipt and return `EAS UID`.

* **Activity 4: `notify_discord`**
    * React to the original message with the appropriate medal emoji (🥉, 🥈, 🥇).
    * Send a DM to the target user: "You earned a [Tier] Civility Stamp! View on EAS: [Link]."

---

## 6. Appendix: EAS Schema Details
You must implement the `mint_attestation` activity using this exact schema strategy to ensure data portability.

**Schema String:**
`uint16 scaledScore, uint8[] metricRatings, string sourceRef, string communityContext`

**Data Mapping Rules:**
1.  **`scaledScore` (uint16):** Take the calculated float (e.g., 4.25), multiply by 100, cast to int (Result: 425).
2.  **`metricRatings` (uint8[]):** An array of the 5 raw inputs. MUST follow this order:
    * [0]: Clarity
    * [1]: Respectfulness
    * [2]: Relevance
    * [3]: Evidence
    * [4]: Constructiveness
3.  **`sourceRef` (string):** Format as `discord:{channel_id}:{message_id}` to prevents replay attacks.
4.  **`communityContext` (string):** Hardcode to `"mvp_pilot_v1"`.

---

## 7. Deliverables
Generate the following files:
1.  `schema.sql` (Database setup)
2.  `activities.py` (Temporal activities)
3.  `workflows.py` (Temporal workflow definition)
4.  `api.py` (FastAPI entry point)
5.  `bot.py` (Discord bot logic)
6.  `.env.example` (Template for secrets)