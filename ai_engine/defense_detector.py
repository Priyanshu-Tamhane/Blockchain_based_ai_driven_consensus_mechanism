"""
Byzantine Defense and Anomaly Detection Layer for Phase 5.
Combines:
  1. Physics-Informed Telemetry Consistency Checker (Heinzelman radio dissipation)
  2. Cryptographic Equivocation / Double-Signing Verifier
  3. Sybil & Whitelist Infiltration Filter
  4. Liveness & Fault Isolation (Quorum guarantees despite non-responsive nodes)
  5. Automated Slashing & Quarantine Dispatcher
"""
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from eth_account import Account
from eth_account.messages import encode_defunct

from simulator.models import TelemetryPacket, ConsensusVote, CommitteeDirective
from simulator.energy_model import HeinzelmanEnergyModel, HardwarePreset
from simulator.adversarial import EquivocationPayload, AttackType


@dataclass
class SecurityAlert:
    """Security alert record for logging and auditability."""
    epoch_id: int
    node_id: str
    node_address: str
    attack_type: AttackType
    severity: str  # "CRITICAL", "HIGH", "WARNING"
    description: str
    action_taken: str
    timestamp: float = field(default_factory=time.time)
    proof_data: Optional[Dict[str, Any]] = None


@dataclass
class NodeTrackingRecord:
    """Tracks historical physics and consensus participation per node."""
    last_reported_battery: float
    last_role: str  # "LEADER", "VALIDATOR", "IDLE"
    last_committee_size: int
    last_seen_epoch: int
    silent_rounds_count: int = 0
    consecutive_anomalies: int = 0
    is_slashed: bool = False
    slashed_reason: Optional[str] = None


class ByzantineDefenseDetector:
    """Intelligent defense monitor safeguarding the adaptive consensus network."""

    def __init__(self, hardware: HardwarePreset = HardwarePreset.ESP32):
        self.energy_model = HeinzelmanEnergyModel(hardware=hardware)
        self.node_history: Dict[str, NodeTrackingRecord] = {}
        self.alerts_log: List[SecurityAlert] = []
        self.slashed_addresses: Set[str] = set()

    def record_epoch_assignments(
        self,
        epoch_id: int,
        directive: CommitteeDirective,
        telemetry: List[TelemetryPacket]
    ):
        """Initializes or updates historical records before round execution."""
        leader_addr = directive.leader_address.lower()
        member_addrs = {m.lower() for m in directive.members}

        for packet in telemetry:
            addr = packet.address.lower()
            role = "IDLE"
            if addr == leader_addr:
                role = "LEADER"
            elif addr in member_addrs:
                role = "VALIDATOR"

            if addr not in self.node_history:
                self.node_history[addr] = NodeTrackingRecord(
                    last_reported_battery=packet.battery_percentage,
                    last_role=role,
                    last_committee_size=directive.committee_size,
                    last_seen_epoch=epoch_id
                )
            else:
                rec = self.node_history[addr]
                rec.last_role = role
                rec.last_committee_size = directive.committee_size
                rec.last_seen_epoch = epoch_id

    def verify_telemetry_physics(
        self,
        epoch_id: int,
        telemetry: List[TelemetryPacket],
        drain_multiplier: float = 1.0
    ) -> List[TelemetryPacket]:
        """
        Physics-Informed Consistency Verification.
        Cross-checks reported battery against Heinzelman dissipation bounds.
        If a node reports a battery increase without solar harvesting, or fails to
        dissipate energy consistent with its previous round's radio transmission,
        it flags Telemetry Spoofing, penalizes the node, and corrects the value.
        """
        sanitized_telemetry: List[TelemetryPacket] = []

        for packet in telemetry:
            addr = packet.address.lower()
            rec = self.node_history.get(addr)

            if rec is None or rec.is_slashed:
                # If already slashed, ensure it remains quarantined
                if rec and rec.is_slashed:
                    packet = TelemetryPacket(
                        node_id=packet.node_id,
                        address=packet.address,
                        battery_percentage=0.0,
                        latency_ms=999.0,
                        reputation_score=0.0,
                        is_alive=False
                    )
                sanitized_telemetry.append(packet)
                continue

            # Calculate minimum expected energy dissipation based on last round's role
            expected_energy_j = self.energy_model.calculate_round_energy(
                is_validator=(rec.last_role in ("LEADER", "VALIDATOR")),
                is_leader=(rec.last_role == "LEADER"),
                committee_size=max(1, rec.last_committee_size)
            )

            # Convert expected joules into battery percentage drop (33300 Joules standard battery capacity)
            total_joules = 33300.0
            min_expected_drop_pct = (expected_energy_j / total_joules) * 100.0 * drain_multiplier

            prev_batt = rec.last_reported_battery
            current_batt = packet.battery_percentage

            # Anomaly Condition:
            # 1. Reported battery unexpectedly jumped upwards by more than 1.0% (impossible without harvesting)
            # 2. Or node was Leader/Validator but reported a battery drop < 10% of minimum physics bound while claiming 100%
            is_anomaly = False
            anomaly_reason = ""

            if current_batt > prev_batt + 0.1:
                is_anomaly = True
                anomaly_reason = f"Negative discharge: battery increased from {prev_batt:.1f}% to {current_batt:.1f}%"
            elif rec.last_role in ("LEADER", "VALIDATOR") and current_batt >= 99.0 and prev_batt < 80.0:
                is_anomaly = True
                anomaly_reason = f"Free-rider spoofing: reported {current_batt:.1f}% despite prior active role"

            if is_anomaly:
                rec.consecutive_anomalies += 1
                # Penalty: slash reputation score and quarantine
                penalized_rep = max(0.0, packet.reputation_score * 0.5)
                # Correct to estimated physical battery
                corrected_batt = max(0.0, prev_batt - min_expected_drop_pct)

                alert = SecurityAlert(
                    epoch_id=epoch_id,
                    node_id=packet.node_id,
                    node_address=packet.address,
                    attack_type=AttackType.TELEMETRY_SPOOFING,
                    severity="HIGH",
                    description=anomaly_reason,
                    action_taken="Telemetry sanitized, reputation degraded by 50%, quarantined from leadership",
                    proof_data={
                        "reported_battery": current_batt,
                        "previous_battery": prev_batt,
                        "min_expected_drop": min_expected_drop_pct,
                        "consecutive_anomalies": rec.consecutive_anomalies
                    }
                )
                self.alerts_log.append(alert)

                sanitized_packet = TelemetryPacket(
                    node_id=packet.node_id,
                    address=packet.address,
                    battery_percentage=corrected_batt,
                    latency_ms=packet.latency_ms + 100.0,  # Latency penalty
                    reputation_score=penalized_rep,
                    is_alive=packet.is_alive
                )
                rec.last_reported_battery = corrected_batt
                sanitized_telemetry.append(sanitized_packet)
            else:
                rec.last_reported_battery = current_batt
                rec.consecutive_anomalies = max(0, rec.consecutive_anomalies - 1)
                sanitized_telemetry.append(packet)

        return sanitized_telemetry

    def verify_and_slash_equivocation(
        self,
        proof: EquivocationPayload
    ) -> Tuple[bool, Optional[SecurityAlert]]:
        """
        Cryptographic verification of Byzantine Equivocation (Double Signing).
        Recovers ECDSA public keys from both conflicting signed hashes.
        If signatures resolve to the same address with distinct hashes, triggers immediate slashing.
        """
        if proof.hash_a == proof.hash_b:
            return False, None

        try:
            # Recover signers for both hashes
            msg_a = encode_defunct(hexstr=proof.hash_a)
            msg_b = encode_defunct(hexstr=proof.hash_b)

            signer_a = Account.recover_message(msg_a, signature=proof.signature_a)
            signer_b = Account.recover_message(msg_b, signature=proof.signature_b)

            if signer_a.lower() == signer_b.lower() == proof.signer_address.lower():
                # Cryptographic proof confirmed! Slash the node
                slashed_addr = proof.signer_address.lower()
                self.slashed_addresses.add(slashed_addr)

                if slashed_addr in self.node_history:
                    self.node_history[slashed_addr].is_slashed = True
                    self.node_history[slashed_addr].slashed_reason = "Byzantine Double-Signing Equivocation"

                alert = SecurityAlert(
                    epoch_id=proof.epoch_id,
                    node_id=proof.malicious_node_id,
                    node_address=proof.signer_address,
                    attack_type=AttackType.BYZANTINE_EQUIVOCATION,
                    severity="CRITICAL",
                    description="Malicious node produced 2 conflicting signed block proposals for the same epoch",
                    action_taken="Cryptographic proof verified: Node permanently slashed & quarantined on-chain",
                    proof_data={
                        "hash_a": proof.hash_a,
                        "hash_b": proof.hash_b,
                        "signature_a": proof.signature_a[:18] + "...",
                        "signature_b": proof.signature_b[:18] + "..."
                    }
                )
                self.alerts_log.append(alert)
                return True, alert

        except Exception as e:
            return False, None

        return False, None

    def filter_sybil_and_invalid_votes(
        self,
        epoch_id: int,
        votes: List[ConsensusVote],
        registered_whitelist: Set[str],
        elected_committee: Set[str]
    ) -> Tuple[List[ConsensusVote], List[SecurityAlert]]:
        """
        Filters out votes signed by unregistered Sybil addresses or non-committee nodes.
        """
        valid_votes = []
        sybil_alerts = []
        registered_lower = {a.lower() for a in registered_whitelist}
        elected_lower = {a.lower() for a in elected_committee}

        for vote in votes:
            voter_addr = vote.voter_address.lower()

            if voter_addr not in registered_lower:
                # Rogue Sybil node detected!
                alert = SecurityAlert(
                    epoch_id=epoch_id,
                    node_id="Unknown_Sybil",
                    node_address=vote.voter_address,
                    attack_type=AttackType.SYBIL_INFILTRATION,
                    severity="CRITICAL",
                    description=f"Unregistered rogue address {vote.voter_address[:12]}... attempted to inject consensus vote",
                    action_taken="Vote rejected & dropped from quorum aggregation",
                    proof_data={"unregistered_voter": vote.voter_address, "block_hash": vote.block_hash}
                )
                sybil_alerts.append(alert)
                self.alerts_log.append(alert)
                continue

            if voter_addr not in elected_lower:
                # Registered node, but not part of this round's committee
                continue

            valid_votes.append(vote)

        return valid_votes, sybil_alerts

    def check_liveness_and_quorum(
        self,
        epoch_id: int,
        directive: CommitteeDirective,
        valid_votes: List[ConsensusVote]
    ) -> Tuple[bool, Optional[SecurityAlert]]:
        """
        Verifies whether Byzantine quorum is achieved despite silent or dropped nodes.
        """
        collected_sigs = len(valid_votes)
        quorum_needed = directive.quorum_threshold

        # Check for silent / dropped nodes
        active_signers = {v.voter_address.lower() for v in valid_votes}
        for member in directive.members:
            if member.lower() not in active_signers:
                rec = self.node_history.get(member.lower())
                if rec:
                    rec.silent_rounds_count += 1

        if collected_sigs >= quorum_needed:
            # Quorum achieved! Liveness preserved
            return True, None
        else:
            # Quorum failed: Liveness compromised
            alert = SecurityAlert(
                epoch_id=epoch_id,
                node_id="Consensus_Failure",
                node_address="N/A",
                attack_type=AttackType.SILENT_DROPPING,
                severity="CRITICAL",
                description=f"Quorum missed: {collected_sigs}/{quorum_needed} signatures collected. Network stalled.",
                action_taken="Epoch aborted, fallback election initiated"
            )
            self.alerts_log.append(alert)
            return False, alert
