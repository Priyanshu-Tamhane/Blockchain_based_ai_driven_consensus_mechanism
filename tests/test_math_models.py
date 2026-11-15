"""
Unit test suite verifying mathematical models:
Heinzelman energy physics, BFT safety bounds, and multi-objective utility scoring.
"""
import pytest
import math
import random
from simulator.energy_model import HeinzelmanEnergyModel, HardwarePreset
from simulator.models import TelemetryPacket
from simulator.fleet_simulator import IoTFleetSimulator
from ai_engine.objective import (
    MultiObjectiveOptimizer,
    ObjectiveWeights,
    SystemConstraints,
)


class TestHeinzelmanEnergyModel:
    """Tests the physical radio and CPU energy calculations."""

    def test_crossover_distance(self):
        model = HeinzelmanEnergyModel()
        # d0 = sqrt(10e-12 / 0.0013e-12) ~ 87.7 meters
        assert 87.0 < model.d0 < 88.0

    def test_transmission_energy_scaling(self):
        model = HeinzelmanEnergyModel()
        bits = 1000
        # Energy at 10m (free space, d^2)
        e_10m = model.energy_transmit(bits, distance_m=10.0)
        # Energy at 20m (free space, d^2)
        e_20m = model.energy_transmit(bits, distance_m=20.0)
        
        # d^2 component increases with distance
        assert e_20m > e_10m
        assert e_10m > bits * model.e_elec

    def test_multipath_fading_energy(self):
        model = HeinzelmanEnergyModel()
        bits = 1000
        # Beyond d0 (~87.7m), d^4 applies
        e_below_d0 = model.energy_transmit(bits, distance_m=80.0)
        e_above_d0 = model.energy_transmit(bits, distance_m=100.0)
        assert e_above_d0 > e_below_d0

    def test_reception_energy_linear(self):
        model = HeinzelmanEnergyModel()
        e_1000_bits = model.energy_receive(1000)
        e_2000_bits = model.energy_receive(2000)
        assert math.isclose(e_2000_bits, 2 * e_1000_bits, rel_tol=1e-5)

    def test_validator_vs_idle_energy_disparity(self):
        """Validates that an idle node consumes vastly less energy than a consensus validator."""
        model = HeinzelmanEnergyModel(hardware=HardwarePreset.ESP32)
        k_size = 5
        
        e_leader = model.calculate_round_energy(
            is_validator=True, is_leader=True, committee_size=k_size
        )
        e_validator = model.calculate_round_energy(
            is_validator=True, is_leader=False, committee_size=k_size
        )
        e_idle = model.calculate_round_energy(
            is_validator=False, is_leader=False, committee_size=k_size
        )

        assert e_leader > e_validator
        assert e_validator > e_idle
        # Idle node should consume less than 10% of a validator's energy
        assert e_idle < 0.10 * e_validator


class TestMultiObjectiveOptimization:
    """Tests the AI controller utility function and BFT constraints."""

    def test_weight_auto_normalization(self):
        weights = ObjectiveWeights(w_security=1.0, w_energy=1.0, w_latency=2.0)
        # Sum is 4.0; auto-normalized to 0.25, 0.25, 0.50
        assert math.isclose(weights.w_security, 0.25, rel_tol=1e-3)
        assert math.isclose(weights.w_energy, 0.25, rel_tol=1e-3)
        assert math.isclose(weights.w_latency, 0.50, rel_tol=1e-3)

    def test_zero_total_weights_rejected(self):
        """All-zero weights would previously raise ZeroDivisionError mid-normalization."""
        with pytest.raises(ValueError, match="positive value"):
            ObjectiveWeights(w_security=0.0, w_energy=0.0, w_latency=0.0)

    def test_feasibility_filtering(self):
        optimizer = MultiObjectiveOptimizer(
            constraints=SystemConstraints(min_battery_threshold=15.0, min_reputation_floor=0.60)
        )
        
        fleet = [
            TelemetryPacket("N0", "0x0001", battery_percentage=90.0, reputation_score=0.9, latency_ms=20.0),
            TelemetryPacket("N1", "0x0002", battery_percentage=14.9, reputation_score=0.9, latency_ms=10.0), # Low battery
            TelemetryPacket("N2", "0x0003", battery_percentage=80.0, reputation_score=0.55, latency_ms=15.0), # Low rep
            TelemetryPacket("N3", "0x0004", battery_percentage=70.0, reputation_score=0.85, latency_ms=25.0, is_alive=False), # Dead
            TelemetryPacket("N4", "0x0005", battery_percentage=65.0, reputation_score=0.80, latency_ms=30.0), # Viable
        ]
        
        feasible = optimizer.filter_feasible_nodes(fleet)
        node_ids = [n.node_id for n in feasible]
        
        assert "N0" in node_ids
        assert "N4" in node_ids
        assert "N1" not in node_ids  # Filtered out: Battery <= 15%
        assert "N2" not in node_ids  # Filtered out: Rep < 0.60
        assert "N3" not in node_ids  # Filtered out: is_alive == False
        assert len(feasible) == 2

    def test_bft_quorum_and_leader_election(self):
        optimizer = MultiObjectiveOptimizer(
            constraints=SystemConstraints(byzantine_tolerance_f=1)
        )
        
        # Create 10 viable nodes with varying battery and latencies
        fleet = []
        for i in range(10):
            fleet.append(
                TelemetryPacket(
                    node_id=f"Node_{i}",
                    address=f"0x{i:040x}",
                    battery_percentage=50.0 + (i * 5.0),  # Node 9 has highest battery (95%)
                    reputation_score=0.95,
                    latency_ms=20.0
                )
            )

        directive = optimizer.select_committee(epoch_id=1, telemetry=fleet)

        # Min committee size for f=1 must be >= 3f + 1 = 4
        assert directive.committee_size >= 4
        assert len(directive.members) == directive.committee_size
        
        # Quorum must equal floor(2/3 * K) + 1
        expected_quorum = math.floor((2.0 / 3.0) * directive.committee_size) + 1
        assert directive.quorum_threshold == expected_quorum

        # Leader should be the highest utility node (Node 9 has highest battery and equal reputation/latency)
        assert directive.leader_address == f"0x{9:040x}"

    def test_bft_invariant_failure_raises_exception(self):
        optimizer = MultiObjectiveOptimizer(
            constraints=SystemConstraints(byzantine_tolerance_f=1)  # requires >= 4 nodes
        )
        
        # Only 2 viable nodes
        fleet = [
            TelemetryPacket("N0", "0x0001", battery_percentage=90.0, reputation_score=0.9),
            TelemetryPacket("N1", "0x0002", battery_percentage=85.0, reputation_score=0.8),
        ]
        
        with pytest.raises(ValueError, match="Insufficient viable nodes"):
            optimizer.select_committee(epoch_id=1, telemetry=fleet)


class TestFleetSimulatorDeterminism:
    """
    Guards the two properties the benchmark's credibility depends on:
    seeding must be local, and heterogeneity must be reproducible.
    """

    def test_simulator_seeding_does_not_mutate_global_rng(self):
        """
        Constructing a simulator must not reseed the process-wide RNG.

        Regression: the simulator used to call `random.seed(seed)` in __init__,
        which silently rewrote the global RNG stream for every other consumer
        (test ordering, dashboard sampling, any later simulation).
        """
        random.seed(1234)
        expected = [random.random() for _ in range(5)]

        random.seed(1234)
        IoTFleetSimulator(node_count=6, seed=999)  # must be side-effect free
        actual = [random.random() for _ in range(5)]

        assert expected == actual

    def test_fleet_initialisation_is_reproducible(self):
        """Same seed must yield identical battery / latency / reputation values."""
        a = IoTFleetSimulator(node_count=14, seed=42)
        b = IoTFleetSimulator(node_count=14, seed=42)

        for (a_id, node_a), (b_id, node_b) in zip(a.nodes.items(), b.nodes.items()):
            assert a_id == b_id
            assert math.isclose(node_a.battery_pct, node_b.battery_pct, rel_tol=1e-9)
            assert math.isclose(node_a.base_latency_ms, node_b.base_latency_ms, rel_tol=1e-9)
            assert math.isclose(node_a.reputation, node_b.reputation, rel_tol=1e-9)
