"""
End-to-end Consensus Orchestrator.
Coordinates:
  1. Telemetry gathering from virtual IoT fleet
  2. Multi-Objective AI committee election (K_t >= 3f + 1, Battery > 15%)
  3. On-chain epoch scheduling on AdaptiveConsensus.sol
  4. Cryptographic signing of block proposals by elected validators
  5. On-chain quorum threshold verification (>= floor(2/3*K) + 1)
  6. Post-round Heinzelman physical battery discharge
"""
import time
import hashlib
from typing import Dict, Any, List, Optional
from simulator.fleet_simulator import IoTFleetSimulator
from simulator.energy_model import HardwarePreset
from ai_engine.objective import MultiObjectiveOptimizer, ObjectiveWeights, SystemConstraints
from .web3_client import BlockchainClient


class ConsensusOrchestrator:
    """Orchestrates rounds between IoT Fleet, AI Engine, and EVM Settlement Layer."""

    def __init__(
        self,
        node_count: int = 12,
        hardware: HardwarePreset = HardwarePreset.ESP32,
        use_blockchain: bool = True,
        rpc_url: str = "http://127.0.0.1:8545"
    ):
        self.simulator = IoTFleetSimulator(node_count=node_count, default_hardware=hardware)
        self.optimizer = MultiObjectiveOptimizer(
            weights=ObjectiveWeights(w_security=0.35, w_energy=0.45, w_latency=0.20),
            constraints=SystemConstraints(
                min_battery_threshold=15.0,
                min_reputation_floor=0.60,
                byzantine_tolerance_f=1
            )
        )
        self.use_blockchain = use_blockchain
        self.blockchain: Optional[BlockchainClient] = None
        self.current_epoch = 0
        self.current_block = 0
        self.history: List[Dict[str, Any]] = []

        if use_blockchain:
            self.blockchain = BlockchainClient(rpc_url=rpc_url)
            if self.blockchain.is_connected():
                self._register_fleet_on_chain()

    def _register_fleet_on_chain(self):
        """Registers all simulated nodes in the on-chain NodeRegistry contract."""
        print(f"[*] Registering {len(self.simulator.nodes)} fleet nodes into NodeRegistry.sol...")
        for node in self.simulator.nodes.values():
            try:
                rep_scaled = int(node.reputation * 1000)
                self.blockchain.register_node(node.address, node.node_id, rep_scaled)
            except Exception as e:
                # Might already be registered
                pass

    def run_epoch(self) -> Dict[str, Any]:
        """Executes a single end-to-end consensus epoch."""
        self.current_epoch += 1
        self.current_block += 1
        epoch_id = self.current_epoch
        block_num = self.current_block

        # 1. Telemetry Ingestion
        telemetry = self.simulator.gather_telemetry()

        # 2. AI Multi-Objective Committee Selection
        directive = self.optimizer.select_committee(epoch_id=epoch_id, telemetry=telemetry)
        self.simulator.apply_committee_directive(directive)

        schedule_tx = None
        commit_tx = None

        # 3. Schedule Epoch Committee on EVM
        if self.use_blockchain and self.blockchain and self.blockchain.is_connected():
            schedule_tx = self.blockchain.schedule_epoch_committee(
                epoch_id=epoch_id,
                committee_addresses=directive.members,
                leader_address=directive.leader_address
            )

        # 4. Propose Block & Cryptographic Hashing
        state_root = "0x" + hashlib.sha256(f"state_epoch_{epoch_id}_blk_{block_num}".encode()).hexdigest()
        telemetry_raw = "".join(f"{t.node_id}:{t.battery_percentage}" for t in telemetry)
        telemetry_hash = "0x" + hashlib.sha256(telemetry_raw.encode()).hexdigest()

        if self.use_blockchain and self.blockchain and self.blockchain.is_connected():
            raw_hash = self.blockchain.compute_block_raw_hash(
                epoch_id, block_num, state_root, telemetry_hash
            )
        else:
            raw_hash = "0x" + hashlib.sha256(f"{epoch_id}{block_num}{state_root}{telemetry_hash}".encode()).hexdigest()

        # 5. Committee Signatures
        signatures = self.simulator.collect_committee_signatures(directive, raw_hash)

        # 6. Submit Block & Quorum Verification on EVM
        if self.use_blockchain and self.blockchain and self.blockchain.is_connected():
            commit_tx = self.blockchain.commit_block(
                epoch_id=epoch_id,
                block_number=block_num,
                state_root=state_root,
                telemetry_hash=telemetry_hash,
                signatures=signatures
            )

        # 7. Physical Energy Discharge across fleet
        self.simulator.discharge_fleet_round(
            committee_size=directive.committee_size,
            distance_m=30.0,
            epoch_duration_s=2.0
        )

        # Round Summary Record
        leader_node = self.simulator.get_node_by_address(directive.leader_address)
        round_summary = {
            "epoch_id": epoch_id,
            "block_number": block_num,
            "committee_size": directive.committee_size,
            "quorum_threshold": directive.quorum_threshold,
            "signatures_collected": len(signatures),
            "leader_id": leader_node.node_id if leader_node else "Unknown",
            "leader_address": directive.leader_address,
            "utility_score": directive.metadata.get("utility", 0.0),
            "avg_committee_battery": directive.metadata.get("avg_battery_pct", 0.0),
            "schedule_gas": schedule_tx["gas_used"] if schedule_tx else 0,
            "commit_gas": commit_tx["gas_used"] if commit_tx else 0,
            "on_chain_success": commit_tx["status"] == 1 if commit_tx else True,
            "alive_nodes_count": sum(1 for n in self.simulator.nodes.values() if n.is_alive)
        }
        self.history.append(round_summary)
        return round_summary
