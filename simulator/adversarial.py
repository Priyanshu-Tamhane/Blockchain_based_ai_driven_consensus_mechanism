"""
Adversarial Attack Simulation Engine for Phase 5.
Simulates canonical Byzantine and IoT-specific attack vectors:
  1. Telemetry Spoofing (Free-rider attack: fake 100% battery / low latency)
  2. Byzantine Equivocation (Double-signing conflicting block proposals)
  3. Sybil Infiltration (Unauthorized ghost nodes attempting consensus participation)
  4. Silent Dropping / Eclipse (Validator non-responsiveness / DoS)
"""
import enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from eth_account import Account
import hashlib

from simulator.models import TelemetryPacket, ConsensusVote, CommitteeDirective
from simulator.iot_node import IoTNode


class AttackType(enum.Enum):
    NONE = "None"
    TELEMETRY_SPOOFING = "Telemetry Spoofing (Free-Rider)"
    BYZANTINE_EQUIVOCATION = "Byzantine Double-Signing (Equivocation)"
    SYBIL_INFILTRATION = "Sybil / Unauthorized Ghost Node"
    SILENT_DROPPING = "Silent Dropping (Non-Responsive Validator)"


@dataclass
class EquivocationPayload:
    """Represents a proof-of-equivocation with two conflicting signed hashes."""
    epoch_id: int
    malicious_node_id: str
    signer_address: str
    hash_a: str
    signature_a: str
    hash_b: str
    signature_b: str


class AdversarialInjector:
    """Manages attack injection across the simulated IoT fleet."""

    def __init__(self):
        self.active_attacks: Dict[str, AttackType] = {}
        # Pre-generate Sybil rogue identity
        self.sybil_account = Account.create()
        self.sybil_node_id = "Rogue_Sybil_Node"

    def arm_attack(self, node_id: str, attack_type: AttackType):
        """Arms an attack on a specific target node."""
        self.active_attacks[node_id] = attack_type

    def disarm_attack(self, node_id: str):
        """Disarms any active attack on a target node."""
        if node_id in self.active_attacks:
            del self.active_attacks[node_id]

    def clear_all_attacks(self):
        """Clears all armed attacks."""
        self.active_attacks.clear()

    def get_attack_for_node(self, node_id: str) -> AttackType:
        """Returns the active attack for a given node."""
        return self.active_attacks.get(node_id, AttackType.NONE)

    def tamper_telemetry(self, node: IoTNode, real_telemetry: TelemetryPacket) -> TelemetryPacket:
        """
        Applies telemetry spoofing if node is armed with TELEMETRY_SPOOFING.
        Fakes 100% battery and ultra-low latency while actual battery is depleted.
        """
        attack = self.get_attack_for_node(node.node_id)
        if attack == AttackType.TELEMETRY_SPOOFING:
            return TelemetryPacket(
                node_id=node.node_id,
                address=node.address,
                battery_percentage=100.0,  # Spoofed high battery
                latency_ms=5.0,             # Spoofed ultra-low latency
                reputation_score=real_telemetry.reputation_score,
                is_alive=True
            )
        return real_telemetry

    def generate_equivocation(
        self,
        node: IoTNode,
        epoch_id: int,
        block_number: int
    ) -> EquivocationPayload:
        """
        Simulates Byzantine Equivocation: generates two conflicting block proposals
        with distinct state roots signed by the same private key at the same epoch.
        """
        hash_a = "0x" + hashlib.sha256(f"legitimate_block_{epoch_id}_{block_number}".encode()).hexdigest()
        hash_b = "0x" + hashlib.sha256(f"conflicting_byzantine_block_{epoch_id}_{block_number}".encode()).hexdigest()

        sig_a = node.sign_hash(hash_a)
        sig_b = node.sign_hash(hash_b)

        return EquivocationPayload(
            epoch_id=epoch_id,
            malicious_node_id=node.node_id,
            signer_address=node.address,
            hash_a=hash_a,
            signature_a=sig_a,
            hash_b=hash_b,
            signature_b=sig_b
        )

    def generate_sybil_vote(self, epoch_id: int, block_hash: str, block_number: int = 1) -> ConsensusVote:
        """
        Generates an unauthorized vote signed by an unregistered Sybil keypair.
        """
        from eth_account.messages import encode_defunct
        message = encode_defunct(hexstr=block_hash)
        signed = self.sybil_account.sign_message(message)
        return ConsensusVote(
            epoch_id=epoch_id,
            block_number=block_number,
            block_hash=block_hash,
            voter_address=self.sybil_account.address,
            signature="0x" + signed.signature.hex()
        )
