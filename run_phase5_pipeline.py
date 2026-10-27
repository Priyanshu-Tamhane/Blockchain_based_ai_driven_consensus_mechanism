"""
Phase 5 Adversarial Stress Testing & Byzantine Defense Execution Script.
Demonstrates the full end-to-end security suite under active attack vectors:
  1. Baseline Honest Consensus (Epochs 1-2)
  2. Telemetry Spoofing Detection via Heinzelman Physics Consistency (Epoch 3)
  3. Byzantine Double-Signing (Equivocation) Cryptographic Slashing (Epoch 4)
  4. Sybil Infiltration Rejection via On-Chain Registry Whitelist (Epoch 5)
  5. Validator Silent Dropping & BFT Liveness Preservation (Epoch 6)
  6. Real-Time Slashing and Security Audit Log
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
from simulator.adversarial import AttackType
from simulator.energy_model import HardwarePreset
from ai_engine.drl_agent import DRLCommitteeSelector


def main():
    print("=" * 96)
    print("   PHASE 5: ADVERSARIAL STRESS TESTING & BYZANTINE FAULT TOLERANCE DEFENSE PIPELINE")
    print("=" * 96)

    # Initialize orchestrator with 14 nodes and pre-trained DRL policy
    model_path = ROOT_DIR / "models" / "drl_consensus_agent.pt"
    drl_selector = None
    if model_path.exists():
        drl_selector = DRLCommitteeSelector(model_path=str(model_path), node_count=14)

    orchestrator = ConsensusOrchestrator(
        node_count=14,
        hardware=HardwarePreset.ESP32,
        use_blockchain=False,
        selector=drl_selector
    )

    print(f"\n[*] Initialized Fleet with {len(orchestrator.simulator.nodes)} virtual ESP32 nodes.")
    print("[*] Active Defense Engine: Physics-Informed Heinzelman Sanitizer + ECDSA Equivocation Slasher")
    print("[*] Theoretical Floor: Byzantine Tolerance f = 1 (K_t >= 4, Quorum >= floor(2/3*K) + 1)\n")

    print(f"{'Epoch':<8}{'Block #':<10}{'Attack Scenario':<36}{'K_size':<8}{'Quorum':<8}{'Sigs':<8}{'Status':<12}")
    print("-" * 96)

    # -------------------------------------------------------------
    # Epoch 1 & 2: Honest Baseline
    # -------------------------------------------------------------
    for ep in range(1, 3):
        summary = orchestrator.run_epoch()
        print(
            f"{summary['epoch_id']:<8}"
            f"#{summary['block_number']:<9}"
            f"{'Baseline Honest Consensus':<36}"
            f"{summary['committee_size']:<8}"
            f"{summary['quorum_threshold']:<8}"
            f"{summary['signatures_collected']:<8}"
            f"{'COMMITTED' if summary['on_chain_success'] else 'FAILED':<12}"
        )

    # -------------------------------------------------------------
    # Epoch 3: Telemetry Spoofing / Free-Rider Attack
    # -------------------------------------------------------------
    spoof_target_id = "Node_04"
    target_node = orchestrator.simulator.get_node(spoof_target_id)
    target_node.force_drain_battery(12.0)  # Drain physically to 12.0% (<15% floor)
    orchestrator.adversary.arm_attack(spoof_target_id, AttackType.TELEMETRY_SPOOFING)

    summary_3 = orchestrator.run_epoch()
    print(
        f"{summary_3['epoch_id']:<8}"
        f"#{summary_3['block_number']:<9}"
        f"{'Attack 1: Telemetry Spoofing':<36}"
        f"{summary_3['committee_size']:<8}"
        f"{summary_3['quorum_threshold']:<8}"
        f"{summary_3['signatures_collected']:<8}"
        f"{'COMMITTED' if summary_3['on_chain_success'] else 'FAILED':<12}"
    )
    orchestrator.adversary.disarm_attack(spoof_target_id)

    # -------------------------------------------------------------
    # Epoch 4: Byzantine Double-Signing (Equivocation) Attack
    # -------------------------------------------------------------
    equiv_target_id = summary_3["leader_id"]
    orchestrator.adversary.arm_attack(equiv_target_id, AttackType.BYZANTINE_EQUIVOCATION)

    summary_4 = orchestrator.run_epoch()
    print(
        f"{summary_4['epoch_id']:<8}"
        f"#{summary_4['block_number']:<9}"
        f"{'Attack 2: Double-Signing Equivocation':<36}"
        f"{summary_4['committee_size']:<8}"
        f"{summary_4['quorum_threshold']:<8}"
        f"{summary_4['signatures_collected']:<8}"
        f"{'COMMITTED' if summary_4['on_chain_success'] else 'FAILED':<12}"
    )
    orchestrator.adversary.disarm_attack(equiv_target_id)

    # -------------------------------------------------------------
    # Epoch 5: Sybil Infiltration Attack
    # -------------------------------------------------------------
    orchestrator.adversary.arm_attack("Node_00", AttackType.SYBIL_INFILTRATION)

    summary_5 = orchestrator.run_epoch()
    print(
        f"{summary_5['epoch_id']:<8}"
        f"#{summary_5['block_number']:<9}"
        f"{'Attack 3: Sybil Infiltration':<36}"
        f"{summary_5['committee_size']:<8}"
        f"{summary_5['quorum_threshold']:<8}"
        f"{summary_5['signatures_collected']:<8}"
        f"{'COMMITTED' if summary_5['on_chain_success'] else 'FAILED':<12}"
    )
    orchestrator.adversary.disarm_attack("Node_00")

    # -------------------------------------------------------------
    # Epoch 6: Validator Silent Dropping (DoS / Eclipse)
    # -------------------------------------------------------------
    # Select 1 validator to drop signatures
    last_committee = orchestrator.history[-1]["leader_address"]
    drop_node_id = "Node_02"
    orchestrator.adversary.arm_attack(drop_node_id, AttackType.SILENT_DROPPING)

    summary_6 = orchestrator.run_epoch()
    print(
        f"{summary_6['epoch_id']:<8}"
        f"#{summary_6['block_number']:<9}"
        f"{'Attack 4: Silent Dropping (DoS)':<36}"
        f"{summary_6['committee_size']:<8}"
        f"{summary_6['quorum_threshold']:<8}"
        f"{summary_6['signatures_collected']:<8}"
        f"{'COMMITTED' if summary_6['on_chain_success'] else 'FAILED':<12}"
    )
    orchestrator.adversary.disarm_attack(drop_node_id)

    # -------------------------------------------------------------
    # Security Alerts & Slashing Audit Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 96)
    print("   BYZANTINE DEFENSE & ON-CHAIN SLASHING AUDIT LOG")
    print("=" * 96)

    for idx, alert in enumerate(orchestrator.defense.alerts_log, 1):
        print(f"\n[ALERT #{idx}] Severity: [{alert.severity}] - {alert.attack_type.value}")
        print(f"    - Epoch:        {alert.epoch_id}")
        print(f"    - Target Node:  {alert.node_id} ({alert.node_address[:14]}...)")
        print(f"    - Detection:    {alert.description}")
        print(f"    - Action Taken: {alert.action_taken}")

    print("\n" + "=" * 96)
    print("   SLASHER ENFORCEMENT SUMMARY")
    print("=" * 96)
    print(f"[*] Total Security Incidents Intercepted: {len(orchestrator.defense.alerts_log)}")
    print(f"[*] Total Slashed / Blacklisted Nodes:   {len(orchestrator.defense.slashed_addresses)}")
    for addr in orchestrator.defense.slashed_addresses:
        rec = orchestrator.defense.node_history.get(addr)
        print(f"    - Slashed Address: {addr} (Reason: {rec.slashed_reason if rec else 'Byzantine Fault'})")

    print("\n" + "=" * 96)
    print("   PHASE 5 ADVERSARIAL STRESS TESTING PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 96 + "\n")


if __name__ == "__main__":
    main()
