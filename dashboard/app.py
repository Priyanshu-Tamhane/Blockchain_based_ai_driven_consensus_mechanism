"""
Real-Time Interactive Dashboard for Adaptive IoT Blockchain Consensus.
Interactive Visual Presentation Interface.

Displays:
  - Fleet telemetry, role rotation, and battery state
  - Dynamic committee selection (DRL / MCDM) with quorum verification
  - Cumulative energy savings vs. Static PBFT baseline
  - Byzantine defense audit trail and block settlement ledger

Frontend-only module: all simulation logic lives in simulator/, ai_engine/, bridge/.
"""
import sys
import os
import time
import hashlib
from pathlib import Path

# Ensure project root is in Python sys.path regardless of where streamlit is launched from
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import altair as alt

from simulator.fleet_simulator import IoTFleetSimulator
from simulator.energy_model import HeinzelmanEnergyModel, HardwarePreset
from simulator.adversarial import AdversarialInjector, AttackType
from ai_engine.objective import MultiObjectiveOptimizer, ObjectiveWeights, SystemConstraints
from ai_engine.drl_agent import DRLCommitteeSelector
from ai_engine.defense_detector import ByzantineDefenseDetector

# ---------------------------------------------------------------------------
# Design tokens: one accent (emerald), semantic color reserved for real state.
# ---------------------------------------------------------------------------
CSS = """
<style>
:root{
  --bg:#0a0e13; --panel:#131a22; --panel2:#0d1219; --border:#1f2a35; --border2:#24303d;
  --text:#e8edf2; --muted:#8b98a5; --accent:#2fbf71; --accent-dim:rgba(47,191,113,.13);
  --gold:#e6a23c; --blue:#4ea1d3; --amber:#e0a63c; --red:#e5484d; --dead:#6b7684;
  --font-ui:"Segoe UI Variable Display","Segoe UI",-apple-system,"Helvetica Neue",Arial,sans-serif;
  --font-mono:"Cascadia Mono","JetBrains Mono",Consolas,"SF Mono",ui-monospace,monospace;
}
html,body,.stApp{ background:var(--bg) !important; }
.stApp{ font-family:var(--font-ui) !important; color:var(--text); }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"]{ background:var(--panel2); border-right:1px solid var(--border); }
.side-title{ font-size:15px; font-weight:800; letter-spacing:-.01em; color:var(--text); }
.side-label{ font-family:var(--font-mono); font-size:10px; font-weight:700; letter-spacing:.14em;
  text-transform:uppercase; color:var(--muted); margin:18px 0 6px; }
.side-note{ font-family:var(--font-mono); font-size:10.5px; color:var(--muted); line-height:1.7;
  margin-top:18px; padding-top:12px; border-top:1px solid var(--border); }
.side-note b{ color:var(--accent); font-weight:600; }

/* ---------- Header ---------- */
.app-header{ display:flex; justify-content:space-between; align-items:flex-end; gap:16px;
  padding:4px 2px 14px; border-bottom:1px solid var(--border); margin-bottom:18px; }
.app-title{ font-size:25px; font-weight:800; letter-spacing:-.02em; line-height:1.15; color:var(--text); }
.app-sub{ font-size:13px; color:var(--muted); margin-top:5px; }
.app-bft{ font-family:var(--font-mono); font-size:11px; color:var(--muted); text-align:right; line-height:1.6; white-space:nowrap; }
.app-bft b{ color:var(--accent); font-weight:600; }

/* ---------- Buttons ---------- */
.stButton>button{
  background:var(--panel); color:var(--text); border:1px solid var(--border2);
  border-radius:8px; font-weight:600; font-size:13.5px;
  transition:border-color .15s ease, background .15s ease;
}
.stButton>button:hover{ border-color:var(--accent); background:#18212b; color:#ffffff; }
.stButton>button:active{ transform:translateY(1px); }
.stButton>button[kind="primary"],[data-testid="stBaseButton-primary"]{
  background:var(--accent); color:#06130d; border:1px solid var(--accent); font-weight:700;
}
.stButton>button[kind="primary"]:hover,[data-testid="stBaseButton-primary"]:hover{
  background:#3ad07f; border-color:#3ad07f; color:#06130d;
}

/* ---------- Tabs ---------- */
[data-testid="stTabs"] [data-baseweb="tab-list"]{ gap:4px; border-bottom:1px solid var(--border); }
[data-testid="stTabs"] [data-baseweb="tab"]{
  background:transparent; border-radius:8px 8px 0 0; padding:10px 18px;
  font-weight:600; font-size:14px; color:var(--muted);
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover{ color:var(--text); }
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"]{ color:var(--accent); }
[data-testid="stTabs"] [data-baseweb="tab-highlight"],[data-testid="stTabs-tab-highlight"]{
  background-color:var(--accent); height:2px; border-radius:2px;
}

/* ---------- Metric tiles ---------- */
[data-testid="stMetric"]{
  background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:12px 16px 10px;
}
[data-testid="stMetricLabel"]{
  color:var(--muted); font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  font-family:var(--font-mono);
}
[data-testid="stMetricValue"]{ font-family:var(--font-mono); font-weight:700; color:var(--text); }

/* ---------- Pills ---------- */
.pill{
  display:inline-flex; align-items:center; gap:6px; font-family:var(--font-mono);
  font-size:10px; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
  padding:3px 9px; border-radius:999px; border:1px solid transparent; white-space:nowrap;
}
.pill-leader{ background:rgba(230,162,60,.13); color:var(--gold); border-color:rgba(230,162,60,.45); }
.pill-validator{ background:rgba(78,161,211,.12); color:#69b6e8; border-color:rgba(78,161,211,.45); }
.pill-idle{ background:rgba(139,152,165,.10); color:var(--muted); border-color:rgba(139,152,165,.35); }
.pill-quarantine{ background:rgba(224,166,60,.12); color:var(--amber); border-color:rgba(224,166,60,.45); }
.pill-slashed{ background:rgba(229,72,77,.13); color:#f07b7f; border-color:rgba(229,72,77,.5); }
.pill-dead{ background:rgba(107,118,132,.12); color:var(--dead); border-color:rgba(107,118,132,.4); }
.pill-ok{ background:var(--accent-dim); color:var(--accent); border-color:rgba(47,191,113,.45); }
.pill-fail{ background:rgba(229,72,77,.13); color:#f07b7f; border-color:rgba(229,72,77,.5); }
.pill-attack{ background:rgba(229,72,77,.13); color:#f07b7f; border-color:rgba(229,72,77,.5); }

/* ---------- Section headers ---------- */
.section-head{ display:flex; align-items:baseline; justify-content:space-between; gap:12px;
  margin:20px 0 10px; flex-wrap:wrap; }
.section-title{ font-size:15px; font-weight:700; letter-spacing:-.01em; color:var(--text); }
.section-note{ font-size:11.5px; color:var(--muted); }

/* ---------- Fleet grid ---------- */
.fleet-grid{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
@media(max-width:1500px){ .fleet-grid{ grid-template-columns:repeat(3,1fr); } }
@media(max-width:1000px){ .fleet-grid{ grid-template-columns:repeat(2,1fr); } }
@media(max-width:640px){ .fleet-grid{ grid-template-columns:1fr; } }
.node-card{ background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:12px 12px 10px; border-left:3px solid var(--border2); }
.node-card.st-leader{ border-left-color:var(--gold); }
.node-card.st-validator{ border-left-color:var(--blue); }
.node-card.st-quarantine{ border-left-color:var(--amber); }
.node-card.st-slashed{ border-left-color:var(--red); }
.node-card.st-dead{ border-left-color:var(--dead); }
.node-card.st-idle{ border-left-color:#2a3947; }
.node-head{ display:flex; justify-content:space-between; align-items:center; gap:6px; margin-bottom:9px; }
.node-id{ font-family:var(--font-mono); font-size:12px; font-weight:700; color:var(--text); }
.battery-track{ height:6px; border-radius:4px; background:#1a232e; overflow:hidden; }
.battery-fill{ height:100%; border-radius:4px; }
.node-stats{ display:flex; justify-content:space-between; margin-top:8px;
  font-family:var(--font-mono); font-size:10.5px; color:var(--muted); }
.node-stats b{ color:var(--text); font-weight:600; }

/* ---------- Stat tiles (security strip) ---------- */
.stat-tile{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:12px 16px; }
.stat-tile .k{ font-family:var(--font-mono); font-size:10px; font-weight:700; letter-spacing:.1em;
  text-transform:uppercase; color:var(--muted); margin-bottom:6px; }
.stat-tile .v{ font-family:var(--font-mono); font-size:22px; font-weight:700; color:var(--text); }

/* ---------- Alert cards ---------- */
.alert-card{ background:var(--panel); border:1px solid var(--border); border-left:3px solid var(--border2);
  border-radius:10px; padding:12px 14px; margin-bottom:10px; }
.alert-card.sev-critical{ border-left-color:var(--red); }
.alert-card.sev-high{ border-left-color:var(--amber); }
.alert-card.sev-warning{ border-left-color:var(--blue); }
.alert-top{ display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:7px; flex-wrap:wrap; }
.alert-meta{ display:flex; gap:10px; font-family:var(--font-mono); font-size:10.5px; color:var(--muted); }
.alert-attack{ font-size:13.5px; font-weight:700; color:var(--text); margin-bottom:4px; }
.alert-desc{ font-size:12.5px; color:var(--muted); line-height:1.55; }
.alert-action{ font-size:12px; color:var(--text); margin-top:7px; padding-top:7px;
  border-top:1px dashed var(--border); line-height:1.5; }
.alert-action b{ color:var(--accent); font-weight:700; }

/* ---------- Latest block card ---------- */
.block-card{ background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px 18px; }
.block-top{ display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; }
.block-number{ font-family:var(--font-mono); font-size:18px; font-weight:800; color:var(--accent); }
.block-grid{ display:grid; grid-template-columns:repeat(6,1fr); gap:12px; }
@media(max-width:900px){ .block-grid{ grid-template-columns:repeat(3,1fr); } }
.block-cell .k{ font-family:var(--font-mono); font-size:9.5px; font-weight:700; letter-spacing:.09em;
  text-transform:uppercase; color:var(--muted); margin-bottom:3px; }
.block-cell .v{ font-family:var(--font-mono); font-size:13px; font-weight:600; color:var(--text); }

/* ---------- Epoch strip ---------- */
.epoch-strip{ display:flex; flex-wrap:wrap; gap:4px; margin-top:2px; }
.chip{ min-width:28px; height:22px; border-radius:5px; display:flex; align-items:center; justify-content:center;
  font-family:var(--font-mono); font-size:9.5px; font-weight:600; padding:0 4px;
  background:var(--accent-dim); color:var(--accent); border:1px solid rgba(47,191,113,.35); }
.chip.fail{ background:rgba(229,72,77,.12); color:#f07b7f; border-color:rgba(229,72,77,.4); }
.strip-caption{ font-size:11px; color:var(--muted); margin-top:8px; }

/* ---------- Empty panels ---------- */
.empty-panel{ background:var(--panel); border:1px dashed var(--border2); border-radius:10px;
  padding:26px 20px; text-align:center; color:var(--muted); font-size:13px; }
.empty-panel .pill{ margin-bottom:8px; }

/* ---------- Live mode ---------- */
.live-strip{ display:flex; align-items:center; gap:10px; padding:5px 2px; }
.live-label{ font-family:var(--font-mono); font-size:11px; font-weight:800; letter-spacing:.12em; color:var(--accent); }
.live-text{ font-size:12px; color:var(--muted); }
.live-dot{ width:8px; height:8px; border-radius:50%; background:var(--accent);
  display:inline-block; animation:pulse 1.6s ease-in-out infinite; }
@keyframes pulse{ 0%,100%{opacity:1;} 50%{opacity:.35;} }
@media (prefers-reduced-motion: reduce){ .live-dot{ animation:none; } }
</style>
"""

# Cap on stored per-epoch history so long live sessions stay lightweight.
MAX_HISTORY = 300

ATTACK_SHORT = {
    AttackType.TELEMETRY_SPOOFING: "SPOOFING",
    AttackType.BYZANTINE_EQUIVOCATION: "DOUBLE-SIGN",
    AttackType.SYBIL_INFILTRATION: "SYBIL",
    AttackType.SILENT_DROPPING: "SILENT DROP",
}


# ---------------------------------------------------------------------------
# Small presentation helpers
# ---------------------------------------------------------------------------
def load_css():
    st.markdown(CSS, unsafe_allow_html=True)


def section_head(title: str, note: str = None):
    note_html = f'<div class="section-note">{note}</div>' if note else ""
    st.markdown(
        f'<div class="section-head"><div class="section-title">{title}</div>{note_html}</div>',
        unsafe_allow_html=True,
    )


def battery_color(pct: float) -> str:
    if pct <= 15.0:
        return "var(--red)"
    if pct <= 50.0:
        return "var(--amber)"
    return "var(--accent)"


def node_role(node):
    """Resolves the display role for a node (badge label, pill class, card class)."""
    if node.address.lower() in st.session_state.defense.slashed_addresses:
        return ("SLASHED", "pill-slashed", "st-slashed")
    if not node.is_alive:
        return ("DEAD", "pill-dead", "st-dead")
    if node.is_leader:
        return ("LEADER", "pill-leader", "st-leader")
    if node.is_validator:
        return ("VALIDATOR", "pill-validator", "st-validator")
    if node.battery_pct <= 15.0:
        return ("QUARANTINED", "pill-quarantine", "st-quarantine")
    return ("IDLE", "pill-idle", "st-idle")


def _finalize(chart):
    """Applies the dark chart theme shared by every figure."""
    return (
        chart.configure(background="transparent")
        .configure_axis(
            labelColor="#8b98a5", titleColor="#aeb9c4", gridColor="#1a242e",
            domainColor="#2a3947", tickColor="#2a3947", labelFontSize=11,
            titleFontSize=12, labelLimit=220,
        )
        .configure_legend(labelColor="#e8edf2", titleColor="#8b98a5", labelFontSize=11, symbolLimit=30)
        .configure_view(stroke=None)
    )


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_or_reset_simulation():
    """Initializes or completely resets the fleet simulation state."""
    st.session_state.fleet_size = 14
    st.session_state.simulator = IoTFleetSimulator(node_count=st.session_state.fleet_size, seed=42)
    st.session_state.adversary = AdversarialInjector()
    st.session_state.defense = ByzantineDefenseDetector(hardware=HardwarePreset.ESP32)
    st.session_state.alerts_history = []
    st.session_state.weights = ObjectiveWeights(w_security=0.35, w_energy=0.45, w_latency=0.20)
    st.session_state.constraints = SystemConstraints(
        min_battery_threshold=15.0,
        min_reputation_floor=0.60,
        byzantine_tolerance_f=1
    )
    st.session_state.optimizer = MultiObjectiveOptimizer(
        weights=st.session_state.weights,
        constraints=st.session_state.constraints
    )
    model_weight_path = str(ROOT_DIR / "models" / "drl_consensus_agent.pt")
    st.session_state.drl_selector = DRLCommitteeSelector(
        model_path=model_weight_path if os.path.exists(model_weight_path) else None,
        node_count=st.session_state.fleet_size,
        constraints=st.session_state.constraints
    )
    st.session_state.current_epoch = 0
    st.session_state.current_block = 0
    st.session_state.blocks_history = []
    st.session_state.energy_history_adaptive = []
    st.session_state.energy_history_pbft = []
    st.session_state.cumulative_adaptive_j = 0.0
    st.session_state.cumulative_pbft_j = 0.0
    st.session_state.battery_history = []
    st.session_state.epoch_history = []
    st.session_state.latest_telemetry = {}
    st.session_state.initialized = True


# ---------------------------------------------------------------------------
# Core epoch execution (consensus logic preserved from the original pipeline)
# ---------------------------------------------------------------------------
def execute_epoch():
    st.session_state.current_epoch += 1
    st.session_state.current_block += 1
    epoch = st.session_state.current_epoch
    block = st.session_state.current_block

    engine_mode = st.session_state.get("engine_mode", "Deep Reinforcement Learning (PPO Agent)")
    is_drl = "Reinforcement" in engine_mode
    drain_speed = st.session_state.get("drain_speed", 2500)

    # 1. Telemetry Ingestion & Adversarial Tampering
    raw_telemetry = st.session_state.simulator.gather_telemetry()
    tampered_telemetry = [
        st.session_state.adversary.tamper_telemetry(st.session_state.simulator.nodes[t.node_id], t)
        for t in raw_telemetry
    ]

    # 2. Physics-Informed Defense Sanitization
    telemetry = st.session_state.defense.verify_telemetry_physics(epoch, tampered_telemetry)
    st.session_state.latest_telemetry = {t.node_id: t for t in telemetry}

    # 3. AI Election (with fatigue & dynamic rotation)
    if is_drl:
        directive = st.session_state.drl_selector.select_committee(epoch_id=epoch, telemetry=telemetry)
        engine_label = "Deep RL (PPO Agent)"
    else:
        directive = st.session_state.optimizer.select_committee(epoch_id=epoch, telemetry=telemetry)
        engine_label = "Heuristic MCDM Optimizer"
    st.session_state.simulator.apply_committee_directive(directive)
    st.session_state.defense.record_epoch_assignments(epoch, directive, telemetry)

    # 4. Check for Byzantine Equivocation Attacks
    for node_id, attack in list(st.session_state.adversary.active_attacks.items()):
        if attack == AttackType.BYZANTINE_EQUIVOCATION:
            node = st.session_state.simulator.get_node(node_id)
            if node:
                proof = st.session_state.adversary.generate_equivocation(node, epoch, block)
                is_valid, alert = st.session_state.defense.verify_and_slash_equivocation(proof)
                if is_valid:
                    node.reputation = 0.0
                    node.is_validator = False
                    node.is_leader = False

    # 5. Block Proposal & Signatures (with Silent Dropping simulation)
    raw_hash = hashlib.sha256(f"epoch_{epoch}_block_{block}".encode()).hexdigest()
    valid_signatures = []
    for addr in directive.members:
        node = st.session_state.simulator.get_node_by_address(addr)
        if not node:
            continue
        if node.address.lower() in st.session_state.defense.slashed_addresses:
            continue
        if st.session_state.adversary.get_attack_for_node(node.node_id) == AttackType.SILENT_DROPPING:
            continue
        sig = node.sign_hash(raw_hash)
        valid_signatures.append(sig)

    # 6. Sybil Detection
    for attack in st.session_state.adversary.active_attacks.values():
        if attack == AttackType.SYBIL_INFILTRATION:
            sybil_vote = st.session_state.adversary.generate_sybil_vote(epoch, raw_hash)
            registered_set = {n.address for n in st.session_state.simulator.nodes.values()}
            st.session_state.defense.filter_sybil_and_invalid_votes(
                epoch, [sybil_vote], registered_set, set(directive.members)
            )

    is_quorum_achieved = len(valid_signatures) >= directive.quorum_threshold

    # 7. Energy Model Discharge (Heinzelman)
    model = HeinzelmanEnergyModel(hardware=HardwarePreset.ESP32)
    adaptive_round_j = 0.0
    for node in st.session_state.simulator.nodes.values():
        e_node = node.discharge_round_energy(
            directive.committee_size,
            drain_multiplier=drain_speed
        )
        adaptive_round_j += e_node

    # Baseline Static PBFT (all N nodes validate every single round)
    pbft_round_j = 0.0
    for _ in range(st.session_state.fleet_size):
        # In PBFT, leader transmits to all N-1, all N-1 nodes verify and broadcast (N^2)
        pbft_round_j += model.calculate_round_energy(
            is_validator=True,
            is_leader=False,
            committee_size=st.session_state.fleet_size
        ) * drain_speed

    st.session_state.cumulative_adaptive_j += adaptive_round_j
    st.session_state.cumulative_pbft_j += pbft_round_j
    st.session_state.energy_history_adaptive.append(st.session_state.cumulative_adaptive_j)
    st.session_state.energy_history_pbft.append(st.session_state.cumulative_pbft_j)

    # Per-node battery trajectory snapshot (after discharge)
    for node in st.session_state.simulator.nodes.values():
        st.session_state.battery_history.append(
            {"Epoch": epoch, "Node": node.node_id, "Battery %": round(node.battery_pct, 2)}
        )

    # Per-epoch metrics history for the analytics charts
    st.session_state.epoch_history.append({
        "Epoch": epoch,
        "Committee K": directive.committee_size,
        "Quorum": directive.quorum_threshold,
        "Signatures": len(valid_signatures),
        "Avg Battery %": round(directive.metadata.get("avg_battery_pct", 0.0), 1),
        "Utility": round(directive.metadata.get("utility", 0.0), 3),
    })

    leader_node = st.session_state.simulator.get_node_by_address(directive.leader_address)
    st.session_state.blocks_history.insert(0, {
        "Epoch": epoch,
        "Block #": block,
        "AI Engine": engine_label,
        "Leader": leader_node.node_id if leader_node else "Unknown",
        "Committee Size (K)": directive.committee_size,
        "Quorum Threshold": directive.quorum_threshold,
        "Signatures": len(valid_signatures),
        "Quorum Achieved": "YES" if is_quorum_achieved else "MISSED",
        "Avg Committee Batt %": round(directive.metadata.get("avg_battery_pct", 0.0), 1),
        "Utility Score": round(directive.metadata.get("utility", 0.0), 3),
        "Status": "COMMITTED" if is_quorum_achieved else "FAILED"
    })

    # Trim long-running histories
    if len(st.session_state.blocks_history) > MAX_HISTORY:
        st.session_state.blocks_history = st.session_state.blocks_history[:MAX_HISTORY]
    if len(st.session_state.energy_history_adaptive) > MAX_HISTORY:
        st.session_state.energy_history_adaptive = st.session_state.energy_history_adaptive[-MAX_HISTORY:]
        st.session_state.energy_history_pbft = st.session_state.energy_history_pbft[-MAX_HISTORY:]
    if len(st.session_state.battery_history) > MAX_HISTORY * st.session_state.fleet_size:
        st.session_state.battery_history = st.session_state.battery_history[-MAX_HISTORY * st.session_state.fleet_size:]
    if len(st.session_state.epoch_history) > MAX_HISTORY:
        st.session_state.epoch_history = st.session_state.epoch_history[-MAX_HISTORY:]


# ---------------------------------------------------------------------------
# Charts (Altair, interactive)
# ---------------------------------------------------------------------------
def chart_energy():
    hist_a = st.session_state.energy_history_adaptive
    hist_p = st.session_state.energy_history_pbft
    if not hist_a:
        st.markdown(
            '<div class="empty-panel">Run consensus epochs to plot the comparative energy trajectory.</div>',
            unsafe_allow_html=True,
        )
        return
    df = pd.DataFrame({
        "Epoch": list(range(1, len(hist_a) + 1)),
        "Static PBFT (all N nodes)": hist_p,
        "AI Adaptive Consensus": hist_a,
    }).melt(id_vars="Epoch", var_name="Protocol", value_name="Cumulative Energy (J)")
    c = (
        alt.Chart(df)
        .mark_line(point=True, strokeWidth=2.4)
        .encode(
            x=alt.X("Epoch:Q", title="Epoch", axis=alt.Axis(grid=False)),
            y=alt.Y("Cumulative Energy (J):Q", title="Cumulative joules dissipated"),
            color=alt.Color(
                "Protocol:N",
                scale=alt.Scale(
                    domain=["Static PBFT (all N nodes)", "AI Adaptive Consensus"],
                    range=["#e5484d", "#2fbf71"],
                ),
                legend=alt.Legend(title=None, orient="top-left"),
            ),
            tooltip=[
                alt.Tooltip("Epoch:Q"),
                alt.Tooltip("Protocol:N"),
                alt.Tooltip("Cumulative Energy (J):Q", format=",.0f"),
            ],
        )
        .properties(height=300)
        .interactive()
    )
    st.altair_chart(_finalize(c), width="stretch")


def chart_battery_decay():
    if not st.session_state.battery_history:
        st.markdown(
            '<div class="empty-panel">Run consensus epochs to plot per-node battery decay.</div>',
            unsafe_allow_html=True,
        )
        return
    df = pd.DataFrame(st.session_state.battery_history)
    c = (
        alt.Chart(df)
        .mark_line(strokeWidth=1.6)
        .encode(
            x=alt.X("Epoch:Q", title="Epoch"),
            y=alt.Y("Battery %:Q", title="Battery remaining (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("Node:N", legend=alt.Legend(columns=2, symbolLimit=0, title=None)),
            tooltip=[
                alt.Tooltip("Node:N"),
                alt.Tooltip("Epoch:Q"),
                alt.Tooltip("Battery %:Q", format=",.1f"),
            ],
        )
        .properties(height=320)
        .interactive()
    )
    st.altair_chart(_finalize(c), width="stretch")


def chart_committee():
    if not st.session_state.epoch_history:
        st.markdown(
            '<div class="empty-panel">Run consensus epochs to plot committee sizing.</div>',
            unsafe_allow_html=True,
        )
        return
    df = pd.DataFrame(st.session_state.epoch_history)
    x = alt.X(
        "Epoch:N",
        title="Epoch",
        axis=alt.Axis(labelAngle=0, labelExpr="parseInt(datum.value) % 5 === 0 ? datum.label : ''"),
    )
    bars = (
        alt.Chart(df)
        .mark_bar(color="#4ea1d3")
        .encode(
            x=x,
            y=alt.Y("Committee K:Q", title="Committee size (K)"),
            tooltip=[
                alt.Tooltip("Epoch:Q"),
                alt.Tooltip("Committee K:Q"),
                alt.Tooltip("Quorum:Q"),
                alt.Tooltip("Signatures:Q"),
            ],
        )
    )
    rule = (
        alt.Chart(df)
        .mark_rule(color="#e0a63c", strokeWidth=1.5, strokeDash=[5, 4])
        .encode(y=alt.Y("Quorum:Q"), tooltip=[alt.Tooltip("Quorum:Q", title="Quorum threshold")])
    )
    c = (bars + rule).properties(height=280)
    st.altair_chart(_finalize(c), width="stretch")


def chart_fleet_health():
    if not st.session_state.epoch_history:
        st.markdown(
            '<div class="empty-panel">Run consensus epochs to plot fleet health metrics.</div>',
            unsafe_allow_html=True,
        )
        return
    df = pd.DataFrame(st.session_state.epoch_history)
    l_battery = (
        alt.Chart(df)
        .mark_line(color="#4ea1d3", strokeWidth=2)
        .encode(
            x=alt.X("Epoch:Q", title="Epoch"),
            y=alt.Y("Avg Battery %:Q", title="Avg battery (%)", scale=alt.Scale(domain=[0, 100])),
            tooltip=[alt.Tooltip("Avg Battery %:Q", format=",.1f")],
        )
    )
    l_utility = (
        alt.Chart(df)
        .mark_line(color="#2fbf71", strokeWidth=2)
        .encode(
            x=alt.X("Epoch:Q", title="Epoch"),
            y=alt.Y("Utility:Q", title="Utility score", scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("Utility:Q", format=",.3f")],
        )
    )
    c = alt.layer(l_battery, l_utility).resolve_scale(y="independent").properties(height=280)
    st.altair_chart(_finalize(c), width="stretch")


def chart_signatures():
    if not st.session_state.epoch_history:
        st.markdown(
            '<div class="empty-panel">Run consensus epochs to plot quorum verification.</div>',
            unsafe_allow_html=True,
        )
        return
    df = pd.DataFrame(st.session_state.epoch_history).tail(30)
    x = alt.X("Epoch:N", title="Epoch", axis=alt.Axis(labelAngle=0))
    bars = (
        alt.Chart(df)
        .mark_bar(color="#2fbf71")
        .encode(
            x=x,
            y=alt.Y("Signatures:Q", title="Signatures collected"),
            tooltip=[
                alt.Tooltip("Epoch:Q"),
                alt.Tooltip("Signatures:Q"),
                alt.Tooltip("Quorum:Q"),
            ],
        )
    )
    rule = (
        alt.Chart(df)
        .mark_rule(color="#e0a63c", strokeWidth=1.5, strokeDash=[5, 4])
        .encode(y=alt.Y("Quorum:Q"), tooltip=[alt.Tooltip("Quorum:Q", title="Quorum threshold")])
    )
    c = (bars + rule).properties(height=260)
    st.altair_chart(_finalize(c), width="stretch")


# ---------------------------------------------------------------------------
# Fleet grid & registry table
# ---------------------------------------------------------------------------
def render_fleet_grid():
    cards_html = []
    for node_id, node in st.session_state.simulator.nodes.items():
        label, pill_cls, card_cls = node_role(node)
        tel = st.session_state.latest_telemetry.get(node_id)
        latency = tel.latency_ms if tel else node.base_latency_ms
        cards_html.append(
            f'<div class="node-card {card_cls}">'
            f'<div class="node-head"><span class="node-id">{node_id}</span>'
            f'<span class="pill {pill_cls}">{label}</span></div>'
            f'<div class="battery-track">'
            f'<div class="battery-fill" style="width:{max(0.0, min(100.0, node.battery_pct)):.1f}%;'
            f' background:{battery_color(node.battery_pct)}"></div></div>'
            f'<div class="node-stats"><span>BAT <b>{node.battery_pct:.1f}%</b></span>'
            f'<span>LAT <b>{latency:.1f}ms</b></span>'
            f'<span>REP <b>{node.reputation:.2f}</b></span></div>'
            f'</div>'
        )
    st.markdown(f'<div class="fleet-grid">{"".join(cards_html)}</div>', unsafe_allow_html=True)


def render_fleet_table():
    rows = []
    for node_id, node in st.session_state.simulator.nodes.items():
        role, _, _ = node_role(node)
        tel = st.session_state.latest_telemetry.get(node_id)
        rows.append({
            "Node": node_id,
            "Role": role,
            "Battery %": round(node.battery_pct, 1),
            "Latency (ms)": round(tel.latency_ms if tel else node.base_latency_ms, 1),
            "Reputation": round(node.reputation, 2),
            "Energy (J)": round(node.total_energy_consumed_joules, 1),
            "Blocks Signed": int(node.blocks_signed),
        })
    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        height=320,
        hide_index=True,
        column_config={
            "Battery %": st.column_config.ProgressColumn(
                "Battery %", min_value=0, max_value=100, format="%.1f%%"
            ),
            "Reputation": st.column_config.ProgressColumn(
                "Reputation", min_value=0, max_value=1, format="%.2f"
            ),
        },
    )


# ---------------------------------------------------------------------------
# Security audit
# ---------------------------------------------------------------------------
def render_alert_cards():
    defense = st.session_state.defense
    severity_map = {
        "CRITICAL": ("pill-slashed", "sev-critical"),
        "HIGH": ("pill-quarantine", "sev-high"),
        "WARNING": ("pill-validator", "sev-warning"),
    }
    cards = []
    for alert in reversed(defense.alerts_log):
        pill_cls, sev_cls = severity_map.get(alert.severity, ("pill-idle", "sev-warning"))
        ts = time.strftime("%H:%M:%S", time.localtime(alert.timestamp))
        addr = alert.node_address[:12] + "..." if len(alert.node_address) > 12 else alert.node_address
        cards.append(
            f'<div class="alert-card {sev_cls}">'
            f'<div class="alert-top"><span class="pill {pill_cls}">{alert.severity}</span>'
            f'<div class="alert-meta"><span>EPOCH {alert.epoch_id}</span>'
            f'<span>{alert.node_id}</span><span>{addr}</span><span>{ts}</span></div></div>'
            f'<div class="alert-attack">{alert.attack_type.value}</div>'
            f'<div class="alert-desc">{alert.description}</div>'
            f'<div class="alert-action"><b>Defense action</b> {alert.action_taken}</div>'
            f'</div>'
        )
    st.markdown("".join(cards), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------
def render_latest_block_card():
    latest = st.session_state.blocks_history[0]
    status_pill = "pill-ok" if latest["Status"] == "COMMITTED" else "pill-fail"
    st.markdown(
        f'<div class="block-card">'
        f'<div class="block-top"><span class="block-number">BLOCK #{latest["Block #"]}</span>'
        f'<span class="pill {status_pill}">{latest["Status"]}</span></div>'
        f'<div class="block-grid">'
        f'<div class="block-cell"><div class="k">Epoch</div><div class="v">#{latest["Epoch"]}</div></div>'
        f'<div class="block-cell"><div class="k">Leader</div><div class="v">{latest["Leader"]}</div></div>'
        f'<div class="block-cell"><div class="k">Engine</div><div class="v">{latest["AI Engine"]}</div></div>'
        f'<div class="block-cell"><div class="k">Committee</div><div class="v">K = {latest["Committee Size (K)"]}</div></div>'
        f'<div class="block-cell"><div class="k">Quorum</div><div class="v">{latest["Signatures"]} / {latest["Quorum Threshold"]}</div></div>'
        f'<div class="block-cell"><div class="k">Utility</div><div class="v">{latest["Utility Score"]}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def render_epoch_strip():
    blocks = st.session_state.blocks_history
    chips = []
    for b in reversed(blocks[-30:]):  # oldest to newest
        cls = "chip" if b["Status"] == "COMMITTED" else "chip fail"
        chips.append(
            f'<div class="{cls}" title="Epoch {b["Epoch"]}: K={b["Committee Size (K)"]}, '
            f'signatures {b["Signatures"]}/{b["Quorum Threshold"]}, {b["Status"]}">{b["Epoch"]}</div>'
        )
    st.markdown(
        f'<div class="epoch-strip">{"".join(chips)}</div>'
        f'<div class="strip-caption">Most recent epochs (oldest to newest). Hover a chip for details.</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Dashboard body (rendered statically, or inside the live fragment)
# ---------------------------------------------------------------------------
def render_metric_banner():
    latest = st.session_state.blocks_history[0] if st.session_state.blocks_history else None
    alive_nodes = sum(1 for n in st.session_state.simulator.nodes.values() if n.is_alive)
    saved_pct = 0.0
    if st.session_state.cumulative_pbft_j > 0:
        saved_pct = (
            (st.session_state.cumulative_pbft_j - st.session_state.cumulative_adaptive_j)
            / st.session_state.cumulative_pbft_j
        ) * 100.0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Epoch / Block", f"#{st.session_state.current_epoch}")
    m2.metric("Active Committee (K)", f"{latest['Committee Size (K)'] if latest else 'N/A'}")
    m3.metric("Quorum Threshold", f"{latest['Quorum Threshold'] if latest else 'N/A'}")
    m4.metric("Alive Nodes", f"{alive_nodes} / {st.session_state.fleet_size}")
    m5.metric(
        "Energy Saved vs PBFT",
        f"{saved_pct:.1f}%",
        delta=f"{st.session_state.cumulative_adaptive_j:,.1f} J dissipated",
    )


def render_fleet_tab():
    section_head(
        "Fleet Telemetry & Role Rotation",
        "Telemetry shown after physics-informed defense sanitization",
    )
    render_fleet_grid()
    section_head("Fleet Registry", "Sortable telemetry table; click column headers to sort")
    render_fleet_table()
    section_head("Per-Node Battery Decay", "Zoom and pan; hover any line for exact values")
    chart_battery_decay()


def render_energy_tab():
    section_head(
        "Energy Depletion: Adaptive vs Static PBFT",
        "Baseline: all 14 nodes validate every round with O(N^2) messages",
    )
    chart_energy()
    col_left, col_right = st.columns(2)
    with col_left:
        section_head("Committee Sizing per Epoch", "Bars: committee size K. Dashed line: quorum threshold")
        chart_committee()
    with col_right:
        section_head("Fleet Health Trajectory", "Blue: avg committee battery. Green: utility score")
        chart_fleet_health()


def render_security_tab():
    defense = st.session_state.defense
    f = st.session_state.constraints.byzantine_tolerance_f
    integrity_ok = len(defense.slashed_addresses) <= f

    c1, c2, c3 = st.columns(3)
    c1.markdown(
        '<div class="stat-tile"><div class="k">Incidents Intercepted</div>'
        f'<div class="v">{len(defense.alerts_log)}</div></div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        '<div class="stat-tile"><div class="k">Slashed & Quarantined</div>'
        f'<div class="v">{len(defense.slashed_addresses)}</div></div>',
        unsafe_allow_html=True,
    )
    integrity_pill = (
        '<span class="pill pill-ok">ENFORCED</span>' if integrity_ok else '<span class="pill pill-fail">AT RISK</span>'
    )
    c3.markdown(
        f'<div class="stat-tile"><div class="k">Network Byzantine Integrity</div>'
        f'<div class="v">{integrity_pill}</div></div>',
        unsafe_allow_html=True,
    )

    section_head("Defense & Slashing Audit Trail", "Newest incidents first")
    if defense.alerts_log:
        render_alert_cards()
        audit_rows = [
            {
                "Epoch": a.epoch_id,
                "Severity": a.severity,
                "Attack Vector": a.attack_type.value,
                "Target Node": a.node_id,
                "Target Address": a.node_address,
                "Detection": a.description,
                "Defense Action": a.action_taken,
            }
            for a in reversed(defense.alerts_log)
        ]
        csv = pd.DataFrame(audit_rows).to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Audit Log (CSV)",
            data=csv,
            file_name="security_audit_log.csv",
            mime="text/csv",
        )
    else:
        st.markdown(
            '<div class="empty-panel"><span class="pill pill-ok">SECURE</span><br>'
            "No adversarial incidents or anomalies detected. Fleet operating in honest mode.</div>",
            unsafe_allow_html=True,
        )


def render_ledger_tab():
    if not st.session_state.blocks_history:
        st.markdown(
            '<div class="empty-panel">No blocks committed yet. Run consensus epochs to settle blocks.</div>',
            unsafe_allow_html=True,
        )
        return

    section_head("Latest Settled Block")
    render_latest_block_card()
    section_head("Epoch Timeline", "Green: quorum achieved and block committed. Red: failed")
    render_epoch_strip()
    section_head("Quorum Verification", "Bars: signatures collected. Dashed line: quorum threshold")
    chart_signatures()
    section_head("Block Settlement Ledger", "Sortable; newest blocks first")
    st.dataframe(pd.DataFrame(st.session_state.blocks_history), width="stretch", height=340, hide_index=True)


def render_dashboard_body():
    render_metric_banner()
    tab_fleet, tab_energy, tab_security, tab_ledger = st.tabs(
        ["Fleet Monitor", "Energy & Benchmark", "Security Audit", "Block Ledger"]
    )
    with tab_fleet:
        render_fleet_tab()
    with tab_energy:
        render_energy_tab()
    with tab_security:
        render_security_tab()
    with tab_ledger:
        render_ledger_tab()


@st.fragment(run_every="2s")
def live_engine_fragment():
    """Auto-executes one consensus epoch every 2 seconds and refreshes the full body."""
    execute_epoch()
    render_dashboard_body()


# ---------------------------------------------------------------------------
# App flow
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Adaptive IoT Consensus Dashboard", layout="wide")
load_css()

# Initialize Session State if not present
if not st.session_state.get("initialized", False):
    init_or_reset_simulation()

# ------------------------------ Sidebar ------------------------------
with st.sidebar:
    st.markdown('<div class="side-title">Consensus Control Console</div>', unsafe_allow_html=True)

    if st.button("Reset Fleet & Ledger", width="stretch"):
        init_or_reset_simulation()
        st.toast("Fleet, batteries, and ledger reset")
        st.rerun()

    st.markdown('<div class="side-label">Optimization Engine</div>', unsafe_allow_html=True)
    engine_mode = st.radio(
        "Committee selection model",
        ["Deep Reinforcement Learning (PPO Agent)", "Heuristic MCDM Optimizer"],
        index=0,
        key="engine_mode",
        label_visibility="collapsed",
    )
    is_drl = "Reinforcement" in engine_mode

    if is_drl:
        st.sidebar.caption("Neural engine active: Actor-Critic PPO policy (models/drl_consensus_agent.pt)")
    else:
        st.sidebar.caption("Heuristic engine active: multi-criteria decision making")
        st.sidebar.markdown("**Objective Function Weights**")
        w_sec = st.sidebar.slider("Security (w1)", 0.0, 1.0, 0.35, 0.05)
        w_eng = st.sidebar.slider("Residual Battery (w2)", 0.0, 1.0, 0.45, 0.05)
        w_lat = st.sidebar.slider("Low Latency (w3)", 0.0, 1.0, 0.20, 0.05)
        st.session_state.weights = ObjectiveWeights(w_security=w_sec, w_energy=w_eng, w_latency=w_lat)
        st.session_state.optimizer.weights = st.session_state.weights

    st.markdown('<div class="side-label">Simulation Physics</div>', unsafe_allow_html=True)
    st.slider(
        "Discharge Acceleration",
        min_value=100,
        max_value=10000,
        value=2500,
        step=100,
        key="drain_speed",
        help="Accelerates simulation physical discharge so battery bars visibly deplete across 10-20 rounds",
    )

    st.markdown('<div class="side-label">Adversarial Injection</div>', unsafe_allow_html=True)
    target_node_id = st.selectbox(
        "Attack Target Node", list(st.session_state.simulator.nodes.keys())
    )

    col_att1, col_att2 = st.columns(2)
    with col_att1:
        if st.button("Drain to 10%", width="stretch"):
            node = st.session_state.simulator.get_node(target_node_id)
            if node:
                node.force_drain_battery(10.0)
                st.toast(f"{target_node_id} battery forced to 10%")
    with col_att2:
        if st.button("Spoof Telemetry", width="stretch"):
            st.session_state.adversary.arm_attack(target_node_id, AttackType.TELEMETRY_SPOOFING)
            st.toast(f"Telemetry spoofing armed on {target_node_id}")

    col_att3, col_att4 = st.columns(2)
    with col_att3:
        if st.button("Double-Sign Attack", width="stretch"):
            st.session_state.adversary.arm_attack(target_node_id, AttackType.BYZANTINE_EQUIVOCATION)
            st.toast(f"Double-signing equivocation armed on {target_node_id}")
    with col_att4:
        if st.button("Inject Sybil Vote", width="stretch"):
            st.session_state.adversary.arm_attack("Rogue", AttackType.SYBIL_INFILTRATION)
            st.toast("Rogue Sybil vote injection armed")

    col_att5, col_att6 = st.columns(2)
    with col_att5:
        if st.button("Silent Drop Attack", width="stretch"):
            st.session_state.adversary.arm_attack(target_node_id, AttackType.SILENT_DROPPING)
            st.toast(f"Silent dropping armed on {target_node_id}")
    with col_att6:
        if st.button("Clear All Attacks", width="stretch"):
            st.session_state.adversary.clear_all_attacks()
            st.toast("All armed attacks cleared")

    if st.session_state.adversary.active_attacks:
        st.markdown('<div class="side-label">Armed Attacks</div>', unsafe_allow_html=True)
        for node_id_key, attack_type in list(st.session_state.adversary.active_attacks.items()):
            row_a, row_b = st.columns([0.62, 0.38])
            row_a.markdown(
                f'<div class="node-head"><span class="node-id">{node_id_key}</span></div>'
                f'<span class="pill pill-attack">{ATTACK_SHORT.get(attack_type, attack_type.name)}</span>',
                unsafe_allow_html=True,
            )
            if row_b.button("Disarm", key=f"disarm_{node_id_key}", width="stretch"):
                st.session_state.adversary.disarm_attack(node_id_key)
                st.toast(f"Attack disarmed on {node_id_key}")

    st.markdown(
        '<div class="side-note">BFT invariant: <b>K &ge; 3f + 1</b> (f = 1)<br>'
        "Quorum: <b>floor(2/3 &middot; K) + 1</b><br>"
        "Radio physics: Heinzelman first-order model (ESP32)</div>",
        unsafe_allow_html=True,
    )

# ------------------------------ Header ------------------------------
st.markdown(
    '<div class="app-header">'
    '<div><div class="app-title">Adaptive Consensus Control</div>'
    '<div class="app-sub">AI-driven committee selection for energy-efficient blockchain IoT networks</div></div>'
    '<div class="app-bft">BFT invariant: <b>K &ge; 3f + 1</b><br>Quorum: <b>floor(2/3 &middot; K) + 1</b><br>'
    'Defense: <b>physics-informed sanitizer + ECDSA slashing</b></div>'
    '</div>',
    unsafe_allow_html=True,
)

# ------------------------------ Toolbar ------------------------------
live_mode = st.session_state.get("live_mode", False)
run_one = False
run_five = False

if not live_mode:
    tcol1, tcol2, tcol3 = st.columns([1.1, 1.4, 1.0])
    with tcol1:
        run_one = st.button("Run 1 Epoch", type="primary", width="stretch")
    with tcol2:
        run_five = st.button("Auto-Run 5 Epochs", width="stretch")
    with tcol3:
        st.toggle("Live Mode", key="live_mode")
else:
    tcol1, tcol2 = st.columns([1.0, 3.0])
    with tcol1:
        st.toggle("Live Mode", key="live_mode")
    with tcol2:
        st.markdown(
            '<div class="live-strip"><span class="live-dot"></span>'
            '<span class="live-label">LIVE</span>'
            '<span class="live-text">auto-executing one consensus epoch every 2 seconds</span></div>',
            unsafe_allow_html=True,
        )

# ------------------------------ Execution ------------------------------
if run_one:
    execute_epoch()
if run_five:
    for _ in range(5):
        execute_epoch()

if st.session_state.get("live_mode", False):
    live_engine_fragment()
else:
    render_dashboard_body()
