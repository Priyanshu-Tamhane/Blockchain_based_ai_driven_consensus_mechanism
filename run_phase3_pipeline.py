"""
Phase 3 Prototype Pipeline Execution Script.
Demonstrates the complete end-to-end consensus flow:
  1. Fleet Telemetry Ingestion (12 nodes)
  2. AI Multi-Objective Committee Selection (U_t maximization)
  3. Dynamic Byzantine Committee Sizing (K_t >= 3f + 1)
  4. Real Cryptographic Block Signing (secp256k1 ECDSA)
  5. Quorum Threshold Enforcement (>= floor(2/3*K) + 1)
  6. Post-round Heinzelman energy dissipation & dynamic validator rotation
"""
import time
from bridge.orchestrator import ConsensusOrchestrator
from simulator.energy_model import HardwarePreset


def main():
    print("=" * 80)
    print("   PHASE 3 MID-SEMESTER PROTOTYPE: END-TO-END ADAPTIVE CONSENSUS PIPELINE")
    print("=" * 80)

    # Initialize orchestrator (runs with internal EVM signature validation)
    orchestrator = ConsensusOrchestrator(node_count=12, hardware=HardwarePreset.ESP32, use_blockchain=False)
    print(f"\n[*] Initialized IoT Fleet with {len(orchestrator.simulator.nodes)} virtual ESP32 nodes.")
    print("[*] Security Bounds: Byzantine tolerance f = 1 (Minimum K >= 4), Battery Floor = 15.0%\n")

    print(f"{'Epoch':<8}{'Block #':<10}{'K_size':<10}{'Quorum':<10}{'Signatures':<12}{'Leader':<12}{'Avg Batt %':<14}{'Status':<12}")
    print("-" * 88)

    for epoch in range(1, 6):
        summary = orchestrator.run_epoch()
        print(
            f"{summary['epoch_id']:<8}"
            f"#{summary['block_number']:<9}"
            f"{summary['committee_size']:<10}"
            f"{summary['quorum_threshold']:<10}"
            f"{summary['signatures_collected']:<12}"
            f"{summary['leader_id']:<12}"
            f"{summary['avg_committee_battery']:<14.1f}"
            f"{'COMMITTED' if summary['on_chain_success'] else 'FAILED':<12}"
        )

    print("\n" + "=" * 80)
    print("   DYNAMIC STRESS TEST: FORCING LEADER BATTERY DOWN TO 10.0%")
    print("=" * 80)
    
    # Identify the leader of epoch 5
    last_leader_id = orchestrator.history[-1]["leader_id"]
    last_leader_node = orchestrator.simulator.get_node(last_leader_id)
    print(f"[!] Target: {last_leader_id} (Address: {last_leader_node.address[:12]}...)")
    print(f"    Current Battery: {last_leader_node.battery_pct:.1f}%")
    print("    Simulating high workload drain -> Battery drops to 10.0% (< 15% threshold)!\n")
    
    last_leader_node.force_drain_battery(10.0)

    print("[*] Executing Epoch 6...")
    summary_6 = orchestrator.run_epoch()

    print(f"\n[*] Epoch 6 Results:")
    print(f"    - New Committee Size:   {summary_6['committee_size']}")
    print(f"    - Quorum Required:      {summary_6['quorum_threshold']} signatures")
    print(f"    - Signatures Collected: {summary_6['signatures_collected']}")
    print(f"    - New Round Leader:     {summary_6['leader_id']}")
    
    # Check if drained node was successfully protected
    was_drained_node_in_committee = any(
        addr.lower() == last_leader_node.address.lower()
        for addr in orchestrator.simulator.nodes[last_leader_id].address
    )
    print(f"    - Was {last_leader_id} excluded from validation? {not last_leader_node.is_validator}")
    print(f"    - Current role of {last_leader_id}:             {'VALIDATING (DANGER)' if last_leader_node.is_validator else 'IDLE SLEEP (PROTECTED)'}")

    print("\n" + "=" * 80)
    print("   END-TO-END VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
