#!/usr/bin/env python3
"""
Simple helper script to register EAS schema on Optimism Sepolia.

This script provides step-by-step guidance for registering your schema.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config


def main():
    """Show instructions for schema registration."""
    print("\n" + "=" * 70)
    print("EAS SCHEMA REGISTRATION HELPER")
    print("=" * 70)

    print("\nYour Schema Details:")
    print("-" * 70)
    print("Schema: uint16 scaledScore, uint8[] metricRatings, string sourceRef, string communityContext")
    print("Network: Optimism Sepolia")
    print("Chain ID: 11155420")
    print("\n")

    print("Method 1: Using This Script (Automated)")
    print("-" * 70)
    print("Run the automated registration script:")
    print("  python scripts/register_eas_schema.py\n")
    print("This will:")
    print("  1. Sign and submit a transaction to register your schema")
    print("  2. Wait for confirmation")
    print("  3. Return your schema UID\n")

    print("Method 2: Manual Registration (Web UI)")
    print("-" * 70)
    print("Alternatively, register manually on the EAS website:")
    print("  1. Go to: https://optimism-sepolia-eas.vercel.app/")
    print("  2. Click 'Create Schema'")
    print("  3. Enter your schema definition:")
    print("     uint16 scaledScore, uint8[] metricRatings, string sourceRef, string communityContext")
    print("  4. Set Resolver to: 0x0000000000000000000000000000000000000000")
    print("  5. Set Revocable to: No")
    print("  6. Click 'Attest' to submit")
    print("  7. Copy your schema UID from the transaction receipt\n")

    print("Prerequisites for Automated Method:")
    print("-" * 70)
    print(f"Private Key configured: {'✓' if config.PRIVATE_KEY else '✗ Missing'}")
    print(f"Optimism Sepolia RPC: {config.OPTIMISM_SEPOLIA_RPC_URL}")
    print(f"EAS Contract Address: {config.EAS_CONTRACT_ADDRESS}\n")

    if not config.PRIVATE_KEY:
        print("⚠ To use the automated method, set PRIVATE_KEY in your .env file")
        print("  PRIVATE_KEY=0x<your-private-key-without-0x-prefix>\n")

    print("After Registration:")
    print("-" * 70)
    print("1. You'll receive a schema UID (64 hex characters)")
    print("2. Add it to your .env file:")
    print("   EAS_SCHEMA_UID=<your-schema-uid>\n")
    print("3. Your application will use this UID for all attestations\n")

    print("Need Testnet ETH?")
    print("-" * 70)
    print("Get free testnet ETH from:")
    print("  https://app.optimism.io/faucet\n")

    print("Learn More:")
    print("-" * 70)
    print("EAS Docs: https://docs.attest.sh/")
    print("Optimism Sepolia: https://docs.optimism.io/builders/dapp-developers/testnet\n")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
