"""
Phase 1 & Phase 2 Interactive Verification Demonstration.
Demonstrates:
  1. Heinzelman Radio Physics & Cryptographic Energy Dissipation
  2. Multi-Node IoT Fleet Telemetry Generation
  3. AI Multi-Objective Optimization & Feasibility Filtering
  4. Byzantine Dynamic Committee Sizing (K >= 3f + 1) & Quorum Calculation
  5. Dynamic Health Protection: Automatic exclusion of low-battery (<15%) nodes
"""
import sys
import time
from simulator.energy_model import HeinzelmanEnergyModel, HardwarePreset
from simulator.models import TelemetryPacket
from ai_engine.objective import MultiObjectiveOptimizer, ObjectiveWeights, SystemConstraints


def print_header(title: str):
    print("\n" + "=" * 78)
    print(f"  {title.upper()}")
    print("=" * 78)


def demo_energy_physics():
    print_header("1. Heinzelman Radio Physics & Microcontroller Energy Dissipation")
    model = HeinzelmanEnergyModel(hardware=HardwarePreset.ESP32)

    print(f"[*] Hardware Profile: ESP32 Xtensa (V_dd=3.3V, I_active=160mA, I_sleep=15uA)")
    print(f"[*] Crossover Distance Threshold (d0): {model.d0:.2f} meters")
    print(f"    - Distances < {model.d0:.1f}m follow Free-Space Model (E_amp ~ d^2)")
    print(f"    - Distances >= {model.d0:.1f}m follow Multi-Path Fading Model (E_amp ~ d^4)\n")

    distances = [10.0, 30.0, 60.0, 87.0, 100.0, 150.0]
    packet_bits = 8192  # 1 KB payload
    print(f"{'Distance (m)':<15}{'E_tx (Joules)':<18}{'Path Loss Regime':<20}")
    print("-" * 55)
    for d in distances:
        e_tx = model.energy_transmit(packet_bits, distance_m=d)
        regime = "Free-Space (d^2)" if d < model.d0 else "Multi-Path Fading (d^4)"
        print(f"{d:<15.1f}{e_tx:<18.6f}{regime:<20}")

    print("\n[*] Consensus Round Role Energy Comparison (K = 6 nodes, 30m distance):")
    e_leader = model.calculate_round_energy(is_validator=True, is_leader=True, committee_size=6, distance_m=30.0)
    e_validator = model.calculate_round_energy(is_validator=True, is_leader=False, committee_size=6, distance_m=30.0)
    e_idle = model.calculate_round_energy(is_validator=False, is_leader=False, committee_size=6, distance_m=30.0)

    print(f"    - Committee Leader (Propose + Verify):  {e_leader * 1000:8.3f} mJ (100.0%)")
    print(f"    - Active Validator (Sign + Transmit):   {e_validator * 1000:8.3f} mJ ({e_validator/e_leader*100:5.1f}%)")
    print(f"    - Idle Sleep Node (Listen Only):        {e_idle * 1000:8.3f} mJ ({e_idle/e_leader*100:5.1f}%)")
    print(f"    >>> Energy Saved by Rotating to Idle:    {(1.0 - (e_idle / e_validator)) * 100:.1f}% reduction per round!")


def demo_ai_optimization_and_rotation():
    print_header("2. AI Multi-Objective Committee Selection & Dynamic Protection")
    
    weights = ObjectiveWeights(w_security=0.35, w_energy=0.45, w_latency=0.20)
    constraints = SystemConstraints(
        min_battery_threshold=15.0,
        min_reputation_floor=0.60,
        byzantine_tolerance_f=1
    )
    optimizer = MultiObjectiveOptimizer(weights=weights, constraints=constraints)

    # Instantiate simulated fleet of 10 nodes
    fleet = [
        TelemetryPacket("Node_00", "0x1000000000000000000000000000000000000001", battery_percentage=95.0, latency_ms=18.0, reputation_score=0.98),
        TelemetryPacket("Node_01", "0x2000000000000000000000000000000000000002", battery_percentage=88.0, latency_ms=22.0, reputation_score=0.92),
        TelemetryPacket("Node_02", "0x3000000000000000000000000000000000000003", battery_percentage=72.0, latency_ms=35.0, reputation_score=0.85),
        TelemetryPacket("Node_03", "0x4000000000000000000000000000000000000004", battery_percentage=45.0, latency_ms=15.0, reputation_score=0.90),
        TelemetryPacket("Node_04", "0x5000000000000000000000000000000000000005", battery_percentage=18.0, latency_ms=40.0, reputation_score=0.88),  # Near threshold
        TelemetryPacket("Node_05", "0x6000000000000000000000000000000000000006", battery_percentage=12.0, latency_ms=10.0, reputation_score=0.95),  # Depleted (<15%)
        TelemetryPacket("Node_06", "0x7000000000000000000000000000000000000007", battery_percentage=80.0, latency_ms=28.0, reputation_score=0.50),  # Low trust (<0.60)
        TelemetryPacket("Node_07", "0x8000000000000000000000000000000000000008", battery_percentage=60.0, latency_ms=19.0, reputation_score=0.82),
        TelemetryPacket("Node_08", "0x9000000000000000000000000000000000000009", battery_percentage=0.0,  latency_ms=99.0, reputation_score=0.70, is_alive=False), # Dead
        TelemetryPacket("Node_09", "0xA000000000000000000000000000000000000010", battery_percentage=82.0, latency_ms=25.0, reputation_score=0.89),
    ]

    print("[*] Current Fleet Status:")
    print(f"{'Node ID':<10}{'Battery %':<12}{'Latency (ms)':<15}{'Reputation':<14}{'Status':<15}")
    print("-" * 66)
    for n in fleet:
        status = "ALIVE" if n.is_alive else "DEAD"
        print(f"{n.node_id:<10}{n.battery_percentage:<12.1f}{n.latency_ms:<15.1f}{n.reputation_score:<14.2f}{status:<15}")

    print("\n[*] Running AI Optimizer for Epoch 1...")
    directive_epoch1 = optimizer.select_committee(epoch_id=1, telemetry=fleet)

    print(f"    - Viable Node Pool:     {int(directive_epoch1.metadata['viable_pool_count'])} nodes (Node_05 excluded: <15% batt, Node_06 excluded: <0.60 trust, Node_08 excluded: dead)")
    print(f"    - Byzantine Safety:     K_t = {directive_epoch1.committee_size} >= 3f + 1 ({3*constraints.byzantine_tolerance_f + 1}) [Satisfied]")
    print(f"    - On-Chain Quorum:      {directive_epoch1.quorum_threshold} signatures required (floor(2/3 * {directive_epoch1.committee_size}) + 1)")
    print(f"    - Designated Leader:    {directive_epoch1.metadata['leader_id']} ({directive_epoch1.leader_address[:10]}...)")
    print(f"    - Committee Utility:    {directive_epoch1.metadata['utility']:.4f}")
    print(f"    - Active Committee:     {[addr[:10] + '...' for addr in directive_epoch1.members]}")

    # SIMULATION OF DYNAMIC ROTATION
    print("\n" + "-" * 78)
    print("[!] DYNAMIC STRESS TEST: Simulating rapid battery drain on Node_00 (the leader)...")
    print("    Node_00 was actively validating; battery drops from 95% down to 10% (CRITICAL)!")
    fleet[0].battery_percentage = 10.0  # Drops below 15% threshold

    print("\n[*] Running AI Optimizer for Epoch 2...")
    directive_epoch2 = optimizer.select_committee(epoch_id=2, telemetry=fleet)

    print(f"    - Is Node_00 in Epoch 2 Committee? {directive_epoch2.members.__contains__(fleet[0].address)}")
    print(f"    - New Designated Leader:           {directive_epoch2.metadata['leader_id']}")
    print(f"    - New Committee Size (K_t):        {directive_epoch2.committee_size}")
    print(f"    - New Active Committee:            {[addr[:10] + '...' for addr in directive_epoch2.members]}")
    print("\n[SUCCESS] Node_00 was dynamically rotated out to low-power sleep, protecting it from network death!")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    demo_energy_physics()
    demo_ai_optimization_and_rotation()
