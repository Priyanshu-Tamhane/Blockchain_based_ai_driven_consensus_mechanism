"""
Mathematical optimization and constraint formulations for Adaptive IoT Consensus.
Implements the multi-factor utility function U_t and BFT safety checks.
"""
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import math
from simulator.models import TelemetryPacket, CommitteeDirective


@dataclass
class ObjectiveWeights:
    """Balancing weights for the global utility function U_t (w1 + w2 + w3 = 1.0)."""
    w_security: float = 0.35      # w1: Weight for committee reputation/security
    w_energy: float = 0.45        # w2: Weight for average residual battery
    w_latency: float = 0.20       # w3: Weight for network propagation latency

    def __post_init__(self):
        total = self.w_security + self.w_energy + self.w_latency
        if not math.isclose(total, 1.0, rel_tol=1e-3):
            # Normalize automatically if not strictly 1.0
            self.w_security /= total
            self.w_energy /= total
            self.w_latency /= total


@dataclass
class SystemConstraints:
    """Operational and BFT feasibility bounds."""
    min_battery_threshold: float = 15.0      # E_threshold (%): nodes below this are excluded
    min_reputation_floor: float = 0.60       # R_min [0.0, 1.0]
    byzantine_tolerance_f: int = 1           # Maximum tolerated Byzantine nodes (f)
    min_committee_size: int = 4              # 3f + 1 when f = 1
    max_committee_size: int = 10             # Scaled down to prevent broadcast storms
    max_latency_ms: float = 200.0            # Latency cap for normalization


class MultiObjectiveOptimizer:
    """
    Evaluates node telemetry vectors and selects the optimal consensus committee
    by maximizing utility function U_t subject to BFT and battery constraints.
    """

    def __init__(
        self,
        weights: Optional[ObjectiveWeights] = None,
        constraints: Optional[SystemConstraints] = None
    ):
        self.weights = weights or ObjectiveWeights()
        self.constraints = constraints or SystemConstraints()
        # Tracks which epoch a node last served as leader (for fair rotation & fatigue penalty)
        self.leadership_history: Dict[str, int] = {}

    def filter_feasible_nodes(self, telemetry: List[TelemetryPacket]) -> List[TelemetryPacket]:
        """
        Applies hard feasibility constraints:
          1. Node must be alive (is_alive == True)
          2. Residual battery > E_threshold (e.g., > 15%)
          3. Reputation score >= R_min (e.g., >= 0.60)
        """
        feasible = []
        for t in telemetry:
            if not t.is_alive:
                continue
            if t.battery_percentage <= self.constraints.min_battery_threshold:
                continue
            if t.reputation_score < self.constraints.min_reputation_floor:
                continue
            feasible.append(t)
        return feasible

    def score_individual_node(self, node: TelemetryPacket, current_epoch: int = 1) -> float:
        """
        Calculates individual node utility based on normalized metrics and leadership fatigue:
          score = w1 * reputation + w2 * (battery / 100) - w3 * (latency / max_latency) - fatigue
        """
        norm_rep = max(0.0, min(1.0, node.reputation_score))
        norm_bat = max(0.0, min(1.0, node.battery_percentage / 100.0))
        norm_lat = max(0.0, min(1.0, node.latency_ms / self.constraints.max_latency_ms))

        # Leadership Workload & Fatigue Penalty
        # Prevents a single high-battery node from monopolizing leadership every single round.
        fatigue = 0.0
        if node.address in self.leadership_history:
            epochs_since_lead = current_epoch - self.leadership_history[node.address]
            if epochs_since_lead <= 2:
                fatigue = 0.20 / max(1, epochs_since_lead)

        score = (
            self.weights.w_security * norm_rep +
            self.weights.w_energy * norm_bat -
            self.weights.w_latency * norm_lat -
            fatigue
        )
        return score

    def compute_committee_utility(self, committee: List[TelemetryPacket]) -> float:
        """
        Evaluates global committee utility U_t:
          U_t = w1 * avg(S) + w2 * avg(E_rem) - w3 * avg(Latency)
        """
        if not committee:
            return -1.0

        avg_rep = sum(n.reputation_score for n in committee) / len(committee)
        avg_bat = sum(n.battery_percentage / 100.0 for n in committee) / len(committee)
        avg_lat = sum(n.latency_ms / self.constraints.max_latency_ms for n in committee) / len(committee)

        utility = (
            self.weights.w_security * avg_rep +
            self.weights.w_energy * avg_bat -
            self.weights.w_latency * avg_lat
        )
        return utility

    def determine_optimal_committee_size(self, feasible_count: int) -> int:
        """
        Dynamically calculates optimal committee size K_t:
          - Must satisfy K_t >= 3f + 1 (BFT Invariant)
          - Scales with available viable nodes up to max_committee_size
        """
        f = self.constraints.byzantine_tolerance_f
        min_k = 3 * f + 1
        
        if feasible_count < min_k:
            raise ValueError(
                f"Insufficient viable nodes ({feasible_count}) to satisfy Byzantine invariant 3f + 1 ({min_k})."
            )

        # Dynamic scaling: Use minimum viable quorum for maximum energy conservation,
        # but expand up to max_committee_size if ample nodes exist.
        target_k = min(feasible_count, max(min_k, min_k + (feasible_count // 5)))
        return min(target_k, self.constraints.max_committee_size)

    def select_committee(
        self,
        epoch_id: int,
        telemetry: List[TelemetryPacket]
    ) -> CommitteeDirective:
        """
        Executes the full election pipeline:
          1. Filters feasible nodes (battery > 15%, trust >= 0.6)
          2. Ranks feasible candidates by multi-criteria utility score
          3. Chooses optimal committee size K_t >= 3f + 1
          4. Selects top K_t nodes and designates highest-scoring node as round leader
          5. Computes quorum threshold = floor(2/3 * K_t) + 1
        """
        feasible = self.filter_feasible_nodes(telemetry)
        k_size = self.determine_optimal_committee_size(len(feasible))

        # Rank candidates by utility score descending (accounting for fatigue)
        scored_candidates = [
            (node, self.score_individual_node(node, current_epoch=epoch_id))
            for node in feasible
        ]
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        selected_nodes = [node for node, score in scored_candidates[:k_size]]
        leader = selected_nodes[0]
        
        # Record leadership history for future rotation
        self.leadership_history[leader.address] = epoch_id
        
        quorum = math.floor((2.0 / 3.0) * k_size) + 1
        avg_utility = self.compute_committee_utility(selected_nodes)
        avg_battery = sum(n.battery_percentage for n in selected_nodes) / len(selected_nodes)

        return CommitteeDirective(
            epoch_id=epoch_id,
            committee_size=k_size,
            members=[n.address for n in selected_nodes],
            leader_address=leader.address,
            quorum_threshold=quorum,
            metadata={
                "utility": avg_utility,
                "avg_battery_pct": avg_battery,
                "leader_id": leader.node_id,
                "viable_pool_count": float(len(feasible))
            }
        )
