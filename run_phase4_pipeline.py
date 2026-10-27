"""
Phase 4 Deep Reinforcement Learning (DRL) Pipeline Execution Script.
Demonstrates the full end-to-end consensus loop powered by the trained
Actor-Critic (PPO) neural policy network:
  1. Fleet Telemetry Ingestion (12 nodes)
  2. DRL Policy Network Forward Pass (continuous K_t sizing + node ranking logits)
  3. Dynamic Byzantine Committee Sizing (K_t >= 3f + 1)
  4. Real Cryptographic Block Signing (secp256k1 ECDSA)
  5. Quorum Threshold Enforcement (>= floor(2/3*K) + 1)
  6. Heinzelman Energy Dissipation & Comparison with Static PBFT Baseline
  7. Adversarial / Battery Stress Injection test against the DRL agent
"""
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Redirect inductor and temp directories to local project directory on Windows
tmp_dir = ROOT_DIR / "cache" / "tmp"
tmp_dir.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(tmp_dir)
os.environ["TMP"] = str(tmp_dir)
os.environ["TORCHINDUCTOR_CACHE_DIR"] = str(tmp_dir)

from bridge.orchestrator import ConsensusOrchestrator
from simulator.energy_model import HardwarePreset, HeinzelmanEnergyModel
from ai_engine.drl_agent import DRLCommitteeSelector


def main():
    print("=" * 88)
    print("   PHASE 4 DRL CONSENSUS PIPELINE: ACTOR-CRITIC (PPO) NEURAL POLICY DEPLOYMENT")
    print("=" * 88)

    model_path = ROOT_DIR / "models" / "drl_consensus_agent.pt"
    if not model_path.exists():
        print(f"[-] Trained model not found at {model_path}. Please run python ai_engine/train_rl.py first.")
        return

    node_count = 14
    drl_selector = DRLCommitteeSelector(model_path=str(model_path), node_count=node_count)
    print(f"\n[*] Loaded Pre-trained PPO Agent from: {model_path}")
    print(f"[*] Initialized IoT Fleet with {node_count} virtual ESP32 nodes.")
    print("[*] Neural Policy Inputs: [Battery %, Latency ms, Reputation, Participation Fatigue] x N + Viability Ratio + Epoch Normalized")
    print("[*] Neural Policy Outputs: Continuous K_t Sizing Logit + N Node Priority Logits\n")

    orchestrator = ConsensusOrchestrator(
        node_count=node_count,
        hardware=HardwarePreset.ESP32,
        use_blockchain=False,
        selector=drl_selector
    )

    energy_model = HeinzelmanEnergyModel(hardware=HardwarePreset.ESP32)
    cum_adaptive_j = 0.0
    cum_pbft_j = 0.0

    print(f"{'Epoch':<8}{'Block #':<10}{'Engine':<12}{'K_size':<10}{'Quorum':<10}{'Signatures':<12}{'Leader':<12}{'Avg Batt %':<14}{'Status':<12}")
    print("-" * 100)

    for epoch in range(1, 6):
        summary = orchestrator.run_epoch()

        # Calculate round energy for adaptive vs static PBFT
        adaptive_round_j = sum(
            node.discharge_round_energy(summary["committee_size"], drain_multiplier=1.0)
            for node in orchestrator.simulator.nodes.values()
        )
        pbft_round_j = sum(
            energy_model.calculate_round_energy(is_validator=True, is_leader=False, committee_size=node_count)
            for _ in range(node_count)
        )

        cum_adaptive_j += adaptive_round_j
        cum_pbft_j += pbft_round_j

        print(
            f"{summary['epoch_id']:<8}"
            f"#{summary['block_number']:<9}"
            f"{'DRL (PPO)':<12}"
            f"{summary['committee_size']:<10}"
            f"{summary['quorum_threshold']:<10}"
            f"{summary['signatures_collected']:<12}"
            f"{summary['leader_id']:<12}"
            f"{summary['avg_committee_battery']:<14.1f}"
            f"{'COMMITTED' if summary['on_chain_success'] else 'FAILED':<12}"
        )

    energy_saved_pct = ((cum_pbft_j - cum_adaptive_j) / cum_pbft_j) * 100.0
    print("-" * 100)
    print(f"[*] Cumulative Energy Dissipated (5 Epochs):")
    print(f"    - Static PBFT (N={node_count} validators every round): {cum_pbft_j:.4f} Joules")
    print(f"    - DRL Adaptive Consensus:                     {cum_adaptive_j:.4f} Joules")
    print(f"    - Net Energy Conservation:                    {energy_saved_pct:.2f}% reduction")

    print("\n" + "=" * 88)
    print("   ADVERSARIAL & BATTERY STRESS INJECTION TEST AGAINST DRL POLICY")
    print("=" * 88)

    last_leader_id = orchestrator.history[-1]["leader_id"]
    last_leader_node = orchestrator.simulator.get_node(last_leader_id)
    print(f"[!] Target: {last_leader_id} (Previous round leader)")
    print(f"    Simulating battery crash -> Dropping battery to 10.0% (below 15.0% viability floor)...")
    last_leader_node.force_drain_battery(10.0)

    print("[*] Executing Epoch 6 under DRL policy...")
    summary_6 = orchestrator.run_epoch()

    print(f"\n[*] Epoch 6 Neural Decision Results:")
    print(f"    - Elected Committee Size (K_t): {summary_6['committee_size']} nodes")
    print(f"    - Quorum Required:              {summary_6['quorum_threshold']} ECDSA signatures")
    print(f"    - Signatures Collected:         {summary_6['signatures_collected']}")
    print(f"    - Newly Elected Leader:         {summary_6['leader_id']}")
    print(f"    - Was Degraded Node {last_leader_id} Excluded?  {not last_leader_node.is_validator}")
    print(f"    - Current State of {last_leader_id}:           {'SLEEP / CONSERVING' if not last_leader_node.is_validator else 'CRITICAL'}")

    print("\n" + "=" * 88)
    print("   PHASE 4 DRL PIPELINE DEMONSTRATION SUCCESSFUL!")
    print("=" * 88 + "\n")


if __name__ == "__main__":
    main()
