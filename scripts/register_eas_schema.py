#!/usr/bin/env python3
"""
Register EAS schema on Optimism Sepolia.

This script registers a new schema with the Ethereum Attestation Service (EAS)
on Optimism Sepolia testnet.

Schema: uint16 scaledScore, uint8[] metricRatings, string sourceRef, string communityContext

Usage:
    python scripts/register_eas_schema.py

The script will:
1. Connect to Optimism Sepolia RPC
2. Register the schema with EAS
3. Output the schema UID (add this to your .env file as EAS_SCHEMA_UID)
"""

import sys
from pathlib import Path

# Add src to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from web3 import Web3
from eth_abi import encode

from src.config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# EAS SchemaRegistry ABI (simplified - only includes registerSchema function)
EAS_SCHEMA_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "schema", "type": "string"},
            {
                "internalType": "contract ISchemaResolver",
                "name": "resolver",
                "type": "address",
            },
            {"internalType": "bool", "name": "revocable", "type": "bool"},
        ],
        "name": "register",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


def register_schema():
    """Register the schema on EAS."""
    logger.info("Starting EAS schema registration...")

    # Connect to Optimism Sepolia
    w3 = Web3(Web3.HTTPProvider(config.OPTIMISM_SEPOLIA_RPC_URL))
    if not w3.is_connected():
        logger.error("Failed to connect to Optimism Sepolia RPC")
        return False

    logger.info(f"✓ Connected to Optimism Sepolia RPC")

    # Validate private key is set
    if not config.PRIVATE_KEY:
        logger.error(
            "PRIVATE_KEY not set in environment. Please set it in your .env file."
        )
        return False

    # Get account from private key
    try:
        account = w3.eth.account.from_key(config.PRIVATE_KEY)
        logger.info(f"✓ Using account: {account.address}")
    except Exception as e:
        logger.error(f"Failed to load private key: {e}")
        return False

    # Get account balance
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, "ether")
    logger.info(f"  Account balance: {balance_eth:.4f} ETH")

    if balance == 0:
        logger.warning(
            "⚠ Account has no balance. You'll need ETH on Optimism Sepolia testnet."
        )
        logger.warning("  Get testnet ETH from: https://app.optimism.io/faucet")
        return False

    # EAS SchemaRegistry address on Optimism Sepolia
    # https://docs.attest.sh/docs/contract-deployments
    schema_registry_address = Web3.to_checksum_address(
        "0x4200000000000000000000000000000000000020"
    )

    # Schema definition
    # Format: "uint16 scaledScore, uint8[] metricRatings, string sourceRef, string communityContext"
    schema_string = (
        "uint16 scaledScore, uint8[] metricRatings, string sourceRef, string communityContext"
    )

    logger.info(f"Schema: {schema_string}")

    # Create contract instance
    schema_registry = w3.eth.contract(
        address=schema_registry_address, abi=EAS_SCHEMA_REGISTRY_ABI
    )

    # Prepare transaction
    try:
        # No resolver address (0x0) and revocable = false
        resolver_address = "0x0000000000000000000000000000000000000000"

        # Build transaction
        tx = schema_registry.functions.register(
            schema_string,  # schema
            resolver_address,  # resolver
            False,  # revocable
        ).build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
                "gasPrice": w3.eth.gas_price,
            }
        )

        # Estimate gas
        try:
            gas_estimate = w3.eth.estimate_gas(tx)
            tx["gas"] = int(gas_estimate * 1.2)  # 20% buffer
            logger.info(f"  Estimated gas: {tx['gas']}")
        except Exception as e:
            logger.warning(f"  Could not estimate gas: {e}, using default")
            tx["gas"] = 200000

        logger.info("✓ Transaction prepared")
        logger.info(f"  To: {tx['to']}")
        logger.info(f"  Gas: {tx['gas']}")
        logger.info(f"  Gas Price: {w3.from_wei(tx['gasPrice'], 'gwei')} gwei")

    except Exception as e:
        logger.error(f"Failed to prepare transaction: {e}")
        return False

    # Sign and send transaction
    try:
        logger.info("Signing transaction...")
        signed_tx = w3.eth.account.sign_transaction(tx, config.PRIVATE_KEY)
        logger.info("✓ Transaction signed")

        logger.info("Sending transaction...")
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash_hex = tx_hash.hex()
        logger.info(f"✓ Transaction sent: {tx_hash_hex}")

        # Wait for receipt
        logger.info("Waiting for transaction receipt...")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

        if tx_receipt["status"] == 1:
            logger.info("✓ Transaction confirmed!")

            # Extract schema UID from logs
            # The register function returns the schema ID, but we can also get it from logs
            if len(tx_receipt["logs"]) > 0:
                # The first log should contain the SchemaRegistered event
                logger.info(f"  Transaction Hash: {tx_receipt['transactionHash'].hex()}")
                logger.info(f"  Block Number: {tx_receipt['blockNumber']}")

                # Try to decode the return value
                # Note: Web3.py doesn't easily decode return values from receipts,
                # so we'll use the transaction input to extract the schema UID
                logger.info("\n" + "=" * 60)
                logger.info("SCHEMA REGISTRATION SUCCESSFUL!")
                logger.info("=" * 60)
                logger.info(
                    "\nTo get your schema UID, check the transaction receipt:"
                )
                logger.info(
                    f"Optimism Sepolia Explorer: https://sepolia-optimism.etherscan.io/tx/{tx_hash_hex}"
                )
                logger.info(
                    "\nLook for the 'SchemaRegistered' event in the transaction logs."
                )
                logger.info("The schema UID will be the indexed 'uid' parameter.\n")
                logger.info("Once you have the schema UID, add it to your .env file:")
                logger.info("  EAS_SCHEMA_UID=<your-schema-uid-here>\n")

            else:
                logger.warning("No logs found in transaction receipt")

            return True
        else:
            logger.error(f"✗ Transaction failed: {tx_receipt}")
            return False

    except Exception as e:
        logger.error(f"Failed to send transaction: {e}")
        return False


if __name__ == "__main__":
    success = register_schema()
    sys.exit(0 if success else 1)
