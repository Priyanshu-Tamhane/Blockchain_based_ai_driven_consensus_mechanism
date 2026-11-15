"""
Empirical Benchmarking Engine.
Compares:
  1. Classical Static PBFT Baseline (All N nodes validate every round, O(N^2) messages)
  2. Fixed Stake-Based PoS Baseline (Fixed validator subset, no energy awareness)
  3. AI-Driven Adaptive Consensus (Dynamic K_t >= 3f + 1, Health-aware rotation, deep sleep)
"""
import math
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from simulator.fleet_simulator import IoTFleetSimulator
from simulator.energy_model import HeinzelmanEnergyModel, HardwarePreset
from ai_engine.objective import MultiObjectiveOptimizer, ObjectiveWeights, SystemConstraints
# NOTE: ai_engine.drl_agent (and therefore torch) is imported lazily inside
# _run_adaptive so that running the MCDM benchmark never pays the multi-second
# torch import cost.


@dataclass
class ProtocolBenchmarkStats:
    """Stores round-by-round and summary benchmark metrics for a single consensus protocol."""
    protocol_name: str
    rounds_executed: int = 0
    # Requested simulation horizon. Recorded so downstream consumers (charts,
    # JSON export, the Word report) can render "None (>N)" markers without
    # re-guessing the bound from however many rounds actually completed.
    horizon_rounds: int = 0
    first_node_dead_round: Optional[int] = None
    network_half_life_round: Optional[int] = None
    network_partition_round: Optional[int] = None
    total_energy_dissipated_joules: float = 0.0
    total_messages_exchanged: int = 0
    final_alive_nodes: int = 0
    
    # Time series trajectories
    alive_nodes_history: List[int] = field(default_factory=list)
    # Active committee size K_t per round. Needed to report committee-size
    # distributions and to justify message-count comparisons analytically.
    committee_size_history: List[int] = field(default_factory=list)
    cumulative_energy_history: List[float] = field(default_factory=list)
    cumulative_messages_history: List[int] = field(default_factory=list)
    mean_battery_history: List[float] = field(default_factory=list)
    std_battery_history: List[float] = field(default_factory=list)
    node_battery_trajectories: Dict[str, List[float]] = field(default_factory=dict)


class ConsensusBenchmarkRunner:
    """Runs parallel comparative benchmark simulations under identical network conditions."""

    def __init__(
        self,
        node_count: int = 14,
        hardware: HardwarePreset = HardwarePreset.ESP32,
        byzantine_f: int = 1,
        drain_multiplier: float = 40000.0,  # Accelerates discharge so depletion curves emerge in 60-150 rounds
        seed: int = 42
    ):
        self.node_count = node_count
        self.hardware = hardware
        self.byzantine_f = byzantine_f
        self.drain_multiplier = drain_multiplier
        self.min_k = 3 * byzantine_f + 1
        self.seed = seed
        self.energy_model = HeinzelmanEnergyModel(hardware=hardware)

    def _init_fleet(self) -> IoTFleetSimulator:
        return IoTFleetSimulator(
            node_count=self.node_count,
            default_hardware=self.hardware,
            seed=self.seed
        )

    def run_benchmark(
        self,
        max_rounds: int = 150,
        drl_model_path: Optional[str] = None
    ) -> Dict[str, ProtocolBenchmarkStats]:
        """
        Executes simulated consensus across all three paradigms:
          1. Static PBFT
          2. Fixed PoS (Fixed Validator Committee)
          3. AI Adaptive Consensus (MCDM / DRL)
        """
        results = {
            "Static PBFT": self._run_static_pbft(max_rounds),
            "Static PoS (Fixed Stake)": self._run_static_pos(max_rounds),
            "AI Adaptive Consensus": self._run_adaptive(max_rounds, drl_model_path=drl_model_path)
        }
        # Stamp the requested horizon onto every arm so "no death" markers can be
        # rendered unambiguously downstream.
        for stats in results.values():
            stats.horizon_rounds = max_rounds
        return results

    def _run_static_pbft(self, max_rounds: int) -> ProtocolBenchmarkStats:
        """
        Static PBFT Baseline: All N nodes participate as validators in every single round.
        Broadcast complexity: O(N^2) messages per round.
        """
        fleet = self._init_fleet()
        stats = ProtocolBenchmarkStats(protocol_name="Static PBFT")
        for node_id in fleet.nodes.keys():
            stats.node_battery_trajectories[node_id] = []

        cum_energy = 0.0
        cum_messages = 0

        for r in range(1, max_rounds + 1):
            alive_count = sum(1 for n in fleet.nodes.values() if n.is_alive)
            stats.alive_nodes_history.append(alive_count)
            # In PBFT every live node validates, so the active set equals the fleet.
            stats.committee_size_history.append(alive_count)

            # Record metrics
            if alive_count < self.node_count and stats.first_node_dead_round is None:
                stats.first_node_dead_round = r
            if alive_count <= self.node_count // 2 and stats.network_half_life_round is None:
                stats.network_half_life_round = r
            if alive_count < self.min_k and stats.network_partition_round is None:
                stats.network_partition_round = r
                break  # Byzantine quorum impossible

            # In PBFT: Leader sends to (N-1) nodes; each node broadcasts to (N-1) nodes
            # Message complexity: (N - 1) + (N - 1)^2 ≈ N^2
            round_messages = (alive_count - 1) + (alive_count - 1) * (alive_count - 1)
            cum_messages += round_messages
            stats.cumulative_messages_history.append(cum_messages)

            # Energy dissipation: 1 Leader + (alive_count - 1) Validators
            round_energy = 0.0
            nodes_list = [n for n in fleet.nodes.values() if n.is_alive]
            # Round-robin primary rotation. A real PBFT deployment rotates the
            # primary on every view change; pinning the primary to index 0 for
            # the whole run would guarantee that a single node absorbs every
            # leader cost, which materially skews the First-Node-Dead result.
            leader_node = nodes_list[(r - 1) % len(nodes_list)] if nodes_list else None

            for node in fleet.nodes.values():
                if not node.is_alive:
                    stats.node_battery_trajectories[node.node_id].append(0.0)
                    continue

                is_lead = (node == leader_node)
                node.set_consensus_role(is_validator=True, is_leader=is_lead)
                e_discharged = node.discharge_round_energy(
                    committee_size=alive_count,
                    drain_multiplier=self.drain_multiplier
                )
                round_energy += e_discharged
                stats.node_battery_trajectories[node.node_id].append(node.battery_pct)

            cum_energy += round_energy
            stats.cumulative_energy_history.append(cum_energy)

            batt_vals = [n.battery_pct for n in fleet.nodes.values() if n.is_alive]
            stats.mean_battery_history.append(sum(batt_vals) / len(batt_vals) if batt_vals else 0.0)
            variance = sum((b - stats.mean_battery_history[-1]) ** 2 for b in batt_vals) / len(batt_vals) if batt_vals else 0.0
            stats.std_battery_history.append(math.sqrt(variance))
            stats.rounds_executed = r

        stats.total_energy_dissipated_joules = cum_energy
        stats.total_messages_exchanged = cum_messages
        stats.final_alive_nodes = sum(1 for n in fleet.nodes.values() if n.is_alive)
        return stats

    def _run_static_pos(self, max_rounds: int) -> ProtocolBenchmarkStats:
        """
        Static PoS Baseline: A fixed subset of nodes (e.g. 5 nodes) are permanently elected
        as validators based on static capital/stake. The remaining nodes remain idle.
        Validators rapidly burn out while idle nodes sit with near 100% battery.
        """
        fleet = self._init_fleet()
        stats = ProtocolBenchmarkStats(protocol_name="Static PoS (Fixed Stake)")
        for node_id in fleet.nodes.keys():
            stats.node_battery_trajectories[node_id] = []

        # Static stake-based election: the 5 highest-reputation devices (the
        # closest available proxy for highest stake) are permanently elected.
        # Selecting by *position* instead -- `list(...)[:5]` -- would correlate
        # the committee with fleet ordering rather than stake, which is not what
        # a stake-based protocol does and biases the comparison.
        validator_count = min(5, self.node_count)
        fixed_validators = sorted(
            fleet.nodes.keys(),
            key=lambda nid: -fleet.nodes[nid].reputation
        )[:validator_count]
        cum_energy = 0.0
        cum_messages = 0

        for r in range(1, max_rounds + 1):
            alive_count = sum(1 for n in fleet.nodes.values() if n.is_alive)
            active_validators_alive = sum(1 for v_id in fixed_validators if fleet.nodes[v_id].is_alive)
            stats.alive_nodes_history.append(alive_count)
            # Active set is the still-alive fixed validator committee.
            stats.committee_size_history.append(active_validators_alive)

            if alive_count < self.node_count and stats.first_node_dead_round is None:
                stats.first_node_dead_round = r
            if alive_count <= self.node_count // 2 and stats.network_half_life_round is None:
                stats.network_half_life_round = r
            if active_validators_alive < self.min_k and stats.network_partition_round is None:
                stats.network_partition_round = r
                break  # Fixed validator committee exhausted

            # Messages: Leader transmits to K-1, validators reply
            round_messages = max(0, active_validators_alive - 1) * 2
            cum_messages += round_messages
            stats.cumulative_messages_history.append(cum_messages)

            # Rotate the proposer slot across the (alive) fixed validator set,
            # mirroring how stake-based protocols rotate block proposers. A
            # permanently pinned leader would burn out the same device every
            # round and confound "energy-blind selection" with "no rotation".
            alive_validators = [v for v in fixed_validators if fleet.nodes[v].is_alive]
            current_proposer = (
                alive_validators[(r - 1) % len(alive_validators)] if alive_validators else None
            )

            round_energy = 0.0
            for node_id, node in fleet.nodes.items():
                if not node.is_alive:
                    stats.node_battery_trajectories[node_id].append(0.0)
                    continue

                if node_id in fixed_validators:
                    is_lead = (node_id == current_proposer)
                    node.set_consensus_role(is_validator=True, is_leader=is_lead)
                    e_discharged = node.discharge_round_energy(
                        committee_size=len(fixed_validators),
                        drain_multiplier=self.drain_multiplier
                    )
                else:
                    # Non-validator rests in deep sleep
                    node.set_consensus_role(is_validator=False, is_leader=False)
                    e_discharged = node.discharge_round_energy(
                        committee_size=len(fixed_validators),
                        drain_multiplier=self.drain_multiplier
                    )

                round_energy += e_discharged
                stats.node_battery_trajectories[node_id].append(node.battery_pct)

            cum_energy += round_energy
            stats.cumulative_energy_history.append(cum_energy)

            batt_vals = [n.battery_pct for n in fleet.nodes.values() if n.is_alive]
            stats.mean_battery_history.append(sum(batt_vals) / len(batt_vals) if batt_vals else 0.0)
            variance = sum((b - stats.mean_battery_history[-1]) ** 2 for b in batt_vals) / len(batt_vals) if batt_vals else 0.0
            stats.std_battery_history.append(math.sqrt(variance))
            stats.rounds_executed = r

        stats.total_energy_dissipated_joules = cum_energy
        stats.total_messages_exchanged = cum_messages
        stats.final_alive_nodes = sum(1 for n in fleet.nodes.values() if n.is_alive)
        return stats

    def _run_adaptive(
        self,
        max_rounds: int,
        drl_model_path: Optional[str] = None
    ) -> ProtocolBenchmarkStats:
        """
        Proposed AI Adaptive Consensus:
        - Dynamic committee sizing: K_t >= 3f + 1
        - Health-aware rotation and leadership fatigue penalty
        - Unselected nodes conserve battery in deep sleep (15 uA)
        """
        fleet = self._init_fleet()
        stats = ProtocolBenchmarkStats(protocol_name="AI Adaptive Consensus")
        for node_id in fleet.nodes.keys():
            stats.node_battery_trajectories[node_id] = []

        # Initialize selector (DRL if available, else MCDM optimizer)
        if drl_model_path:
            from ai_engine.drl_agent import DRLCommitteeSelector
            selector = DRLCommitteeSelector(model_path=drl_model_path, node_count=self.node_count)
        else:
            selector = MultiObjectiveOptimizer(
                weights=ObjectiveWeights(w_security=0.35, w_energy=0.45, w_latency=0.20),
                constraints=SystemConstraints(
                    min_battery_threshold=15.0,
                    min_reputation_floor=0.60,
                    byzantine_tolerance_f=self.byzantine_f
                )
            )

        cum_energy = 0.0
        cum_messages = 0

        for r in range(1, max_rounds + 1):
            alive_count = sum(1 for n in fleet.nodes.values() if n.is_alive)
            stats.alive_nodes_history.append(alive_count)

            if alive_count < self.node_count and stats.first_node_dead_round is None:
                stats.first_node_dead_round = r
            if alive_count <= self.node_count // 2 and stats.network_half_life_round is None:
                stats.network_half_life_round = r

            # Gather telemetry
            telemetry = fleet.gather_telemetry()
            try:
                directive = selector.select_committee(epoch_id=r, telemetry=telemetry)
                fleet.apply_committee_directive(directive)
            except ValueError:
                # Viable nodes fell below 3f + 1
                if stats.network_partition_round is None:
                    stats.network_partition_round = r
                break

            # Messages: Leader transmits to K_t - 1, validators transmit votes back
            k = directive.committee_size
            stats.committee_size_history.append(k)
            round_messages = (k - 1) * 2
            cum_messages += round_messages
            stats.cumulative_messages_history.append(cum_messages)

            round_energy = 0.0
            for node_id, node in fleet.nodes.items():
                if not node.is_alive:
                    stats.node_battery_trajectories[node_id].append(0.0)
                    continue

                e_discharged = node.discharge_round_energy(
                    committee_size=k,
                    drain_multiplier=self.drain_multiplier
                )
                round_energy += e_discharged
                stats.node_battery_trajectories[node_id].append(node.battery_pct)

            cum_energy += round_energy
            stats.cumulative_energy_history.append(cum_energy)

            batt_vals = [n.battery_pct for n in fleet.nodes.values() if n.is_alive]
            stats.mean_battery_history.append(sum(batt_vals) / len(batt_vals) if batt_vals else 0.0)
            variance = sum((b - stats.mean_battery_history[-1]) ** 2 for b in batt_vals) / len(batt_vals) if batt_vals else 0.0
            stats.std_battery_history.append(math.sqrt(variance))
            stats.rounds_executed = r

        stats.total_energy_dissipated_joules = cum_energy
        stats.total_messages_exchanged = cum_messages
        stats.final_alive_nodes = sum(1 for n in fleet.nodes.values() if n.is_alive)
        return stats
