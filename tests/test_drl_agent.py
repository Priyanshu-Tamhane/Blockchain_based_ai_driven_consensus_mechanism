"""
Unit test suite verifying Phase 4 Deep Reinforcement Learning components:
IoTConsensusEnv MDP dynamics, ActorCriticNetwork forward pass, and DRLCommitteeSelector inference.
"""
import os
import sys

# Configure clean local cache directories
_local_cache = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cache", "tmp"))
os.makedirs(_local_cache, exist_ok=True)
os.environ["TORCHINDUCTOR_CACHE_DIR"] = _local_cache
os.environ["TORCH_EXTENSIONS_DIR"] = _local_cache
os.environ["TEMP"] = _local_cache
os.environ["TMP"] = _local_cache

import pytest
import numpy as np
import torch
import math
from ai_engine.consensus_env import IoTConsensusEnv
from ai_engine.drl_agent import ActorCriticNetwork, PPOAgent, DRLCommitteeSelector
from simulator.models import TelemetryPacket


class TestConsensusMDPEnvironment:
    """Verifies Gymnasium-compatible IoT Consensus environment."""

    def test_env_dimensions(self):
        env = IoTConsensusEnv(node_count=14)
        obs = env.reset(seed=123)
        assert obs.shape == (58,)  # 14 * 4 + 2
        assert env.action_dim == 15  # 1 sizing + 14 priority

    def test_step_execution_and_rewards(self):
        env = IoTConsensusEnv(node_count=14)
        obs = env.reset(seed=42)
        
        # Test random continuous action
        action = np.random.randn(env.action_dim).astype(np.float32)
        next_obs, reward, terminated, truncated, info = env.step(action)

        assert next_obs.shape == (58,)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert "committee_size" in info
        assert info["committee_size"] >= 4  # Byzantine invariant K >= 3f + 1
        assert info["quorum"] == math.floor((2.0 / 3.0) * info["committee_size"]) + 1

    def test_bft_invariant_failure_penalty(self):
        env = IoTConsensusEnv(node_count=14)
        env.reset(seed=42)
        
        # Manually drain all nodes to 10%
        for node in env.simulator.nodes.values():
            node.force_drain_battery(10.0)

        action = np.zeros(env.action_dim, dtype=np.float32)
        next_obs, reward, terminated, truncated, info = env.step(action)

        assert terminated is True
        assert reward < -20.0  # Heavy failure penalty


class TestDRLPolicyNetwork:
    """Verifies neural network shapes and forward passes."""

    def test_actor_critic_forward_shape(self):
        net = ActorCriticNetwork(obs_dim=58, node_count=14)
        dummy_obs = torch.randn(4, 58)  # Batch size 4
        action_mean, action_std, value = net(dummy_obs)

        assert action_mean.shape == (4, 15)
        assert action_std.shape == (4, 15)
        assert value.shape == (4, 1)

    def test_agent_save_and_load(self, tmp_path):
        agent = PPOAgent(obs_dim=58, node_count=14)
        save_file = str(tmp_path / "test_model.pt")
        agent.save(save_file)

        agent2 = PPOAgent(obs_dim=58, node_count=14)
        agent2.load(save_file)

        dummy_obs = np.random.randn(58).astype(np.float32)
        act1, _, _ = agent.select_action(dummy_obs, deterministic=True)
        act2, _, _ = agent2.select_action(dummy_obs, deterministic=True)

        assert np.allclose(act1, act2)


class TestDRLCommitteeSelectorInference:
    """Verifies that the DRLCommitteeSelector adapter outputs valid directives."""

    def test_drl_selector_output_directive(self):
        selector = DRLCommitteeSelector(model_path=None, node_count=10)
        
        fleet = []
        for i in range(10):
            fleet.append(
                TelemetryPacket(
                    node_id=f"Node_{i}",
                    address=f"0x{i:040x}",
                    battery_percentage=90.0 if i != 3 else 10.0, # Node 3 is depleted (<15%)
                    reputation_score=0.95,
                    latency_ms=25.0
                )
            )

        directive = selector.select_committee(epoch_id=1, telemetry=fleet)

        assert directive.committee_size >= 4
        assert directive.leader_address in directive.members
        assert directive.quorum_threshold == math.floor((2.0 / 3.0) * directive.committee_size) + 1
        
        # Verify depleted Node 3 was never selected
        depleted_addr = f"0x{3:040x}"
        assert depleted_addr not in directive.members
