"""
Plot Generator and Export Utility for Empirical Benchmarking.
Produces publication-quality comparative visualization charts:
  1. battery_decay_curves.png (Uniform load balancing vs single-node burnout)
  2. cumulative_energy_comparison.png (Fleet energy trajectory)
  3. network_survival_curves.png (Alive nodes vs. rounds, FND, Half-life)
  4. message_complexity_scaling.png (O(N^2) vs O(K^2) communication scaling)
  5. benchmark_metrics_summary.json and .csv
"""
import os
import json
import csv
from pathlib import Path
from typing import Dict, Any
import matplotlib.pyplot as plt
import numpy as np

from benchmark.benchmark_engine import ProtocolBenchmarkStats


class BenchmarkPlotGenerator:
    """Generates publication-quality charts and structured metrics exports."""

    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Configure clean matplotlib presentation style
        plt.rcParams.update({
            "font.family": "sans-serif",
            "font.size": 10,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "figure.titlesize": 13,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "axes.grid": True,
            "grid.alpha": 0.4,
            "grid.linestyle": ":"
        })

    def plot_all(self, results: Dict[str, ProtocolBenchmarkStats]) -> Dict[str, str]:
        """Generates all 4 publication charts and saves them to output_dir."""
        saved_paths = {}
        saved_paths["battery_decay"] = self.plot_battery_decay(results)
        saved_paths["cumulative_energy"] = self.plot_cumulative_energy(results)
        saved_paths["network_survival"] = self.plot_network_survival(results)
        saved_paths["message_scaling"] = self.plot_message_complexity_scaling()
        saved_paths["metrics_json"] = self.export_summary_metrics(results)
        return saved_paths

    def plot_battery_decay(self, results: Dict[str, ProtocolBenchmarkStats]) -> str:
        """Plots individual node battery trajectories for each protocol in subplots."""
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
        fig.suptitle("IoT Node Battery Trajectories Across Consensus Protocols", fontweight="bold", y=0.98)

        colors = ["#ff4444", "#ffaa00", "#00aa55"]
        protocols = ["Static PBFT", "Static PoS (Fixed Stake)", "AI Adaptive Consensus"]

        for idx, (ax, proto_name) in enumerate(zip(axes, protocols)):
            stats = results.get(proto_name)
            if not stats:
                continue

            for node_id, trajectory in stats.node_battery_trajectories.items():
                ax.plot(trajectory, alpha=0.6, linewidth=1.2)

            # Plot mean battery with bold dashed line
            if stats.mean_battery_history:
                ax.plot(stats.mean_battery_history, color="#111111", linewidth=2.5, linestyle="--", label="Fleet Mean")

            ax.set_title(proto_name, fontweight="bold")
            ax.set_xlabel("Consensus Round")
            if idx == 0:
                ax.set_ylabel("Residual Battery (%)")
            ax.set_ylim(-2, 105)
            ax.axhline(15.0, color="red", linestyle=":", alpha=0.7, label="Critical Floor (15%)")
            ax.legend(loc="upper right")

        plt.tight_layout()
        out_path = self.output_dir / "battery_decay_curves.png"
        fig.savefig(out_path)
        plt.close(fig)
        return str(out_path)

    def plot_cumulative_energy(self, results: Dict[str, ProtocolBenchmarkStats]) -> str:
        """Plots cumulative Joules dissipated over rounds."""
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.suptitle("Cumulative Fleet Energy Dissipation (Joules)", fontweight="bold")

        colors = {
            "Static PBFT": "#ff3333",
            "Static PoS (Fixed Stake)": "#ff9900",
            "AI Adaptive Consensus": "#00aa44"
        }
        styles = {
            "Static PBFT": "--",
            "Static PoS (Fixed Stake)": "-.",
            "AI Adaptive Consensus": "-"
        }

        for proto_name, stats in results.items():
            color = colors.get(proto_name, "#555555")
            style = styles.get(proto_name, "-")
            ax.plot(
                stats.cumulative_energy_history,
                label=f"{proto_name} ({stats.total_energy_dissipated_joules:.1f} J)",
                color=color,
                linestyle=style,
                linewidth=2.2
            )

        ax.set_xlabel("Consensus Round")
        ax.set_ylabel("Total Cumulative Energy Dissipated (J)")
        ax.legend(loc="upper left")

        plt.tight_layout()
        out_path = self.output_dir / "cumulative_energy_comparison.png"
        fig.savefig(out_path)
        plt.close(fig)
        return str(out_path)

    def plot_network_survival(self, results: Dict[str, ProtocolBenchmarkStats]) -> str:
        """Plots number of surviving nodes vs rounds (Kaplan-Meier survival style)."""
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.suptitle("Network Survival & Node Longevity Curves", fontweight="bold")

        colors = {
            "Static PBFT": "#ff3333",
            "Static PoS (Fixed Stake)": "#ff9900",
            "AI Adaptive Consensus": "#00aa44"
        }

        for proto_name, stats in results.items():
            color = colors.get(proto_name, "#555555")
            ax.plot(
                stats.alive_nodes_history,
                label=f"{proto_name} (FND: {stats.first_node_dead_round or 'N/A'})",
                color=color,
                linewidth=2.2
            )
            # Mark FND
            if stats.first_node_dead_round is not None and stats.first_node_dead_round < len(stats.alive_nodes_history):
                ax.scatter(
                    [stats.first_node_dead_round],
                    [stats.alive_nodes_history[stats.first_node_dead_round]],
                    color=color,
                    s=60,
                    zorder=5
                )

        ax.axhline(4.0, color="gray", linestyle=":", label="BFT Quorum Floor (3f + 1 = 4)")
        ax.set_xlabel("Consensus Round")
        ax.set_ylabel("Alive Operational Nodes")
        ax.legend(loc="lower left")

        plt.tight_layout()
        out_path = self.output_dir / "network_survival_curves.png"
        fig.savefig(out_path)
        plt.close(fig)
        return str(out_path)

    def plot_message_complexity_scaling(self, max_committee_size: int = 8, min_k: int = 4) -> str:
        """
        Plots ANALYTIC (closed-form) message complexity from N=10 to N=100.

        Message counts follow the same accounting used by the benchmark engine:
          * PBFT:    (N-1) pre-prepare + (N-1)^2 prepare/commit  -> O(N^2)
          * PoS:     2 * (5-1) = 8, independent of N
          * Adaptive: 2 * (K_t - 1), where K_t = min(max(3f+1, N), K_max)

        The adaptive curve is O(K), bounded by K_max -- not O(K^2). An earlier
        revision hard-coded K = 4 for every N, so this "scaling" figure was a
        flat line drawn from a literal rather than a function of N.
        """
        n_vals = np.linspace(10, 100, 19, dtype=int)

        # PBFT: (N - 1) + (N - 1)^2 ≈ N^2
        pbft_messages = (n_vals - 1) + (n_vals - 1) ** 2

        # Fixed PoS (5 validators): 2 * (5 - 1) = 8 messages, constant in N
        pos_messages = np.full_like(n_vals, 8)

        # Adaptive Consensus: committee grows with the fleet but saturates at K_max
        adaptive_k = np.clip(n_vals, min_k, max_committee_size)
        adaptive_messages = 2 * (adaptive_k - 1)

        fig, ax = plt.subplots(figsize=(8, 5))
        fig.suptitle("Message Complexity per Round: O(N²) PBFT vs O(K) Bounded Committee", fontweight="bold")

        ax.plot(n_vals, pbft_messages, label="Static PBFT: O(N²) all-to-all broadcast",
                color="#ff3333", linewidth=2.5)
        ax.plot(n_vals, pos_messages, label="Static PoS: fixed 5 validators (constant)",
                color="#ff9900", linestyle="-.", linewidth=2)
        ax.plot(n_vals, adaptive_messages,
                label=f"AI Adaptive Consensus: O(K), K ≤ {max_committee_size}",
                color="#00aa44", linewidth=2.5)

        ax.set_xlabel("Total Network Size (N IoT Devices)")
        ax.set_ylabel("Messages Transmitted per Consensus Round")
        ax.legend(loc="upper left")

        plt.tight_layout()
        out_path = self.output_dir / "message_complexity_scaling.png"
        fig.savefig(out_path)
        plt.close(fig)
        return str(out_path)

    def export_summary_metrics(self, results: Dict[str, ProtocolBenchmarkStats]) -> str:
        """Exports benchmark metrics summary to JSON and CSV formats."""
        summary = {}
        pbft_energy = results.get("Static PBFT", ProtocolBenchmarkStats(protocol_name="")).total_energy_dissipated_joules

        for name, stats in results.items():
            energy_saved_pct = 0.0
            if pbft_energy > 0:
                energy_saved_pct = ((pbft_energy - stats.total_energy_dissipated_joules) / pbft_energy) * 100.0

            mean_k = (
                round(sum(stats.committee_size_history) / len(stats.committee_size_history), 2)
                if stats.committee_size_history else 0.0
            )
            summary[name] = {
                "Protocol": name,
                "Horizon Rounds": stats.horizon_rounds,
                "Rounds Executed": stats.rounds_executed,
                "Mean Committee Size (K_t)": mean_k,
                "First Node Dead (FND) Round": stats.first_node_dead_round,
                "Network Half-Life Round": stats.network_half_life_round,
                "Partition Round (Quorum Loss)": stats.network_partition_round,
                "Total Energy Dissipated (Joules)": round(stats.total_energy_dissipated_joules, 2),
                "Energy Savings vs PBFT (%)": round(energy_saved_pct, 2),
                "Total Messages Exchanged": stats.total_messages_exchanged,
                "Final Alive Nodes": stats.final_alive_nodes
            }

        # Export JSON
        json_path = self.output_dir / "benchmark_metrics_summary.json"
        with open(json_path, "w") as f:
            json.dump(summary, f, indent=4)

        # Export CSV
        csv_path = self.output_dir / "benchmark_metrics_summary.csv"
        fieldnames = [
            "Protocol",
            "Horizon Rounds",
            "Rounds Executed",
            "Mean Committee Size (K_t)",
            "First Node Dead (FND) Round",
            "Network Half-Life Round",
            "Partition Round (Quorum Loss)",
            "Total Energy Dissipated (Joules)",
            "Energy Savings vs PBFT (%)",
            "Total Messages Exchanged",
            "Final Alive Nodes"
        ]
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in summary.values():
                writer.writerow(row)

        return str(json_path)
