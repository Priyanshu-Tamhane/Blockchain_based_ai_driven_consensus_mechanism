"""
Gymnasium-compatible reinforcement learning environment for AI-Driven Adaptive IoT Consensus.
Formulates the IoT Fleet committee selection as a Markov Decision Process (MDP).
"""
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
import math
from simulator.fleet_simulator import IoTFleetSimulator
from simulator.energy_model import HardwarePreset, HeinzelmanEnergyModel
from simulator.models import TelemetryPacket, CommitteeDirective
from ai_engine.objective import SystemConstraints


class IoTConsensusEnv:
    """
    Custom MDP Environment for Reinforcement Learning in IoT Blockchain Consensus.
    
    State Space:
      Matrix of shape (N, 4) flattened to (4*N + 2,):
      - For each node: [Battery%, Latency, Reputation, ParticipationRatio]
      - Network-level: [ViableNodeRatio, EpochProgress]
      
    Action Space:
      Continuous vector of size N + 1:
      - action[0]: Continuous sizing for K_t in range [min_k, max_k]
      - action[1..N]: Priority bidding logits for each node
      
    Reward:
      Balanced multi-objective reward function encouraging longevity,
      load balancing (low battery variance), and fast block finalization.
    """

    def __init__(
        self,
        node_count: int = 14,
        max_epochs: int = 100,
        drain_multiplier: float = 1500.0,
        hardware: HardwarePreset = HardwarePreset.ESP32,
        seed: Optional[int] = 42
    ):
        self.node_count = node_count
        self.max_epochs = max_epochs
        self.drain_multiplier = drain_multiplier
        self.hardware = hardware
        self.seed = seed
        self.constraints = SystemConstraints(
            min_battery_threshold=15.0,
            min_reputation_floor=0.60,
            byzantine_tolerance_f=1
        )
        self.min_k = 3 * self.constraints.byzantine_tolerance_f + 1  # 4 for f=1
        self.max_k = min(self.node_count, 8)
        self.energy_model = HeinzelmanEnergyModel(hardware=hardware)

        # Dimension specifications
        self.obs_dim = (self.node_count * 4) + 2
        self.action_dim = self.node_count + 1

        self.simulator: Optional[IoTFleetSimulator] = None
        self.current_epoch = 0
        self.total_rounds_validated: Dict[str, int] = {}
        self.initial_batteries: Dict[str, float] = {}

    def reset(self, seed: Optional[int] = None) -> np.ndarray:
        """Resets the fleet and environment to initial state."""
        env_seed = seed if seed is not None else self.seed
        self.simulator = IoTFleetSimulator(
            node_count=self.node_count,
            default_hardware=self.hardware,
            seed=env_seed
        )
        self.current_epoch = 0
        self.total_rounds_validated = {node.address: 0 for node in self.simulator.nodes.values()}
        self.initial_batteries = {node.address: node.battery_pct for node in self.simulator.nodes.values()}
        return self._get_observation()

    def _get_observation(self) -> np.ndarray:
        """Constructs normalized state vector for the RL agent."""
        telemetry = self.simulator.gather_telemetry()
        obs = []

        viable_count = 0
        for t in telemetry:
            norm_batt = max(0.0, min(1.0, t.battery_percentage / 100.0))
            norm_lat = max(0.0, min(1.0, t.latency_ms / 200.0))
            norm_rep = max(0.0, min(1.0, t.reputation_score))
            
            rounds_led = self.total_rounds_validated.get(t.address, 0)
            norm_part = max(0.0, min(1.0, rounds_led / max(1, self.current_epoch)))

            obs.extend([norm_batt, norm_lat, norm_rep, norm_part])

            if t.is_alive and t.battery_percentage > self.constraints.min_battery_threshold and t.reputation_score >= self.constraints.min_reputation_floor:
                viable_count += 1

        # Network-level context
        obs.append(viable_count / float(self.node_count))
        obs.append(min(1.0, self.current_epoch / float(self.max_epochs)))

        return np.array(obs, dtype=np.float32)

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Executes one consensus epoch using the RL agent's action.
        
        action[0]: Committee sizing logit (mapped to [min_k, max_k])
        action[1:]: Priority scoring logits for each node
        """
        self.current_epoch += 1
        telemetry = self.simulator.gather_telemetry()

        # 1. Feasibility Filtering (Hard BFT & Battery Gates)
        feasible_nodes: List[TelemetryPacket] = []
        feasible_indices: List[int] = []
        for idx, t in enumerate(telemetry):
            if (t.is_alive and 
                t.battery_percentage > self.constraints.min_battery_threshold and 
                t.reputation_score >= self.constraints.min_reputation_floor):
                feasible_nodes.append(t)
                feasible_indices.append(idx)

        # Failure Condition: Insufficient viable nodes to maintain BFT
        if len(feasible_nodes) < self.min_k:
            dead_penalty = -50.0
            next_obs = self._get_observation()
            return next_obs, dead_penalty, True, False, {
                "reason": "Byzantine Invariant Violated: Less than 3f+1 viable nodes remaining",
                "epoch": self.current_epoch,
                "first_node_dead": True
            }

        # 2. Decode Committee Size K_t from action[0]
        # Map sigmoid/tanh of action[0] to integer in [min_k, min(len(feasible_nodes), max_k)]
        raw_size = float(action[0])
        norm_size = 1.0 / (1.0 + math.exp(-raw_size))  # Sigmoid [0, 1]
        allowed_max_k = min(len(feasible_nodes), self.max_k)
        target_k = int(round(self.min_k + norm_size * (allowed_max_k - self.min_k)))
        target_k = max(self.min_k, min(allowed_max_k, target_k))

        # 3. Rank Feasible Nodes by Agent's Priority Logits
        node_scores = []
        for f_idx, node in zip(feasible_indices, feasible_nodes):
            agent_priority = float(action[1 + f_idx])
            node_scores.append((node, agent_priority))

        # Sort descending by priority logits
        node_scores.sort(key=lambda x: x[1], reverse=True)
        selected_nodes = [n for n, score in node_scores[:target_k]]
        leader = selected_nodes[0]

        # Update participation counts
        self.total_rounds_validated[leader.address] = self.total_rounds_validated.get(leader.address, 0) + 1

        # 4. Form Directive and Apply Physical Discharge
        quorum = math.floor((2.0 / 3.0) * target_k) + 1
        directive = CommitteeDirective(
            epoch_id=self.current_epoch,
            committee_size=target_k,
            members=[n.address for n in selected_nodes],
            leader_address=leader.address,
            quorum_threshold=quorum
        )
        self.simulator.apply_committee_directive(directive)
        self.simulator.discharge_fleet_round(
            committee_size=target_k,
            drain_multiplier=self.drain_multiplier
        )

        # 5. Reward Calculation
        # Components:
        # + Success reward (+2.0)
        # - Latency penalty
        # - Battery Variance penalty (encourages fleet balance and prevents early node death)
        # - Dead node penalty
        # + Avg committee battery bonus
        all_batteries = [node.battery_pct for node in self.simulator.nodes.values() if node.is_alive]
        dead_nodes_count = sum(1 for node in self.simulator.nodes.values() if not node.is_alive)
        
        battery_variance = float(np.var(all_batteries)) if all_batteries else 100.0
        avg_committee_lat = sum(n.latency_ms for n in selected_nodes) / float(target_k)
        avg_committee_bat = sum(n.battery_percentage for n in selected_nodes) / float(target_k)

        r_success = 2.0
        r_latency = -0.5 * (avg_committee_lat / 100.0)
        r_variance = -0.02 * battery_variance  # Penalizes uneven discharge
        r_dead = -20.0 * dead_nodes_count
        r_battery_bonus = 1.0 * (avg_committee_bat / 100.0)

        step_reward = r_success + r_latency + r_variance + r_dead + r_battery_bonus

        terminated = self.current_epoch >= self.max_epochs or dead_nodes_count > 0
        truncated = False

        info = {
            "epoch": self.current_epoch,
            "committee_size": target_k,
            "quorum": quorum,
            "leader_id": leader.node_id,
            "avg_latency": avg_committee_lat,
            "battery_variance": battery_variance,
            "dead_nodes": dead_nodes_count,
            "alive_nodes": len(all_batteries)
        }

        next_obs = self._get_observation()
        return next_obs, step_reward, terminated, truncated, info
