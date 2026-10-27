"""
Unit and Integration Test Suite for Phase 5: Adversarial Stress Testing & Byzantine Defense.
Verifies:
  1. Adversarial attack injection (Telemetry Spoofing, Equivocation, Sybil, Silent Dropping)
  2. Physics-informed telemetry anomaly detection (Heinzelman dissipation check)
  3. Cryptographic equivocation proof verification and slashing
  4. Sybil vote filtering against on-chain registration whitelist
  5. Byzantine liveness preservation under silent dropping (K >= 3f + 1)
"""
import pytest
from eth_account import Account

from simulator.models import TelemetryPacket, CommitteeDirective, ConsensusVote
from simulator.iot_node import IoTNode
from simulator.energy_model import HardwarePreset
from simulator.adversarial import AdversarialInjector, AttackType, EquivocationPayload
from ai_engine.defense_detector import ByzantineDefenseDetector, SecurityAlert
from bridge.orchestrator import ConsensusOrchestrator


class TestAdversarialInjector:
    """Tests the attack injection module."""

    def test_arm_and_disarm_attacks(self):
        injector = AdversarialInjector()
        assert injector.get_attack_for_node("Node_01") == AttackType.NONE

        injector.arm_attack("Node_01", AttackType.TELEMETRY_SPOOFING)
        assert injector.get_attack_for_node("Node_01") == AttackType.TELEMETRY_SPOOFING

        injector.disarm_attack("Node_01")
        assert injector.get_attack_for_node("Node_01") == AttackType.NONE

    def test_telemetry_tampering_spoofing(self):
        injector = AdversarialInjector()
        node = IoTNode(node_id="Node_01", initial_battery_pct=12.0)
        real_telemetry = node.emit_telemetry()

        # Without attack
        untampered = injector.tamper_telemetry(node, real_telemetry)
        assert untampered.battery_percentage == 12.0

        # With attack armed
        injector.arm_attack("Node_01", AttackType.TELEMETRY_SPOOFING)
        tampered = injector.tamper_telemetry(node, real_telemetry)
        assert tampered.battery_percentage == 100.0
        assert tampered.latency_ms == 5.0

    def test_generate_equivocation_payload(self):
        injector = AdversarialInjector()
        node = IoTNode(node_id="Node_02", initial_battery_pct=85.0)
        payload = injector.generate_equivocation(node, epoch_id=1, block_number=1)

        assert payload.epoch_id == 1
        assert payload.malicious_node_id == "Node_02"
        assert payload.signer_address == node.address
        assert payload.hash_a != payload.hash_b
        assert payload.signature_a != payload.signature_b

    def test_generate_sybil_vote(self):
        injector = AdversarialInjector()
        vote = injector.generate_sybil_vote(epoch_id=1, block_hash="0xabcdef12")
        assert vote.epoch_id == 1
        assert vote.block_hash == "0xabcdef12"
        assert vote.voter_address == injector.sybil_account.address


class TestPhysicsTelemetrySanitization:
    """Tests the Heinzelman physics-based anomaly detector."""

    def test_detects_negative_discharge_spoofing(self):
        detector = ByzantineDefenseDetector(hardware=HardwarePreset.ESP32)

        # Epoch 1: Record node as active Leader with 75.0% battery
        directive = CommitteeDirective(
            epoch_id=1,
            committee_size=4,
            members=["0x1111111111111111111111111111111111111111"],
            leader_address="0x1111111111111111111111111111111111111111",
            quorum_threshold=3
        )
        packet_ep1 = TelemetryPacket(
            node_id="Node_01",
            address="0x1111111111111111111111111111111111111111",
            battery_percentage=75.0,
            latency_ms=40.0,
            reputation_score=0.90,
            is_alive=True
        )
        detector.record_epoch_assignments(1, directive, [packet_ep1])

        # Epoch 2: Malicious node claims battery increased to 100.0%
        spoofed_packet_ep2 = TelemetryPacket(
            node_id="Node_01",
            address="0x1111111111111111111111111111111111111111",
            battery_percentage=100.0,
            latency_ms=5.0,
            reputation_score=0.90,
            is_alive=True
        )

        sanitized = detector.verify_telemetry_physics(2, [spoofed_packet_ep2])
        assert len(sanitized) == 1
        assert sanitized[0].battery_percentage < 75.0  # Corrected to physical value
        assert sanitized[0].reputation_score == 0.45   # Penalized by 50%
        assert len(detector.alerts_log) == 1
        assert detector.alerts_log[0].attack_type == AttackType.TELEMETRY_SPOOFING


class TestCryptographicEquivocationSlashing:
    """Tests the cryptographic verification of double-signing attacks."""

    def test_valid_equivocation_proof_slashes_node(self):
        detector = ByzantineDefenseDetector()
        injector = AdversarialInjector()
        node = IoTNode(node_id="Malicious_Node", initial_battery_pct=90.0)

        proof = injector.generate_equivocation(node, epoch_id=3, block_number=3)
        is_slashed, alert = detector.verify_and_slash_equivocation(proof)

        assert is_slashed is True
        assert alert is not None
        assert alert.attack_type == AttackType.BYZANTINE_EQUIVOCATION
        assert alert.severity == "CRITICAL"
        assert node.address.lower() in detector.slashed_addresses

    def test_tampered_equivocation_proof_rejected(self):
        detector = ByzantineDefenseDetector()
        injector = AdversarialInjector()
        node = IoTNode(node_id="Malicious_Node", initial_battery_pct=90.0)

        proof = injector.generate_equivocation(node, epoch_id=3, block_number=3)
        # Tamper hash_a to a different value without re-signing
        proof.hash_a = "0x" + "00" * 32

        is_slashed, alert = detector.verify_and_slash_equivocation(proof)
        assert is_slashed is False
        assert alert is None


class TestSybilFiltering:
    """Tests dropping of unregistered rogue Sybil votes."""

    def test_sybil_vote_rejected(self):
        detector = ByzantineDefenseDetector()
        injector = AdversarialInjector()

        registered_whitelist = {
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        }
        committee = registered_whitelist

        sybil_vote = injector.generate_sybil_vote(epoch_id=1, block_hash="0x12345678")
        valid_votes, alerts = detector.filter_sybil_and_invalid_votes(
            epoch_id=1,
            votes=[sybil_vote],
            registered_whitelist=registered_whitelist,
            elected_committee=committee
        )

        assert len(valid_votes) == 0
        assert len(alerts) == 1
        assert alerts[0].attack_type == AttackType.SYBIL_INFILTRATION


class TestSilentDroppingAndLiveness:
    """Tests network liveness when a validator silently drops consensus participation."""

    def test_liveness_preserved_under_byzantine_fault_bound(self):
        detector = ByzantineDefenseDetector()

        # Committee size K=4, Quorum = floor(2/3*4) + 1 = 3
        # 1 node is silent, 3 nodes sign -> Quorum achieved!
        directive = CommitteeDirective(
            epoch_id=1,
            committee_size=4,
            members=["0x1", "0x2", "0x3", "0x4"],
            leader_address="0x1",
            quorum_threshold=3
        )
        votes = [
            ConsensusVote(epoch_id=1, block_number=1, block_hash="0xhash", voter_address="0x1", signature="0xsig1"),
            ConsensusVote(epoch_id=1, block_number=1, block_hash="0xhash", voter_address="0x2", signature="0xsig2"),
            ConsensusVote(epoch_id=1, block_number=1, block_hash="0xhash", voter_address="0x3", signature="0xsig3")
            # 0x4 dropped/silent
        ]

        liveness_ok, alert = detector.check_liveness_and_quorum(1, directive, votes)
        assert liveness_ok is True
        assert alert is None

    def test_liveness_failure_when_faults_exceed_bound(self):
        detector = ByzantineDefenseDetector()

        # Committee size K=4, Quorum = 3
        # 2 nodes silent, only 2 sign -> Quorum missed!
        directive = CommitteeDirective(
            epoch_id=1,
            committee_size=4,
            members=["0x1", "0x2", "0x3", "0x4"],
            leader_address="0x1",
            quorum_threshold=3
        )
        votes = [
            ConsensusVote(epoch_id=1, block_number=1, block_hash="0xhash", voter_address="0x1", signature="0xsig1"),
            ConsensusVote(epoch_id=1, block_number=1, block_hash="0xhash", voter_address="0x2", signature="0xsig2")
        ]

        liveness_ok, alert = detector.check_liveness_and_quorum(1, directive, votes)
        assert liveness_ok is False
        assert alert is not None
        assert alert.attack_type == AttackType.SILENT_DROPPING


class TestConsensusOrchestratorDefensePipeline:
    """Integration test: ConsensusOrchestrator running with active defense under attack."""

    def test_end_to_end_equivocation_and_slashing_flow(self):
        orchestrator = ConsensusOrchestrator(node_count=12, use_blockchain=False)

        # Epoch 1: Normal round
        summary_1 = orchestrator.run_epoch()
        assert summary_1["on_chain_success"] is True
        assert summary_1["slashed_nodes_count"] == 0

        # Epoch 2: Arm Byzantine Equivocation on Leader of round 1
        target_leader_id = summary_1["leader_id"]
        orchestrator.adversary.arm_attack(target_leader_id, AttackType.BYZANTINE_EQUIVOCATION)

        summary_2 = orchestrator.run_epoch()
        # Equivocation detected and target slashed!
        assert summary_2["slashed_nodes_count"] >= 1
        slashed_node = orchestrator.simulator.get_node(target_leader_id)
        assert slashed_node.address.lower() in orchestrator.defense.slashed_addresses

        # Epoch 3: Ensure slashed node is permanently excluded from committee
        summary_3 = orchestrator.run_epoch()
        assert slashed_node.address not in summary_3["leader_address"]
        assert not slashed_node.is_validator
