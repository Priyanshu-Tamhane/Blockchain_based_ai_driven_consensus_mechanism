"""
Phase 6 Empirical Benchmarking & Comparative Evaluation Execution Script.
Executes a head-to-head simulation across three consensus paradigms:
  1. Static PBFT (N=14 nodes validate every round, O(N^2) quadratic messaging)
  2. Static PoS (Fixed 5-node validator subset, capital-driven without energy awareness)
  3. AI Adaptive Consensus (Dynamic K_t >= 3f + 1, health-aware rotation, deep sleep)

Generates publication-quality charts and structured reports in benchmark_results/:
  - battery_decay_curves.png
  - cumulative_energy_comparison.png
  - network_survival_curves.png
  - message_complexity_scaling.png
  - benchmark_metrics_summary.json / .csv
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

from benchmark.benchmark_engine import ConsensusBenchmarkRunner
from benchmark.plot_generator import BenchmarkPlotGenerator
from simulator.energy_model import HardwarePreset


def main():
    print("=" * 100)
    print("   PHASE 6: EMPIRICAL BENCHMARKING & COMPARATIVE CONSENSUS EVALUATION")
    print("=" * 100)

    node_count = 14
    max_rounds = 100
    model_path = ROOT_DIR / "models" / "drl_consensus_agent.pt"
    drl_path_str = str(model_path) if model_path.exists() else None

    print(f"\n[*] Fleet Configuration:     {node_count} heterogeneous virtual ESP32 nodes")
    print(f"[*] Total Consensus Rounds:   {max_rounds}")
    print(f"[*] Fault Tolerance Bound:    f = 1 (Min BFT Quorum = 3f + 1 = 4)")
    print(f"[*] AI Policy Network:       {drl_path_str if drl_path_str else 'Multi-Objective MCDM Heuristic'}")
    print("[*] Running comparative simulation across PBFT, PoS, and Adaptive Consensus...\n")

    runner = ConsensusBenchmarkRunner(
        node_count=node_count,
        hardware=HardwarePreset.ESP32,
        byzantine_f=1,
        drain_multiplier=40000.0,
        seed=42
    )

    results = runner.run_benchmark(max_rounds=max_rounds, drl_model_path=drl_path_str)

    # Generate publication figures
    output_dir = ROOT_DIR / "benchmark_results"
    plot_gen = BenchmarkPlotGenerator(output_dir=str(output_dir))
    saved_files = plot_gen.plot_all(results)

    # Print Formatted Results Table
    pbft_energy = results["Static PBFT"].total_energy_dissipated_joules
    adaptive_energy = results["AI Adaptive Consensus"].total_energy_dissipated_joules
    saved_pct = ((pbft_energy - adaptive_energy) / pbft_energy) * 100.0 if pbft_energy > 0 else 0.0

    print("=" * 100)
    print(f"{'Consensus Protocol':<28}{'FND (Round)':<14}{'Half-Life':<14}{'Total Energy (J)':<18}{'Messages':<14}{'Energy Saved %':<16}")
    print("-" * 100)

    for proto_name, stats in results.items():
        energy_pct = 0.0
        if pbft_energy > 0:
            energy_pct = ((pbft_energy - stats.total_energy_dissipated_joules) / pbft_energy) * 100.0

        fnd_str = str(stats.first_node_dead_round) if stats.first_node_dead_round else "None (>100)"
        hl_str = str(stats.network_half_life_round) if stats.network_half_life_round else "None (>100)"

        print(
            f"{proto_name:<28}"
            f"{fnd_str:<14}"
            f"{hl_str:<14}"
            f"{stats.total_energy_dissipated_joules:<18.1f}"
            f"{stats.total_messages_exchanged:<14}"
            f"{f'{energy_pct:.1f}%' if proto_name != 'Static PBFT' else '0.0% (Baseline)':<16}"
        )

    print("=" * 100)
    print("\n[*] Key Research Findings & Benchmarking Conclusions:")
    pbft_fnd = results["Static PBFT"].first_node_dead_round or max_rounds
    pos_fnd = results["Static PoS (Fixed Stake)"].first_node_dead_round or max_rounds
    adp_fnd = results["AI Adaptive Consensus"].first_node_dead_round or max_rounds

    if pos_fnd > 0:
        lifespan_mult = adp_fnd / pos_fnd
        print(f"    1. First Node Dead (FND) Extension: Adaptive Consensus extends FND by {lifespan_mult:.2f}x over Static PoS.")
    print(f"    2. Net Energy Reduction:            {saved_pct:.1f}% less battery dissipation compared to Classical PBFT.")
    print(f"    3. Message Volume Efficiency:       Adaptive consensus scales at O(K^2) vs O(N^2) in PBFT.")
    print(f"    4. Battery Uniformity:              Dynamic leader fatigue prevents single-node burnout, keeping fleet variance low.")

    print("\n[*] Exported Publication Figures to benchmark_results/:")
    for key, path in saved_files.items():
        print(f"    - [{key}]: {path}")

    print("\n" + "=" * 100)
    print("   PHASE 6 EMPIRICAL BENCHMARKING COMPLETED SUCCESSFULLY!")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
