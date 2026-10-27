"""
Deep Reinforcement Learning (Actor-Critic / PPO) Agent for Adaptive IoT Consensus.
Replaces static heuristic MCDM with a neural network policy trained to maximize fleet survival.
"""
import os
import sys
import math

# Configure clean local cache directories to prevent Windows permission issues
_local_cache = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cache", "tmp"))
os.makedirs(_local_cache, exist_ok=True)
os.environ["TORCHINDUCTOR_CACHE_DIR"] = _local_cache
os.environ["TORCH_EXTENSIONS_DIR"] = _local_cache
os.environ["TEMP"] = _local_cache
os.environ["TMP"] = _local_cache

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal
from typing import Dict, List, Tuple, Optional, Any

from simulator.models import TelemetryPacket, CommitteeDirective
from ai_engine.objective import SystemConstraints


class ActorCriticNetwork(nn.Module):
    """
    Two-headed Actor-Critic Deep Neural Network.
    Actor: Outputs committee size logit and per-node priority logits.
    Critic: Estimates expected cumulative future return V(s).
    """

    def __init__(self, obs_dim: int, node_count: int, hidden_dim: int = 128):
        super(ActorCriticNetwork, self).__init__()
        self.obs_dim = obs_dim
        self.node_count = node_count
        self.action_dim = node_count + 1

        # Shared representation for actor
        self.actor_shared = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        # Sizing head: outputs scalar logit for committee size K_t
        self.actor_size_head = nn.Linear(hidden_dim, 1)
        # Node ranking head: outputs logits for each node in the fleet
        self.actor_priority_head = nn.Linear(hidden_dim, node_count)

        # Log standard deviation parameter for continuous action Gaussian distribution
        self.log_std = nn.Parameter(torch.ones(self.action_dim) * -0.5)

        # Value Network (Critic)
        self.critic = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        feat = self.actor_shared(x)
        size_logit = self.actor_size_head(feat)
        node_logits = self.actor_priority_head(feat)
        action_mean = torch.cat([size_logit, node_logits], dim=-1)
        action_std = torch.exp(self.log_std).expand_as(action_mean)

        value = self.critic(x)
        return action_mean, action_std, value

    def get_value(self, x: torch.Tensor) -> torch.Tensor:
        return self.critic(x)


class RolloutBuffer:
    """Stores trajectory rollouts for PPO optimization."""

    def __init__(self):
        self.observations: List[np.ndarray] = []
        self.actions: List[np.ndarray] = []
        self.log_probs: List[float] = []
        self.rewards: List[float] = []
        self.dones: List[bool] = []
        self.values: List[float] = []

    def clear(self):
        self.observations.clear()
        self.actions.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.dones.clear()
        self.values.clear()

    def add(self, obs, action, log_prob, reward, done, value):
        self.observations.append(obs)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.rewards.append(reward)
        self.dones.append(done)
        self.values.append(value)


class PPOAgent:
    """Proximal Policy Optimization (PPO) reinforcement learning agent."""

    def __init__(
        self,
        obs_dim: int,
        node_count: int,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01
    ):
        self.obs_dim = obs_dim
        self.node_count = node_count
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef

        self.device = torch.device("cpu")
        self.network = ActorCriticNetwork(obs_dim, node_count).to(self.device)
        self.optimizer = optim.Adam(self.network.parameters(), lr=lr)
        self.buffer = RolloutBuffer()

    def select_action(self, obs: np.ndarray, deterministic: bool = False) -> Tuple[np.ndarray, float, float]:
        """Selects action vector: continuous K_t logit + node priority logits."""
        self.network.eval()
        with torch.no_grad():
            obs_tensor = torch.as_tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
            mean, std, value = self.network(obs_tensor)

            if deterministic:
                action = mean
                log_prob = 0.0
            else:
                dist = Normal(mean, std)
                action = dist.sample()
                log_prob = dist.log_prob(action).sum(dim=-1).item()

        return action.squeeze(0).cpu().numpy(), log_prob, value.squeeze().item()

    def update(self, batch_size: int = 64, epochs: int = 5) -> Dict[str, float]:
        """Updates Actor and Critic parameters using PPO clipped loss."""
        self.network.train()

        obs_arr = np.array(self.buffer.observations)
        actions_arr = np.array(self.buffer.actions)
        old_log_probs_arr = np.array(self.buffer.log_probs)
        rewards_arr = np.array(self.buffer.rewards)
        dones_arr = np.array(self.buffer.dones)
        values_arr = np.array(self.buffer.values)

        # Generalized Advantage Estimation (GAE)
        advantages = np.zeros_like(rewards_arr, dtype=np.float32)
        last_gae = 0.0
        n_steps = len(rewards_arr)

        for t in reversed(range(n_steps)):
            next_val = values_arr[t + 1] if t + 1 < n_steps else 0.0
            next_non_terminal = 1.0 - float(dones_arr[t])
            delta = rewards_arr[t] + self.gamma * next_val * next_non_terminal - values_arr[t]
            advantages[t] = last_gae = delta + self.gamma * self.gae_lambda * next_non_terminal * last_gae

        returns = advantages + values_arr
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # Convert to tensors
        obs_tensor = torch.as_tensor(obs_arr, dtype=torch.float32, device=self.device)
        actions_tensor = torch.as_tensor(actions_arr, dtype=torch.float32, device=self.device)
        old_log_probs_tensor = torch.as_tensor(old_log_probs_arr, dtype=torch.float32, device=self.device)
        returns_tensor = torch.as_tensor(returns, dtype=torch.float32, device=self.device)
        advantages_tensor = torch.as_tensor(advantages, dtype=torch.float32, device=self.device)

        total_policy_loss = 0.0
        total_value_loss = 0.0

        for _ in range(epochs):
            indices = np.arange(n_steps)
            np.random.shuffle(indices)

            for start in range(0, n_steps, batch_size):
                end = start + batch_size
                batch_idx = indices[start:end]

                mean, std, value = self.network(obs_tensor[batch_idx])
                dist = Normal(mean, std)
                new_log_probs = dist.log_prob(actions_tensor[batch_idx]).sum(dim=-1)
                entropy = dist.entropy().sum(dim=-1).mean()

                ratio = torch.exp(new_log_probs - old_log_probs_tensor[batch_idx])
                surr1 = ratio * advantages_tensor[batch_idx]
                surr2 = torch.clamp(ratio, 1.0 - self.clip_epsilon, 1.0 + self.clip_epsilon) * advantages_tensor[batch_idx]
                policy_loss = -torch.min(surr1, surr2).mean()

                value_loss = nn.MSELoss()(value.squeeze(-1), returns_tensor[batch_idx])

                loss = policy_loss + (self.value_coef * value_loss) - (self.entropy_coef * entropy)

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), max_norm=0.5)
                self.optimizer.step()

                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()

        self.buffer.clear()
        return {
            "policy_loss": total_policy_loss / (epochs * max(1, n_steps // batch_size)),
            "value_loss": total_value_loss / (epochs * max(1, n_steps // batch_size))
        }

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        torch.save(self.network.state_dict(), filepath)

    def load(self, filepath: str):
        if os.path.exists(filepath):
            self.network.load_state_dict(torch.load(filepath, map_location=self.device))
            self.network.eval()


class DRLCommitteeSelector:
    """
    Inference adapter: Wraps the trained Deep RL agent to expose the same
    interface as MultiObjectiveOptimizer (`select_committee`), enabling seamless
    drop-in usage in ConsensusOrchestrator and the Streamlit dashboard.
    """

    def __init__(
        self,
        model_path: Optional[str] = "models/drl_consensus_agent.pt",
        node_count: int = 14,
        constraints: Optional[SystemConstraints] = None
    ):
        self.node_count = node_count
        self.obs_dim = (node_count * 4) + 2
        self.constraints = constraints or SystemConstraints()
        self.min_k = 3 * self.constraints.byzantine_tolerance_f + 1
        self.max_k = min(node_count, 8)

        self.agent = PPOAgent(obs_dim=self.obs_dim, node_count=node_count)
        if model_path and os.path.exists(model_path):
            self.agent.load(model_path)
            self.has_weights = True
        else:
            self.has_weights = False

        self.rounds_led_map: Dict[str, int] = {}

    def reset(self):
        """Resets leadership fatigue and tracking history."""
        self.rounds_led_map.clear()

    def _telemetry_to_observation(self, telemetry: List[TelemetryPacket], epoch_id: int) -> np.ndarray:
        obs = []
        viable_count = 0

        for t in telemetry:
            norm_batt = max(0.0, min(1.0, t.battery_percentage / 100.0))
            norm_lat = max(0.0, min(1.0, t.latency_ms / 200.0))
            norm_rep = max(0.0, min(1.0, t.reputation_score))
            rounds_led = self.rounds_led_map.get(t.address, 0)
            norm_part = max(0.0, min(1.0, rounds_led / max(1, epoch_id)))

            obs.extend([norm_batt, norm_lat, norm_rep, norm_part])
            if (t.is_alive and 
                t.battery_percentage > self.constraints.min_battery_threshold and 
                t.reputation_score >= self.constraints.min_reputation_floor):
                viable_count += 1

        obs.append(viable_count / float(max(1, len(telemetry))))
        obs.append(min(1.0, epoch_id / 100.0))
        return np.array(obs, dtype=np.float32)

    def select_committee(self, epoch_id: int, telemetry: List[TelemetryPacket]) -> CommitteeDirective:
        """Evaluates telemetry with the trained Deep RL neural network."""
        # 1. Feasibility Filter
        feasible_nodes = []
        feasible_indices = []
        for idx, t in enumerate(telemetry):
            if (t.is_alive and 
                t.battery_percentage > self.constraints.min_battery_threshold and 
                t.reputation_score >= self.constraints.min_reputation_floor):
                feasible_nodes.append(t)
                feasible_indices.append(idx)

        if len(feasible_nodes) < self.min_k:
            raise ValueError(
                f"Insufficient viable nodes ({len(feasible_nodes)}) to satisfy Byzantine invariant 3f + 1 ({self.min_k})."
            )

        # 2. Forward pass through neural network
        obs = self._telemetry_to_observation(telemetry, epoch_id)
        action, _, _ = self.agent.select_action(obs, deterministic=True)

        # 3. Decode K_t
        raw_size = float(action[0])
        norm_size = 1.0 / (1.0 + math.exp(-raw_size))
        allowed_max_k = min(len(feasible_nodes), self.max_k)
        target_k = int(round(self.min_k + norm_size * (allowed_max_k - self.min_k)))
        target_k = max(self.min_k, min(allowed_max_k, target_k))

        # 4. Rank candidates by agent's output logits
        node_scores = []
        for f_idx, node in zip(feasible_indices, feasible_nodes):
            priority_score = float(action[1 + f_idx])
            node_scores.append((node, priority_score))

        node_scores.sort(key=lambda x: x[1], reverse=True)
        selected_nodes = [node for node, score in node_scores[:target_k]]
        leader = selected_nodes[0]

        self.rounds_led_map[leader.address] = self.rounds_led_map.get(leader.address, 0) + 1
        quorum = math.floor((2.0 / 3.0) * target_k) + 1
        avg_battery = sum(n.battery_percentage for n in selected_nodes) / len(selected_nodes)

        return CommitteeDirective(
            epoch_id=epoch_id,
            committee_size=target_k,
            members=[n.address for n in selected_nodes],
            leader_address=leader.address,
            quorum_threshold=quorum,
            metadata={
                "utility": float(node_scores[0][1]),
                "avg_battery_pct": avg_battery,
                "leader_id": leader.node_id,
                "viable_pool_count": float(len(feasible_nodes)),
                "engine_type": "Deep RL (PPO) Policy Network"
            }
        )
