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
from typing import Dict, Any, List, Optional, Set
from simulator.fleet_simulator import IoTFleetSimulator
from simulator.energy_model import HardwarePreset
from simulator.adversarial import AdversarialInjector, AttackType, EquivocationPayload
from ai_engine.objective import MultiObjectiveOptimizer, ObjectiveWeights, SystemConstraints
from ai_engine.defense_detector import ByzantineDefenseDetector, SecurityAlert
from .web3_client import BlockchainClient


class ConsensusOrchestrator:
    """Orchestrates rounds between IoT Fleet, AI Engine, Byzantine Defense, and EVM Settlement Layer."""

    def __init__(
        self,
        node_count: int = 12,
        hardware: HardwarePreset = HardwarePreset.ESP32,
        use_blockchain: bool = True,
        rpc_url: str = "http://127.0.0.1:8545",
        selector: Optional[Any] = None
    ):
        self.simulator = IoTFleetSimulator(node_count=node_count, default_hardware=hardware)
        self.selector = selector or MultiObjectiveOptimizer(
            weights=ObjectiveWeights(w_security=0.35, w_energy=0.45, w_latency=0.20),
            constraints=SystemConstraints(
                min_battery_threshold=15.0,
                min_reputation_floor=0.60,
                byzantine_tolerance_f=1
            )
        )
        self.optimizer = self.selector  # Backwards compatibility alias
        self.adversary = AdversarialInjector()
        self.defense = ByzantineDefenseDetector(hardware=hardware)

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
        """Executes a single end-to-end consensus epoch with active Byzantine defense."""
        self.current_epoch += 1
        self.current_block += 1
        epoch_id = self.current_epoch
        block_num = self.current_block

        # 1. Telemetry Ingestion & Adversarial Tampering
        raw_telemetry = self.simulator.gather_telemetry()
        tampered_telemetry = [
            self.adversary.tamper_telemetry(self.simulator.nodes[t.node_id], t)
            for t in raw_telemetry
        ]

        # 2. Physics-Informed Defense Sanitization
        telemetry = self.defense.verify_telemetry_physics(epoch_id, tampered_telemetry)

        # 3. AI Committee Selection (MCDM Heuristic or DRL Policy Network)
        directive = self.selector.select_committee(epoch_id=epoch_id, telemetry=telemetry)
        self.simulator.apply_committee_directive(directive)
        self.defense.record_epoch_assignments(epoch_id, directive, telemetry)

        # 4. Check for Byzantine Equivocation Attacks
        equivocation_detected = False
        for node_id, attack in list(self.adversary.active_attacks.items()):
            if attack == AttackType.BYZANTINE_EQUIVOCATION:
                node = self.simulator.get_node(node_id)
                if node:
                    proof = self.adversary.generate_equivocation(node, epoch_id, block_num)
                    is_valid, alert = self.defense.verify_and_slash_equivocation(proof)
                    if is_valid:
                        equivocation_detected = True
                        node.reputation = 0.0
                        node.is_validator = False
                        node.is_leader = False
                        if self.use_blockchain and self.blockchain and self.blockchain.is_connected():
                            try:
                                self.blockchain.slash_node(node.address, "Byzantine Double-Signing Equivocation")
                            except Exception:
                                pass

        schedule_tx = None
        commit_tx = None

        # 5. Schedule Epoch Committee on EVM
        if self.use_blockchain and self.blockchain and self.blockchain.is_connected():
            schedule_tx = self.blockchain.schedule_epoch_committee(
                epoch_id=epoch_id,
                committee_addresses=directive.members,
                leader_address=directive.leader_address
            )

        # 6. Propose Block & Cryptographic Hashing
        state_root = "0x" + hashlib.sha256(f"state_epoch_{epoch_id}_blk_{block_num}".encode()).hexdigest()
        telemetry_raw = "".join(f"{t.node_id}:{t.battery_percentage}" for t in telemetry)
        telemetry_hash = "0x" + hashlib.sha256(telemetry_raw.encode()).hexdigest()

        if self.use_blockchain and self.blockchain and self.blockchain.is_connected():
            raw_hash = self.blockchain.compute_block_raw_hash(
                epoch_id, block_num, state_root, telemetry_hash
            )
        else:
            raw_hash = "0x" + hashlib.sha256(f"{epoch_id}{block_num}{state_root}{telemetry_hash}".encode()).hexdigest()

        # 7. Collect Committee Signatures (with Silent Dropping simulation)
        valid_signatures = []
        for addr in directive.members:
            node = self.simulator.get_node_by_address(addr)
            if not node:
                continue
            # Check if node is slashed
            if node.address.lower() in self.defense.slashed_addresses:
                continue
            # Check if node is armed with SILENT_DROPPING
            if self.adversary.get_attack_for_node(node.node_id) == AttackType.SILENT_DROPPING:
                continue

            sig = node.sign_hash(raw_hash)
            valid_signatures.append(sig)

        # 8. Filter Sybil Injection Attacks if armed
        for attack in self.adversary.active_attacks.values():
            if attack == AttackType.SYBIL_INFILTRATION:
                sybil_vote = self.adversary.generate_sybil_vote(epoch_id, raw_hash)
                registered_set = {n.address for n in self.simulator.nodes.values()}
                filtered_votes, sybil_alerts = self.defense.filter_sybil_and_invalid_votes(
                    epoch_id, [sybil_vote], registered_set, set(directive.members)
                )

        # 9. Byzantine Quorum Verification
        is_quorum_achieved = len(valid_signatures) >= directive.quorum_threshold

        # 10. Submit Block & Quorum Verification on EVM
        if is_quorum_achieved and self.use_blockchain and self.blockchain and self.blockchain.is_connected():
            try:
                commit_tx = self.blockchain.commit_block(
                    epoch_id=epoch_id,
                    block_number=block_num,
                    state_root=state_root,
                    telemetry_hash=telemetry_hash,
                    signatures=valid_signatures
                )
            except Exception:
                commit_tx = None

        # 11. Physical Energy Discharge across fleet
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
            "signatures_collected": len(valid_signatures),
            "quorum_achieved": is_quorum_achieved,
            "leader_id": leader_node.node_id if leader_node else "Unknown",
            "leader_address": directive.leader_address,
            "utility_score": directive.metadata.get("utility", 0.0),
            "avg_committee_battery": directive.metadata.get("avg_battery_pct", 0.0),
            "schedule_gas": schedule_tx["gas_used"] if schedule_tx else 0,
            "commit_gas": commit_tx["gas_used"] if commit_tx else 0,
            "on_chain_success": (commit_tx["status"] == 1 if commit_tx else is_quorum_achieved),
            "alive_nodes_count": sum(1 for n in self.simulator.nodes.values() if n.is_alive),
            "active_alerts_count": len(self.defense.alerts_log),
            "slashed_nodes_count": len(self.defense.slashed_addresses)
        }
        self.history.append(round_summary)
        return round_summary
