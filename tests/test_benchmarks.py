"""
Unit Tests for Phase 6 Empirical Benchmarking Suite.
Verifies:
  1. Multi-protocol comparative simulation execution (PBFT, PoS, Adaptive)
  2. Metrics tracking (FND, Cumulative Joules, Message count)
  3. Energy savings invariant (Adaptive Consensus energy < Static PBFT)
  4. Message complexity invariant (Adaptive messages < PBFT messages)
  5. Publication plot and data export generation
"""
import os
import pytest
from pathlib import Path

from benchmark.benchmark_engine import ConsensusBenchmarkRunner, ProtocolBenchmarkStats
from benchmark.plot_generator import BenchmarkPlotGenerator
from simulator.energy_model import HardwarePreset


class TestBenchmarkEngine:
    """Tests the benchmark runner across all three consensus paradigms."""

    def test_run_short_benchmark_all_protocols(self):
        runner = ConsensusBenchmarkRunner(
            node_count=8,
            hardware=HardwarePreset.ESP32,
            byzantine_f=1,
            drain_multiplier=50.0,
            seed=42
        )
        results = runner.run_benchmark(max_rounds=15)

        assert "Static PBFT" in results
        assert "Static PoS (Fixed Stake)" in results
        assert "AI Adaptive Consensus" in results

        pbft_stats = results["Static PBFT"]
        pos_stats = results["Static PoS (Fixed Stake)"]
        adaptive_stats = results["AI Adaptive Consensus"]

        assert pbft_stats.rounds_executed > 0
        assert pos_stats.rounds_executed > 0
        assert adaptive_stats.rounds_executed > 0

        # Energy invariant: Adaptive consensus must dissipate significantly less energy than PBFT
        assert adaptive_stats.total_energy_dissipated_joules < pbft_stats.total_energy_dissipated_joules

        # Message complexity invariant: PBFT O(N^2) must exceed Adaptive O(K^2)
        assert adaptive_stats.total_messages_exchanged < pbft_stats.total_messages_exchanged

    def test_pos_concentrated_depletion(self):
        """In fixed PoS, the fixed validator nodes deplete while remaining nodes remain untouched."""
        runner = ConsensusBenchmarkRunner(
            node_count=10,
            hardware=HardwarePreset.ESP32,
            drain_multiplier=60000.0,
            seed=42
        )
        pos_stats = runner._run_static_pos(max_rounds=35)

        # First node dead occurs early for the fixed leader
        assert pos_stats.first_node_dead_round is not None
        assert pos_stats.first_node_dead_round <= 35
        # High battery variance in PoS due to unbalanced load
        assert len(pos_stats.std_battery_history) > 0
        assert pos_stats.std_battery_history[-1] > 10.0


class TestPlotGenerator:
    """Tests generation and export of publication charts and CSV/JSON reports."""

    def test_generate_plots_and_exports(self, tmp_path):
        runner = ConsensusBenchmarkRunner(
            node_count=8,
            drain_multiplier=80.0,
            seed=42
        )
        results = runner.run_benchmark(max_rounds=12)

        generator = BenchmarkPlotGenerator(output_dir=str(tmp_path))
        saved_paths = generator.plot_all(results)

        assert Path(saved_paths["battery_decay"]).exists()
        assert Path(saved_paths["cumulative_energy"]).exists()
        assert Path(saved_paths["network_survival"]).exists()
        assert Path(saved_paths["message_scaling"]).exists()
        assert Path(saved_paths["metrics_json"]).exists()

        assert os.path.getsize(saved_paths["battery_decay"]) > 1000
        assert os.path.getsize(saved_paths["cumulative_energy"]) > 1000
        assert os.path.getsize(saved_paths["metrics_json"]) > 100
