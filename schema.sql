-- PoCiv MVP Database Schema for Supabase/PostgreSQL

-- Create enum for attestation status
CREATE TYPE attestation_status AS ENUM ('PENDING', 'MINTED', 'FAILED');

-- Users table
CREATE TABLE users (
    discord_id BIGINT PRIMARY KEY,
    wallet_address VARCHAR(42) CHECK (wallet_address IS NULL OR wallet_address ~ '^0x[a-fA-F0-9]{40}$'),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Validations table
CREATE TABLE validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    validator_id BIGINT NOT NULL REFERENCES users(discord_id),
    target_message_id BIGINT NOT NULL,
    target_user_id BIGINT NOT NULL REFERENCES users(discord_id),
    channel_id BIGINT NOT NULL,
    metrics_json JSONB NOT NULL,
    calculated_score FLOAT NOT NULL CHECK (calculated_score >= 0 AND calculated_score <= 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Attestations table
CREATE TABLE attestations (
    uid VARCHAR(66) PRIMARY KEY,
    validation_id UUID NOT NULL REFERENCES validations(id),
    recipient_wallet VARCHAR(42) NOT NULL CHECK (recipient_wallet ~ '^0x[a-fA-F0-9]{40}$'),
    tx_hash VARCHAR(66) NOT NULL,
    status attestation_status NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_validations_target_user_id ON validations(target_user_id);
CREATE INDEX idx_validations_validator_id ON validations(validator_id);
CREATE INDEX idx_validations_created_at ON validations(created_at);
CREATE INDEX idx_attestations_validation_id ON attestations(validation_id);
CREATE INDEX idx_attestations_status ON attestations(status);
CREATE INDEX idx_users_wallet_address ON users(wallet_address);

