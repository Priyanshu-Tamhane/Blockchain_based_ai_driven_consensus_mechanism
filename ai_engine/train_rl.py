"""
Training script for the Deep Reinforcement Learning (PPO) consensus agent.
Runs rollout trajectories through IoTConsensusEnv, optimizes Actor-Critic networks,
and exports the trained policy weights to models/drl_consensus_agent.pt.
"""
import os
import sys
import time
import numpy as np

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_engine.consensus_env import IoTConsensusEnv
from ai_engine.drl_agent import PPOAgent


def train_drl_agent(
    total_episodes: int = 60,
    steps_per_episode: int = 50,
    save_path: str = "models/drl_consensus_agent.pt"
):
    print("=" * 80)
    print("      PHASE 4: TRAINING DEEP REINFORCEMENT LEARNING (PPO) CONSENSUS AGENT")
    print("=" * 80)

    env = IoTConsensusEnv(node_count=14, max_epochs=steps_per_episode, drain_multiplier=1200.0)
    agent = PPOAgent(obs_dim=env.obs_dim, node_count=env.node_count, lr=4e-4)

    print(f"[*] Observation Dimension: {env.obs_dim}")
    print(f"[*] Action Dimension:      {env.action_dim} (1 size logit + {env.node_count} node priority logits)")
    print(f"[*] Training Episodes:     {total_episodes}")
    print(f"[*] Target Model Path:     {save_path}\n")

    best_reward = -float("inf")
    start_time = time.time()

    for ep in range(1, total_episodes + 1):
        obs = env.reset(seed=ep * 10)
        ep_reward = 0.0
        ep_steps = 0
        terminal_reason = "Completed all epochs"

        for step in range(steps_per_episode):
            action, log_prob, value = agent.select_action(obs, deterministic=False)
            next_obs, reward, terminated, truncated, info = env.step(action)

            agent.buffer.add(obs, action, log_prob, reward, terminated, value)
            obs = next_obs
            ep_reward += reward
            ep_steps += 1

            if terminated:
                terminal_reason = info.get("reason", "Terminal state reached")
                break

        # Optimize policy network via PPO clipped objective
        loss_dict = agent.update(batch_size=32, epochs=4)

        if ep_reward > best_reward:
            best_reward = ep_reward
            agent.save(save_path)
            saved_tag = "[BEST - SAVED]"
        else:
            saved_tag = ""

        if ep % 5 == 0 or ep == 1:
            elapsed = time.time() - start_time
            print(
                f"Episode {ep:02d}/{total_episodes} | "
                f"Reward: {ep_reward:7.2f} | "
                f"Steps: {ep_steps:02d} | "
                f"PolLoss: {loss_dict['policy_loss']:6.3f} | "
                f"ValLoss: {loss_dict['value_loss']:6.3f} | "
                f"{saved_tag}"
            )

    # Save final model checkpoint
    agent.save(save_path)
    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"[SUCCESS] Training completed in {total_time:.2f} seconds!")
    print(f"[SUCCESS] Model weights saved to: {save_path}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    train_drl_agent(total_episodes=50, steps_per_episode=40)
