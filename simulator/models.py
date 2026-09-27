"""
Core data models and schemas representing IoT physical nodes, telemetry packets,
consensus directives, and cryptographic proposals.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time


@dataclass
class IoTDeviceSpec:
    """Hardware profile specification for an IoT microcontroller."""
    device_id: str
    model_name: str = "ESP32-Xtensa"
    battery_capacity_joules: float = 33300.0  # e.g., 2500 mAh * 3.7V * 3.6
    operating_voltage: float = 3.3            # Volts
    active_current_ma: float = 160.0          # mA during active compute/radio
    sleep_current_ua: float = 15.0            # uA during deep sleep
    clock_frequency_mhz: float = 240.0        # MHz
    tx_power_dbm: float = 14.0                # dBm


@dataclass
class TelemetryPacket:
    """Real-time telemetry packet transmitted from an IoT device to the AI Controller."""
    node_id: str
    address: str                             # Ethereum address (0x...)
    timestamp: float = field(default_factory=time.time)
    battery_percentage: float = 100.0        # [0.0, 100.0] %
    residual_joules: float = 33300.0         # Joules remaining
    latency_ms: float = 25.0                 # Link round-trip propagation latency
    reputation_score: float = 1.0            # Historical honesty/reliability [0.0, 1.0]
    is_alive: bool = True                    # Alive if battery > 0 and responsive


@dataclass
class CommitteeDirective:
    """Directive issued by the AI Controller defining the elected consensus committee."""
    epoch_id: int
    committee_size: int                      # K_t
    members: List[str]                       # List of node Ethereum addresses
    leader_address: str                      # Designated round proposer
    quorum_threshold: int                    # floor(2/3 * K_t) + 1
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, float] = field(default_factory=dict)  # e.g. utility score, avg_battery


@dataclass
class BlockProposal:
    """Candidate block proposed by the designated committee leader."""
    epoch_id: int
    block_number: int
    proposer_address: str
    state_root: str                          # 32-byte hex hash of the consensus state
    telemetry_hash: str                      # Cryptographic root of IoT readings
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConsensusVote:
    """Cryptographic vote (attestation) signed by an active committee member."""
    epoch_id: int
    block_number: int
    block_hash: str
    voter_address: str
    signature: str                           # 65-byte hex ECDSA signature (r, s, v)
    timestamp: float = field(default_factory=time.time)
