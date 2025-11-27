"""EAS client for creating on-chain attestations on Optimism Sepolia."""

import logging
from typing import Any

from web3 import Web3
from web3.types import TxReceipt

from ..config import config

logger = logging.getLogger(__name__)


class EASClient:
    """Client for interacting with EAS on Optimism Sepolia."""

    def __init__(self) -> None:
        """Initialize EAS client with web3 connection."""
        self.w3 = Web3(Web3.HTTPProvider(config.OPTIMISM_SEPOLIA_RPC_URL))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Optimism Sepolia RPC")

        self.account = self.w3.eth.account.from_key(config.PRIVATE_KEY)
        self.eas_contract_address = Web3.to_checksum_address(
            config.EAS_CONTRACT_ADDRESS
        )
        self.schema_uid = config.EAS_SCHEMA_UID

        logger.info(f"EAS Client initialized for {self.eas_contract_address}")

    def create_attestation(
        self,
        recipient: str,
        scaled_score: int,
        metric_ratings: list[int],
        source_ref: str,
        community_context: str = "mvp_pilot_v1",
    ) -> tuple[str, str]:
        """
        Create an EAS attestation with the specified schema.

        Args:
            recipient: Wallet address of the recipient (0x format)
            scaled_score: Score multiplied by 100 (uint16)
            metric_ratings: Array of 5 metric ratings (uint8[])
            source_ref: Source reference string (discord:channel_id:message_id)
            community_context: Community context string (default: "mvp_pilot_v1")

        Returns:
            Tuple of (attestation_uid, transaction_hash)

        Raises:
            ValueError: If inputs are invalid
            Exception: If transaction fails
        """
        if len(metric_ratings) != 5:
            raise ValueError(f"Expected 5 metric ratings, got {len(metric_ratings)}")

        for rating in metric_ratings:
            if not isinstance(rating, int) or rating < 0 or rating > 5:
                raise ValueError(f"Metric rating must be 0-5, got {rating}")

        if not self.w3.is_address(recipient):
            raise ValueError(f"Invalid recipient address: {recipient}")

        # Encode the schema data
        # Schema: uint16 scaledScore, uint8[] metricRatings, string sourceRef, string communityContext
        from eth_abi import encode

        encoded_data = encode(
            ["uint16", "uint8[]", "string", "string"],
            [scaled_score, metric_ratings, source_ref, community_context],
        )

        # Get EAS contract ABI (simplified - in production, load full ABI)
        # For MVP, we'll use a basic attest function call
        # Note: This is a simplified implementation. In production, you'd use the full EAS SDK
        eas_abi = [
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "schema", "type": "bytes32"},
                    {
                        "internalType": "tuple",
                        "name": "data",
                        "type": "tuple",
                        "components": [
                            {
                                "internalType": "address",
                                "name": "recipient",
                                "type": "address",
                            },
                            {
                                "internalType": "uint64",
                                "name": "expirationTime",
                                "type": "uint64",
                            },
                            {
                                "internalType": "bool",
                                "name": "revocable",
                                "type": "bool",
                            },
                            {
                                "internalType": "bytes32",
                                "name": "refUID",
                                "type": "bytes32",
                            },
                            {"internalType": "bytes", "name": "data", "type": "bytes"},
                            {
                                "internalType": "uint256",
                                "name": "value",
                                "type": "uint256",
                            },
                        ],
                    },
                ],
                "name": "attest",
                "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
                "stateMutability": "payable",
                "type": "function",
            },
            {
                "anonymous": False,
                "inputs": [
                    {
                        "indexed": True,
                        "internalType": "bytes32",
                        "name": "uid",
                        "type": "bytes32",
                    },
                    {
                        "indexed": True,
                        "internalType": "bytes32",
                        "name": "schema",
                        "type": "bytes32",
                    },
                    {
                        "indexed": False,
                        "internalType": "address",
                        "name": "recipient",
                        "type": "address",
                    },
                    {
                        "indexed": False,
                        "internalType": "address",
                        "name": "attester",
                        "type": "address",
                    },
                    {
                        "indexed": False,
                        "internalType": "uint64",
                        "name": "expirationTime",
                        "type": "uint64",
                    },
                    {
                        "indexed": False,
                        "internalType": "bool",
                        "name": "revocable",
                        "type": "bool",
                    },
                    {
                        "indexed": False,
                        "internalType": "bytes32",
                        "name": "refUID",
                        "type": "bytes32",
                    },
                    {
                        "indexed": False,
                        "internalType": "bytes",
                        "name": "data",
                        "type": "bytes",
                    },
                ],
                "name": "Attested",
                "type": "event",
            },
        ]

        contract = self.w3.eth.contract(address=self.eas_contract_address, abi=eas_abi)

        # Prepare attestation data
        recipient_address = Web3.to_checksum_address(recipient)
        # Schema UID should be bytes32 (64 hex characters = 32 bytes)
        # Remove 0x prefix if present and pad/truncate to 32 bytes
        schema_uid_hex = self.schema_uid.replace("0x", "")
        if len(schema_uid_hex) != 64:
            raise ValueError(
                f"Schema UID must be 64 hex characters (32 bytes), got {len(schema_uid_hex)}"
            )
        schema_uid_bytes = bytes.fromhex(schema_uid_hex)

        # Build the attestation data tuple
        attestation_data = (
            recipient_address,  # recipient
            0,  # expirationTime (0 = no expiration)
            False,  # revocable
            b"\x00" * 32,  # refUID (no reference)
            encoded_data,  # data
            0,  # value
        )

        # Build transaction
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        gas_price = self.w3.eth.gas_price

        transaction = contract.functions.attest(
            schema_uid_bytes, attestation_data
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "gasPrice": gas_price,
                "chainId": 11155420,  # Optimism Sepolia chain ID
            }
        )

        # Sign and send transaction
        signed_txn = self.account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        logger.info(f"Transaction sent: {tx_hash.hex()}")

        # Wait for receipt
        receipt: TxReceipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status != 1:
            raise Exception(f"Transaction failed: {tx_hash.hex()}")

        # Extract UID from Attested event in transaction logs
        # The EAS contract emits an Attested event with the attestation UID
        attestation_uid = None
        if receipt.logs:
            # Parse the Attested event from logs
            attested_event = contract.events.Attested()
            for log in receipt.logs:
                try:
                    decoded_event = attested_event.process_log(log)
                    # UID is bytes32, convert to hex string with 0x prefix
                    uid_value = decoded_event.args.uid
                    # Handle both bytes and HexBytes types
                    if hasattr(uid_value, "hex"):
                        attestation_uid = "0x" + uid_value.hex()
                    elif isinstance(uid_value, bytes):
                        attestation_uid = "0x" + uid_value.hex()
                    else:
                        # Fallback: convert to hex string
                        attestation_uid = Web3.to_hex(uid_value)
                    logger.info(
                        f"Extracted attestation UID from event: {attestation_uid}"
                    )
                    break
                except Exception as e:
                    # Not the Attested event, continue searching
                    logger.debug(f"Skipping log entry (not Attested event): {e}")
                    continue

        if not attestation_uid:
            # Fallback: try to get the return value from the transaction
            # This requires calling the function directly, which we can't do after the fact
            # So we'll raise an error instead
            raise Exception(
                f"Could not extract attestation UID from transaction {tx_hash.hex()}. "
                "Attested event not found in transaction logs."
            )

        logger.info(f"Attestation created: UID={attestation_uid}, TX={tx_hash.hex()}")

        return attestation_uid, tx_hash.hex()
