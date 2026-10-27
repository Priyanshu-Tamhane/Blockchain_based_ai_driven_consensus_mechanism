"""
Web3 Client bridging the Python AI Engine with local Hardhat EVM smart contracts.
Handles contract loading, transaction submission, and signature payload encoding.
"""
import os
import json
from typing import List, Dict, Any, Optional
from web3 import Web3
from eth_account import Account


class BlockchainClient:
    """Interacts with NodeRegistry and AdaptiveConsensus contracts on EVM."""

    def __init__(
        self,
        rpc_url: str = "http://127.0.0.1:8545",
        deployment_file: str = "contracts_data/deployment.json",
        artifacts_dir: str = "artifacts/contracts"
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.deployment_file = deployment_file
        self.artifacts_dir = artifacts_dir
        
        # Default account (Hardhat Account #0)
        self.default_account = self.w3.eth.accounts[0] if self.w3.is_connected() and len(self.w3.eth.accounts) > 0 else None
        
        self.registry_contract = None
        self.consensus_contract = None
        self.deployment_info = {}

        if os.path.exists(self.deployment_file):
            self.load_contracts()

    def is_connected(self) -> bool:
        return self.w3.is_connected()

    def load_contracts(self):
        """Loads deployed contract addresses and compiled ABIs."""
        with open(self.deployment_file, "r") as f:
            self.deployment_info = json.load(f)

        registry_abi_path = os.path.join(self.artifacts_dir, "NodeRegistry.sol", "NodeRegistry.json")
        consensus_abi_path = os.path.join(self.artifacts_dir, "AdaptiveConsensus.sol", "AdaptiveConsensus.json")

        with open(registry_abi_path, "r") as f:
            registry_artifact = json.load(f)
            self.registry_contract = self.w3.eth.contract(
                address=self.deployment_info["registryAddress"],
                abi=registry_artifact["abi"]
            )

        with open(consensus_abi_path, "r") as f:
            consensus_artifact = json.load(f)
            self.consensus_contract = self.w3.eth.contract(
                address=self.deployment_info["consensusAddress"],
                abi=consensus_artifact["abi"]
            )

    def register_node(self, node_address: str, device_id: str, reputation_score: int = 950) -> str:
        """Registers a node in NodeRegistry contract. Reputation is scaled by 1000 (950 = 0.95)."""
        tx_hash = self.registry_contract.functions.registerNode(
            Web3.to_checksum_address(node_address),
            device_id,
            reputation_score
        ).transact({"from": self.default_account})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.transactionHash.hex()

    def schedule_epoch_committee(
        self,
        epoch_id: int,
        committee_addresses: List[str],
        leader_address: str
    ) -> Dict[str, Any]:
        """Submits elected committee schedule to AdaptiveConsensus.sol."""
        checksum_members = [Web3.to_checksum_address(addr) for addr in committee_addresses]
        checksum_leader = Web3.to_checksum_address(leader_address)

        tx_hash = self.consensus_contract.functions.setEpochCommittee(
            epoch_id,
            checksum_members,
            checksum_leader
        ).transact({"from": self.default_account})
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {
            "tx_hash": receipt.transactionHash.hex(),
            "gas_used": receipt.gasUsed,
            "status": receipt.status
        }

    def compute_block_raw_hash(
        self,
        epoch_id: int,
        block_number: int,
        state_root: str,
        telemetry_hash: str
    ) -> str:
        """Computes matching keccak256 hash formatted as bytes32."""
        raw_hash = Web3.solidity_keccak(
            ["uint256", "uint256", "bytes32", "bytes32"],
            [
                epoch_id,
                block_number,
                bytes.fromhex(state_root.replace("0x", "")),
                bytes.fromhex(telemetry_hash.replace("0x", ""))
            ]
        )
        return raw_hash.hex()

    def commit_block(
        self,
        epoch_id: int,
        block_number: int,
        state_root: str,
        telemetry_hash: str,
        signatures: List[str]
    ) -> Dict[str, Any]:
        """Submits block proposal with aggregated signatures for on-chain quorum validation."""
        bytes_signatures = [bytes.fromhex(sig.replace("0x", "")) for sig in signatures]

        tx_hash = self.consensus_contract.functions.commitBlock(
            epoch_id,
            block_number,
            bytes.fromhex(state_root.replace("0x", "")),
            bytes.fromhex(telemetry_hash.replace("0x", "")),
            bytes_signatures
        ).transact({"from": self.default_account, "gas": 3000000})

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {
            "tx_hash": receipt.transactionHash.hex(),
            "gas_used": receipt.gasUsed,
            "block_number": receipt.blockNumber,
            "status": receipt.status
        }

    def get_latest_block_number(self) -> int:
        return self.consensus_contract.functions.latestBlockNumber().call()

    def slash_node(self, node_address: str, reason: str) -> str:
        """Executes on-chain slashing for a malicious node via NodeRegistry.sol."""
        checksum_addr = Web3.to_checksum_address(node_address)
        tx_hash = self.registry_contract.functions.slashNode(
            checksum_addr,
            reason
        ).transact({"from": self.default_account})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.transactionHash.hex()

    def update_reputation(self, node_address: str, new_reputation: int) -> str:
        """Updates reputation score in NodeRegistry.sol (scaled by 1000)."""
        checksum_addr = Web3.to_checksum_address(node_address)
        tx_hash = self.registry_contract.functions.updateReputation(
            checksum_addr,
            new_reputation
        ).transact({"from": self.default_account})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.transactionHash.hex()

    def is_node_eligible(self, node_address: str) -> bool:
        """Queries on-chain eligibility for committee selection."""
        checksum_addr = Web3.to_checksum_address(node_address)
        return self.registry_contract.functions.isNodeEligible(checksum_addr).call()

    def get_node_info(self, node_address: str) -> Dict[str, Any]:
        """Queries node metadata and slashing status from NodeRegistry.sol."""
        checksum_addr = Web3.to_checksum_address(node_address)
        info = self.registry_contract.functions.nodes(checksum_addr).call()
        return {
            "address": info[0],
            "device_id": info[1],
            "reputation_score": info[2] / 1000.0,
            "status": info[3],  # 0=Inactive, 1=Active, 2=Suspended, 3=Slashed
            "registered_at": info[4],
            "blocks_validated": info[5],
            "blocks_proposed": info[6]
        }
