"""
Represents a simulated IoT node equipped with an ECDSA secp256k1 Ethereum keypair,
Heinzelman physical battery state, radio transceiver status, and telemetry generator.
"""
import time
import math
from typing import Optional, Dict, Any
from eth_account import Account
from eth_account.messages import encode_defunct
from .models import IoTDeviceSpec, TelemetryPacket, BlockProposal, ConsensusVote
from .energy_model import HeinzelmanEnergyModel, HardwarePreset


class IoTNode:
    """
    Simulated physical IoT device operating on an ESP32 microcontroller profile.
    Holds a real Ethereum private key, signs blocks, and drains battery based on radio physics.
    """

    def __init__(
        self,
        node_id: str,
        initial_battery_pct: float = 100.0,
        base_latency_ms: float = 25.0,
        initial_reputation: float = 1.0,
        hardware: HardwarePreset = HardwarePreset.ESP32,
        private_key: Optional[str] = None
    ):
        self.node_id = node_id
        self.hardware = hardware
        self.spec = IoTDeviceSpec(device_id=node_id, model_name=hardware.value)
        self.energy_model = HeinzelmanEnergyModel(hardware=hardware)
        
        # Cryptographic Identity (Ethereum Account)
        if private_key:
            self.account = Account.from_key(private_key)
        else:
            self.account = Account.create()
        self.address = self.account.address

        # Physical and Operational State
        self.battery_pct = max(0.0, min(100.0, initial_battery_pct))
        self.total_joules = self.spec.battery_capacity_joules
        self.residual_joules = (self.battery_pct / 100.0) * self.total_joules
        self.base_latency_ms = base_latency_ms
        self.reputation = max(0.0, min(1.0, initial_reputation))
        self.is_alive = self.battery_pct > 0.0

        # Consensus role tracking for the current epoch
        self.is_validator = False
        self.is_leader = False
        self.last_round_energy_joules = 0.0
        self.total_energy_consumed_joules = 0.0
        self.blocks_signed = 0
        self.blocks_proposed = 0

    def generate_telemetry(self, latency_jitter_ms: float = 0.0) -> TelemetryPacket:
        """Emits real-time telemetry packet to the edge controller."""
        effective_latency = max(5.0, self.base_latency_ms + latency_jitter_ms)
        return TelemetryPacket(
            node_id=self.node_id,
            address=self.address,
            timestamp=time.time(),
            battery_percentage=round(self.battery_pct, 2),
            residual_joules=round(self.residual_joules, 2),
            latency_ms=round(effective_latency, 2),
            reputation_score=round(self.reputation, 3),
            is_alive=self.is_alive
        )

    def sign_block_proposal(self, block_hash: str) -> str:
        """
        Signs a block proposal hash using the node's private key via ECDSA secp256k1.
        Returns a 65-byte hex signature string (r, s, v).
        """
        if not self.is_alive:
            raise RuntimeError(f"Cannot sign: Node {self.node_id} is depleted/dead.")
        
        # Prepare eth_sign compatible message
        message = encode_defunct(hexstr=block_hash)
        signed_message = self.account.sign_message(message)
        self.blocks_signed += 1
        return signed_message.signature.hex()

    def discharge_round_energy(
        self,
        committee_size: int,
        distance_m: float = 30.0,
        epoch_duration_s: float = 2.0,
        drain_multiplier: float = 1.0
    ) -> float:
        """
        Calculates and deducts energy consumed during the consensus round based on role.
        """
        if not self.is_alive:
            return 0.0

        base_energy_j = self.energy_model.calculate_round_energy(
            is_validator=self.is_validator,
            is_leader=self.is_leader,
            committee_size=committee_size,
            distance_m=distance_m,
            epoch_duration_s=epoch_duration_s
        )
        energy_j = base_energy_j * drain_multiplier

        self.last_round_energy_joules = energy_j
        self.total_energy_consumed_joules += energy_j
        self.residual_joules = max(0.0, self.residual_joules - energy_j)
        self.battery_pct = max(0.0, (self.residual_joules / self.total_joules) * 100.0)

        if self.residual_joules <= 0.0 or self.battery_pct <= 0.0:
            self.battery_pct = 0.0
            self.is_alive = False
            self.is_validator = False
            self.is_leader = False

        return energy_j

    def set_consensus_role(self, is_validator: bool, is_leader: bool = False):
        """Sets role for the upcoming epoch."""
        self.is_validator = is_validator
        self.is_leader = is_leader
        if is_leader:
            self.blocks_proposed += 1

    def force_drain_battery(self, target_pct: float):
        """Allows testing dynamic rotation by manually draining battery."""
        self.battery_pct = max(0.0, min(100.0, target_pct))
        self.residual_joules = (self.battery_pct / 100.0) * self.total_joules
        if self.battery_pct == 0.0:
            self.is_alive = False
