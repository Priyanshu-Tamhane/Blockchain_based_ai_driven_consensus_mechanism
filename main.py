"""
Unified Master Pipeline Execution Script.
AI-Driven Adaptive Consensus Mechanism for Energy-Efficient Blockchain IoT Networks.

Integrates the complete end-to-end system:
  1. Consensus Loop: Virtual ESP32 Fleet (14 nodes), Telemetry Ingestion,
     Dynamic Committee Sizing (K_t >= 3f + 1), and Cryptographic ECDSA Signing.
  2. Optimization Engine: Dual support for Heuristic MCDM and Deep Reinforcement Learning (PPO).
  3. Byzantine Defense & Slashing: Telemetry Spoofing Detection, Cryptographic Double-Signing
     Slashing Proofs, Sybil Rejection, and Silent Dropping Fault Tolerance.
  4. Empirical Benchmarking: Head-to-head comparison against Static PBFT and Fixed PoS,
     generating publication-ready charts in benchmark_results/.
"""
import os
import sys
import argparse
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
os.environ["MPLCONFIGDIR"] = str(tmp_dir)

from bridge.orchestrator import ConsensusOrchestrator
from simulator.adversarial import AttackType
from simulator.energy_model import HardwarePreset
from ai_engine.drl_agent import DRLCommitteeSelector
from benchmark.benchmark_engine import ConsensusBenchmarkRunner
from benchmark.plot_generator import BenchmarkPlotGenerator


def run_consensus_demo(use_drl: bool = True):
    """Executes an end-to-end consensus demonstration with active Byzantine defense."""
    print("\n" + "=" * 96)
    print("   AI-DRIVEN ADAPTIVE IOT CONSENSUS: END-TO-END EXECUTION & DEFENSE PIPELINE")
    print("=" * 96)

    model_path = ROOT_DIR / "models" / "drl_consensus_agent.pt"
    drl_selector = None
    engine_name = "Heuristic MCDM Optimizer"

    if use_drl and model_path.exists():
        drl_selector = DRLCommitteeSelector(model_path=str(model_path), node_count=14)
        engine_name = "Deep Reinforcement Learning (PPO Policy)"

    orchestrator = ConsensusOrchestrator(
        node_count=14,
        hardware=HardwarePreset.ESP32,
        use_blockchain=False,
        selector=drl_selector
    )

    print(f"[*] Fleet Configuration:  14 Virtual ESP32 Nodes")
    print(f"[*] Active Optimization:  {engine_name}")
    print(f"[*] BFT Invariant Floor:  f = 1 (K_t >= 4, Quorum = floor(2/3*K) + 1)")
    print(f"[*] Defense Layer:        Physics-Informed Heinzelman Sanitizer + ECDSA Slashing")

    print("\n" + "-" * 96)
    print(f"{'Epoch':<8}{'Block #':<10}{'Execution Stage':<36}{'K_size':<8}{'Quorum':<8}{'Sigs':<8}{'Status':<12}")
    print("-" * 96)

    # 1. Baseline Honest Rounds
    for ep in range(1, 3):
        summary = orchestrator.run_epoch()
        print(
            f"{summary['epoch_id']:<8}"
            f"#{summary['block_number']:<9}"
            f"{'Honest Consensus Round':<36}"
            f"{summary['committee_size']:<8}"
            f"{summary['quorum_threshold']:<8}"
            f"{summary['signatures_collected']:<8}"
            f"{'COMMITTED' if summary['on_chain_success'] else 'FAILED':<12}"
        )

    # 2. Telemetry Spoofing Attack & Defense
    spoof_node_id = "Node_04"
    target_node = orchestrator.simulator.get_node(spoof_node_id)
    target_node.force_drain_battery(12.0)  # Drain physically below 15% threshold
    orchestrator.adversary.arm_attack(spoof_node_id, AttackType.TELEMETRY_SPOOFING)

    summary_3 = orchestrator.run_epoch()
    print(
        f"{summary_3['epoch_id']:<8}"
        f"#{summary_3['block_number']:<9}"
        f"{'Intercepted: Telemetry Spoofing':<36}"
        f"{summary_3['committee_size']:<8}"
        f"{summary_3['quorum_threshold']:<8}"
        f"{summary_3['signatures_collected']:<8}"
        f"{'COMMITTED' if summary_3['on_chain_success'] else 'FAILED':<12}"
    )
    orchestrator.adversary.disarm_attack(spoof_node_id)

    # 3. Byzantine Double-Signing Equivocation & Slashing
    equiv_target_id = summary_3["leader_id"]
    orchestrator.adversary.arm_attack(equiv_target_id, AttackType.BYZANTINE_EQUIVOCATION)

    summary_4 = orchestrator.run_epoch()
    print(
        f"{summary_4['epoch_id']:<8}"
        f"#{summary_4['block_number']:<9}"
        f"{'Intercepted & Slashed: Double-Signing':<36}"
        f"{summary_4['committee_size']:<8}"
        f"{summary_4['quorum_threshold']:<8}"
        f"{summary_4['signatures_collected']:<8}"
        f"{'COMMITTED' if summary_4['on_chain_success'] else 'FAILED':<12}"
    )
    orchestrator.adversary.disarm_attack(equiv_target_id)

    # 4. Sybil Infiltration Attack & Rejection
    orchestrator.adversary.arm_attack("Node_00", AttackType.SYBIL_INFILTRATION)
    summary_5 = orchestrator.run_epoch()
    print(
        f"{summary_5['epoch_id']:<8}"
        f"#{summary_5['block_number']:<9}"
        f"{'Intercepted: Rogue Sybil Infiltration':<36}"
        f"{summary_5['committee_size']:<8}"
        f"{summary_5['quorum_threshold']:<8}"
        f"{summary_5['signatures_collected']:<8}"
        f"{'COMMITTED' if summary_5['on_chain_success'] else 'FAILED':<12}"
    )
    orchestrator.adversary.disarm_attack("Node_00")

    # 5. Silent Dropping & Liveness Preservation
    drop_node_id = "Node_02"
    orchestrator.adversary.arm_attack(drop_node_id, AttackType.SILENT_DROPPING)
    summary_6 = orchestrator.run_epoch()
    print(
        f"{summary_6['epoch_id']:<8}"
        f"#{summary_6['block_number']:<9}"
        f"{'Fault Tolerated: Silent Dropping (DoS)':<36}"
        f"{summary_6['committee_size']:<8}"
        f"{summary_6['quorum_threshold']:<8}"
        f"{summary_6['signatures_collected']:<8}"
        f"{'COMMITTED' if summary_6['on_chain_success'] else 'FAILED':<12}"
    )
    orchestrator.adversary.disarm_attack(drop_node_id)
    print("-" * 96)

    # Print Security Alerts Summary
    print("\n[*] Byzantine Defense & Slashing Audit Trail:")
    for idx, alert in enumerate(orchestrator.defense.alerts_log, 1):
        print(f"    [{idx}] Severity: {alert.severity} | Attack: {alert.attack_type.value}")
        print(f"        Target: {alert.node_id} ({alert.node_address[:14]}...)")
        print(f"        Action: {alert.action_taken}")

    print(f"\n[*] Slashed & Quarantined Nodes: {len(orchestrator.defense.slashed_addresses)}")
    for addr in orchestrator.defense.slashed_addresses:
        rec = orchestrator.defense.node_history.get(addr)
        print(f"    - {addr} (Reason: {rec.slashed_reason if rec else 'Byzantine Fault'})")


def run_benchmarks(max_rounds: int = 100):
    """Executes long-horizon empirical benchmarking across PBFT, PoS, and Adaptive Consensus."""
    print("\n" + "=" * 100)
    print("   EMPIRICAL BENCHMARKING: ADAPTIVE CONSENSUS VS. STATIC PBFT VS. STATIC POS")
    print("=" * 100)

    node_count = 14
    model_path = ROOT_DIR / "models" / "drl_consensus_agent.pt"
    drl_path_str = str(model_path) if model_path.exists() else None

    print(f"[*] Network Size:          {node_count} IoT Devices")
    print(f"[*] Simulation Horizon:    {max_rounds} Consensus Rounds")
    print(f"[*] Radio Energy Model:    Heinzelman First-Order Physical Dissipation (ESP32 Preset)")
    print(f"[*] Output Directory:      benchmark_results/")

    runner = ConsensusBenchmarkRunner(
        node_count=node_count,
        hardware=HardwarePreset.ESP32,
        byzantine_f=1,
        drain_multiplier=40000.0,
        seed=42
    )

    results = runner.run_benchmark(max_rounds=max_rounds, drl_model_path=drl_path_str)

    output_dir = ROOT_DIR / "benchmark_results"
    plot_gen = BenchmarkPlotGenerator(output_dir=str(output_dir))
    saved_files = plot_gen.plot_all(results)

    pbft_energy = results["Static PBFT"].total_energy_dissipated_joules
    adaptive_energy = results["AI Adaptive Consensus"].total_energy_dissipated_joules
    saved_pct = ((pbft_energy - adaptive_energy) / pbft_energy) * 100.0 if pbft_energy > 0 else 0.0

    print("\n" + "=" * 100)
    print(f"{'Consensus Protocol':<28}{'FND (Round)':<14}{'Half-Life':<14}{'Total Energy (J)':<18}{'Messages':<14}{'Energy Saved %':<16}")
    print("-" * 100)

    for proto_name, stats in results.items():
        energy_pct = 0.0
        if pbft_energy > 0:
            energy_pct = ((pbft_energy - stats.total_energy_dissipated_joules) / pbft_energy) * 100.0

        fnd_str = str(stats.first_node_dead_round) if stats.first_node_dead_round else f"None (>{max_rounds})"
        hl_str = str(stats.network_half_life_round) if stats.network_half_life_round else f"None (>{max_rounds})"

        print(
            f"{proto_name:<28}"
            f"{fnd_str:<14}"
            f"{hl_str:<14}"
            f"{stats.total_energy_dissipated_joules:<18.1f}"
            f"{stats.total_messages_exchanged:<14}"
            f"{f'{energy_pct:.1f}%' if proto_name != 'Static PBFT' else '0.0% (Baseline)':<16}"
        )
    print("=" * 100)

    pbft_fnd = results["Static PBFT"].first_node_dead_round or max_rounds
    pos_fnd = results["Static PoS (Fixed Stake)"].first_node_dead_round or max_rounds
    adp_fnd = results["AI Adaptive Consensus"].first_node_dead_round or max_rounds

    print("\n[*] Key Research Metrics:")
    if pos_fnd > 0:
        lifespan_mult = adp_fnd / pos_fnd
        print(f"    - First Node Dead (FND) Extension: Adaptive Consensus extends FND by {lifespan_mult:.2f}x over Static PoS.")
    print(f"    - Net Energy Conservation:          {saved_pct:.1f}% reduction in cumulative battery dissipation vs. PBFT.")
    print(f"    - Message Volume Scalability:       O(K^2) bounded messaging prevents RF channel saturation.")

    print("\n[*] Generated Publication Figures:")
    for key, path in saved_files.items():
        print(f"    - [{key}]: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Unified Execution Pipeline for AI-Driven Adaptive IoT Blockchain Consensus"
    )
    parser.add_argument(
        "--mode",
        choices=["all", "demo", "benchmark", "train", "report"],
        default="all",
        help="Execution mode: 'all' (demo + benchmark), 'demo' (consensus loop), 'benchmark' (PBFT/PoS comparison), 'train' (PPO training), 'report' (Word docx export)"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=100,
        help="Number of consensus rounds for benchmarking (default: 100)"
    )
    parser.add_argument(
        "--optimizer",
        choices=["drl", "mcdm"],
        default="drl",
        help="Committee election engine for demo: 'drl' (Deep RL PPO) or 'mcdm' (Heuristic)"
    )

    args = parser.parse_args()

    if args.mode in ("all", "demo"):
        run_consensus_demo(use_drl=(args.optimizer == "drl"))

    if args.mode in ("all", "benchmark"):
        run_benchmarks(max_rounds=args.rounds)

    if args.mode == "train":
        from ai_engine.train_rl import train_drl_agent
        print("\n[*] Launching Deep Reinforcement Learning (PPO) Training...")
        train_drl_agent(total_episodes=60, steps_per_episode=50)

    if args.mode == "report":
        from generate_report_docx import create_document
        print("\n[*] Generating Complete Dissertation Report (.docx)...")
        create_document()

    print("\n[+] Unified pipeline execution finished successfully!\n")


if __name__ == "__main__":
    main()
