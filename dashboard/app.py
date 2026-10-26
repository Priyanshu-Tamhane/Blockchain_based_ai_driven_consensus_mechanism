"""
Real-Time Interactive Dashboard for Adaptive IoT Blockchain Consensus.
Mid-Semester Review Visual Presentation Interface.
Displays:
  - Fleet Telemetry & Battery Gauges
  - Dynamic Committee Selection & Rotation Highlighting
  - Real-Time Quorum Signature Verification
  - Cumulative Energy Savings vs. Static PBFT Baseline
  - Fault Injection & Stress Testing Controls
"""
import sys
import os
from pathlib import Path

# Ensure project root is in Python sys.path regardless of where streamlit is launched from
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import numpy as np
import time
import hashlib
import matplotlib.pyplot as plt

from simulator.fleet_simulator import IoTFleetSimulator
from simulator.energy_model import HeinzelmanEnergyModel, HardwarePreset
from ai_engine.objective import MultiObjectiveOptimizer, ObjectiveWeights, SystemConstraints


st.set_page_config(
    page_title="AI-Driven Adaptive IoT Consensus Dashboard",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ AI-Driven Adaptive Consensus Mechanism for IoT Networks")
st.markdown("### Energy-Aware Dynamic Committee Selection & Quorum Settlement Layer")

def init_or_reset_simulation():
    """Initializes or completely resets the fleet simulation state."""
    st.session_state.fleet_size = 14
    st.session_state.simulator = IoTFleetSimulator(node_count=st.session_state.fleet_size, seed=42)
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
    st.session_state.current_epoch = 0
    st.session_state.current_block = 0
    st.session_state.blocks_history = []
    st.session_state.energy_history_adaptive = []
    st.session_state.energy_history_pbft = []
    st.session_state.cumulative_adaptive_j = 0.0
    st.session_state.cumulative_pbft_j = 0.0
    st.session_state.initialized = True

# Initialize Session State if not present
if not st.session_state.get("initialized", False):
    init_or_reset_simulation()

# Sidebar Controls
st.sidebar.header("⚙️ Consensus & Fleet Controls")

if st.sidebar.button("🔄 Reset Fleet & Ledger"):
    init_or_reset_simulation()
    st.sidebar.success("Fleet, batteries & ledger reset successfully!")
    st.rerun()

st.sidebar.subheader("Objective Function Weights")
w_sec = st.sidebar.slider("Security (w1)", 0.0, 1.0, 0.35, 0.05)
w_eng = st.sidebar.slider("Residual Battery (w2)", 0.0, 1.0, 0.45, 0.05)
w_lat = st.sidebar.slider("Low Latency (w3)", 0.0, 1.0, 0.20, 0.05)

st.session_state.weights = ObjectiveWeights(w_security=w_sec, w_energy=w_eng, w_latency=w_lat)
st.session_state.optimizer.weights = st.session_state.weights

st.sidebar.subheader("🔋 Simulation Physics & Drain Rate")
drain_speed = st.sidebar.slider(
    "Discharge Acceleration",
    min_value=100,
    max_value=10000,
    value=2500,
    step=100,
    help="Accelerates simulation physical discharge so battery bars visibly deplete across 10-20 rounds (includes 5000 and up to 10000)"
)

st.sidebar.subheader("🚨 Adversarial & Stress Injection")
target_node_id = st.sidebar.selectbox("Select Node to Drain:", list(st.session_state.simulator.nodes.keys()))
if st.sidebar.button(f"⚡ Force Drain {target_node_id} to 10% (Critical)"):
    node = st.session_state.simulator.get_node(target_node_id)
    if node:
        node.force_drain_battery(10.0)
        st.sidebar.warning(f"{target_node_id} battery dropped to 10.0% (< 15% threshold)!")

def execute_epoch():
    st.session_state.current_epoch += 1
    st.session_state.current_block += 1
    epoch = st.session_state.current_epoch
    block = st.session_state.current_block

    # 1. Telemetry
    telemetry = st.session_state.simulator.gather_telemetry()

    # 2. AI Election (with fatigue & dynamic rotation)
    directive = st.session_state.optimizer.select_committee(epoch_id=epoch, telemetry=telemetry)
    st.session_state.simulator.apply_committee_directive(directive)

    # 3. Block Proposal & Signatures
    raw_hash = hashlib.sha256(f"epoch_{epoch}_block_{block}".encode()).hexdigest()
    signatures = st.session_state.simulator.collect_committee_signatures(directive, raw_hash)

    # 4. Energy Model Discharge (Heinzelman)
    model = HeinzelmanEnergyModel(hardware=HardwarePreset.ESP32)
    # Adaptive energy this round
    adaptive_round_j = 0.0
    for node in st.session_state.simulator.nodes.values():
        e_node = node.discharge_round_energy(
            directive.committee_size,
            drain_multiplier=drain_speed
        )
        adaptive_round_j += e_node

    # Baseline Static PBFT (All N nodes validate every single round)
    pbft_round_j = 0.0
    for _ in range(st.session_state.fleet_size):
        # In PBFT, leader transmits to all N-1, all N-1 nodes verify and broadcast to all others (N^2)
        pbft_round_j += model.calculate_round_energy(
            is_validator=True,
            is_leader=False,
            committee_size=st.session_state.fleet_size
        ) * drain_speed

    st.session_state.cumulative_adaptive_j += adaptive_round_j
    st.session_state.cumulative_pbft_j += pbft_round_j

    st.session_state.energy_history_adaptive.append(st.session_state.cumulative_adaptive_j)
    st.session_state.energy_history_pbft.append(st.session_state.cumulative_pbft_j)

    leader_node = st.session_state.simulator.get_node_by_address(directive.leader_address)
    st.session_state.blocks_history.insert(0, {
        "Epoch": epoch,
        "Block #": block,
        "Leader": leader_node.node_id if leader_node else "Unknown",
        "Committee Size (K)": directive.committee_size,
        "Quorum Threshold": directive.quorum_threshold,
        "Signatures": len(signatures),
        "Avg Committee Batt %": round(directive.metadata.get("avg_battery_pct", 0.0), 1),
        "Utility Score": round(directive.metadata.get("utility", 0.0), 3),
        "Status": "✅ COMMITTED"
    })

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    if st.button("▶️ Execute 1 Consensus Epoch", use_container_width=True):
        execute_epoch()
with col_btn2:
    if st.button("⏩ Auto-Run 5 Epochs", use_container_width=True):
        for _ in range(5):
            execute_epoch()

# Top Metric Banner
latest_block = st.session_state.blocks_history[0] if st.session_state.blocks_history else None
alive_nodes = sum(1 for n in st.session_state.simulator.nodes.values() if n.is_alive)
saved_pct = 0.0
if st.session_state.cumulative_pbft_j > 0:
    saved_pct = ((st.session_state.cumulative_pbft_j - st.session_state.cumulative_adaptive_j) / st.session_state.cumulative_pbft_j) * 100.0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Current Epoch / Block", f"#{st.session_state.current_epoch}")
m2.metric("Active Committee (K)", f"{latest_block['Committee Size (K)'] if latest_block else 'N/A'}")
m3.metric("Quorum Threshold", f"{latest_block['Quorum Threshold'] if latest_block else 'N/A'}")
m4.metric("Alive Nodes", f"{alive_nodes} / {st.session_state.fleet_size}")
m5.metric("Cumulative Energy Saved", f"{saved_pct:.1f}%", delta=f"{st.session_state.cumulative_adaptive_j:.2f} J total")

st.divider()

# Fleet Telemetry Grid
st.subheader("📡 Real-Time IoT Fleet Telemetry & Role Rotation")
cols = st.columns(4)

for idx, (node_id, node) in enumerate(st.session_state.simulator.nodes.items()):
    col = cols[idx % 4]
    with col:
        # Determine visual badge
        if not node.is_alive:
            badge = "💀 DEAD"
            color = "#777777"
        elif node.is_leader:
            badge = "👑 ROUND LEADER"
            color = "#ffaa00"
        elif node.is_validator:
            badge = "🛡️ ACTIVE VALIDATOR"
            color = "#00bbff"
        elif node.battery_pct <= 15.0:
            badge = "⚠️ QUARANTINED (<15%)"
            color = "#ff4444"
        else:
            badge = "💤 IDLE SLEEP (CONSERVING)"
            color = "#00dd77"

        st.markdown(
            f"""
            <div style="border: 1px solid #333; border-radius: 8px; padding: 12px; margin-bottom: 12px; background-color: #111;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong>{node_id}</strong>
                    <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background-color: {color}; color: #000; font-weight: bold;">
                        {badge}
                    </span>
                </div>
                <div style="margin-top: 8px;">
                    <small>Battery: {node.battery_pct:.1f}%</small>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.progress(max(0.0, min(1.0, node.battery_pct / 100.0)))

st.divider()

# Energy Comparison Plot & Ledger
c_left, c_right = st.columns([1, 1])

with c_left:
    st.subheader("📊 Energy Depletion: Adaptive vs. Static PBFT")
    if len(st.session_state.energy_history_adaptive) > 0:
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.plot(st.session_state.energy_history_pbft, label="Static PBFT (All N Nodes)", color="#ff4444", linewidth=2, linestyle="--")
        ax.plot(st.session_state.energy_history_adaptive, label="AI Adaptive Consensus", color="#00dd77", linewidth=2.5)
        ax.set_xlabel("Epoch Round")
        ax.set_ylabel("Cumulative Joules Dissipated")
        ax.set_title("Fleet Energy Preservation Trajectory")
        ax.legend()
        ax.grid(True, linestyle=":", alpha=0.6)
        st.pyplot(fig)
    else:
        st.info("Execute consensus epochs to display energy comparative graph.")

with c_right:
    st.subheader("📜 Blockchain Settlement Ledger")
    if st.session_state.blocks_history:
        st.dataframe(pd.DataFrame(st.session_state.blocks_history), use_container_width=True, height=260)
    else:
        st.info("No blocks committed yet. Click 'Execute 1 Consensus Epoch' to start.")
