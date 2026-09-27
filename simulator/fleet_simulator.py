"""
IoT Fleet Simulator managing an ensemble of physical virtual IoT devices.
Handles telemetry streaming, multi-node cryptographic voting, and post-round energy updates.
"""
import random
from typing import List, Dict, Optional
from .iot_node import IoTNode
from .models import TelemetryPacket, CommitteeDirective, BlockProposal, ConsensusVote
from .energy_model import HardwarePreset


class IoTFleetSimulator:
    """
    Manages a heterogeneous fleet of IoT devices simulating real-world mesh distribution.
    """

    def __init__(
        self,
        node_count: int = 15,
        default_hardware: HardwarePreset = HardwarePreset.ESP32,
        seed: Optional[int] = 42
    ):
        if seed is not None:
            random.seed(seed)

        self.nodes: Dict[str, IoTNode] = {}
        self.node_address_map: Dict[str, IoTNode] = {}

        for i in range(node_count):
            node_id = f"Node_{i:02d}"
            # Realistic spread of initial batteries (e.g. 70% to 100%, with a couple lower)
            init_batt = random.uniform(60.0, 100.0) if i > 1 else random.uniform(20.0, 45.0)
            latency = random.uniform(15.0, 45.0)
            reputation = random.uniform(0.85, 1.0)

            node = IoTNode(
                node_id=node_id,
                initial_battery_pct=init_batt,
                base_latency_ms=latency,
                initial_reputation=reputation,
                hardware=default_hardware
            )
            self.nodes[node_id] = node
            self.node_address_map[node.address.lower()] = node

    def gather_telemetry(self) -> List[TelemetryPacket]:
        """Collects telemetry from all alive nodes in the network."""
        telemetry = []
        for node in self.nodes.values():
            # Add small random latency jitter (+/- 3ms)
            jitter = random.uniform(-3.0, 3.0)
            packet = node.generate_telemetry(latency_jitter_ms=jitter)
            telemetry.append(packet)
        return telemetry

    def apply_committee_directive(self, directive: CommitteeDirective):
        """Configures node roles (Leader, Validator, or Idle) for the epoch."""
        committee_addresses = {addr.lower() for addr in directive.members}
        leader_addr = directive.leader_address.lower()

        for addr, node in self.node_address_map.items():
            if addr == leader_addr:
                node.set_consensus_role(is_validator=True, is_leader=True)
            elif addr in committee_addresses:
                node.set_consensus_role(is_validator=True, is_leader=False)
            else:
                node.set_consensus_role(is_validator=False, is_leader=False)

    def collect_committee_signatures(
        self,
        directive: CommitteeDirective,
        block_hash: str
    ) -> List[str]:
        """
        Gathers real cryptographic ECDSA signatures from active committee members.
        Returns a list of hex signature strings.
        """
        signatures = []
        for addr in directive.members:
            node = self.node_address_map.get(addr.lower())
            if node and node.is_alive and node.is_validator:
                sig = node.sign_block_proposal(block_hash)
                signatures.append(sig)
        return signatures

    def discharge_fleet_round(
        self,
        committee_size: int,
        distance_m: float = 30.0,
        epoch_duration_s: float = 2.0,
        drain_multiplier: float = 1.0
    ):
        """Applies energy dissipation to all fleet nodes based on their epoch role."""
        for node in self.nodes.values():
            node.discharge_round_energy(
                committee_size=committee_size,
                distance_m=distance_m,
                epoch_duration_s=epoch_duration_s,
                drain_multiplier=drain_multiplier
            )

    def get_node_by_address(self, address: str) -> Optional[IoTNode]:
        return self.node_address_map.get(address.lower())

    def get_node(self, node_id: str) -> Optional[IoTNode]:
        return self.nodes.get(node_id)
