"""
Generates a comprehensive Word document (.docx) containing the complete project report,
mathematical formulations, architecture, implementation guide, experimental results,
10-slide presentation script, and viva defense Q&A.
"""
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn


def set_cell_background(cell, fill_hex):
    """Sets background shading of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets inner margins for table cells."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def create_document():
    doc = docx.Document()

    # Configure Margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Styles & Colors
    PRIMARY_COLOR = RGBColor(0x1F, 0x4E, 0x79)   # Deep Navy
    SECONDARY_COLOR = RGBColor(0x2E, 0x75, 0xB6) # Slate Blue
    TEXT_COLOR = RGBColor(0x26, 0x26, 0x26)      # Charcoal

    # Document Title Page
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(36)
    title_p.paragraph_format.space_after = Pt(12)
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run("AI-Driven Adaptive Consensus Mechanism for Energy-Efficient Blockchain IoT Networks")
    title_run.font.name = "Calibri"
    title_run.font.size = Pt(24)
    title_run.font.bold = True
    title_run.font.color.rgb = PRIMARY_COLOR

    subtitle_p = doc.add_paragraph()
    subtitle_p.paragraph_format.space_after = Pt(28)
    subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = subtitle_p.add_run("Comprehensive Technical Specification, Mid-Semester Review Report & Presentation Guide")
    sub_run.font.name = "Calibri"
    sub_run.font.size = Pt(13)
    sub_run.font.italic = True
    sub_run.font.color.rgb = SECONDARY_COLOR

    # Meta Table
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_data = [
        ("Domain:", "Blockchain, Internet of Things (IoT), Edge AI & Deep Reinforcement Learning"),
        ("Milestone:", "Final Project Report (Phases 1 through 6 Complete)"),
        ("Target System:", "Decoupled 3-Tier Architecture (EVM Settlement + DRL Off-Chain Controller)"),
        ("Date / Version:", "October 2026 / Version 2.0 (Full Empirical Benchmarking & Defense Verified)")
    ]
    for row_idx, (k, v) in enumerate(meta_data):
        row = meta_table.rows[row_idx]
        row.cells[0].paragraphs[0].add_run(k).bold = True
        row.cells[1].paragraphs[0].add_run(v)
        set_cell_background(row.cells[0], "F2F4F7")
        set_cell_background(row.cells[1], "FAFAFA")
        set_cell_margins(row.cells[0], 80, 80, 120, 120)
        set_cell_margins(row.cells[1], 80, 80, 120, 120)

    doc.add_page_break()

    # Helper function for Headings
    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(20)
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run(text)
        run.font.name = "Calibri"
        run.font.size = Pt(17)
        run.font.bold = True
        run.font.color.rgb = PRIMARY_COLOR
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text)
        run.font.name = "Calibri"
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = SECONDARY_COLOR
        return p

    def add_p(text, bold_prefix=""):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            p.add_run(bold_prefix).bold = True
        p.add_run(text)
        return p

    def add_bullet(text):
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        p.add_run(text)
        return p

    def add_callout(text, title="KEY RESEARCH TAKEAWAY"):
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.rows[0].cells[0]
        set_cell_background(cell, "EDF4F9")
        set_cell_margins(cell, 120, 120, 180, 180)
        p = cell.paragraphs[0]
        p.add_run(f"[{title}] ").bold = True
        p.add_run(text).italic = True
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # 1. Executive Summary
    add_h1("1. Executive Summary")
    add_p(
        "Integrating Internet of Things (IoT) devices with decentralized blockchain networks creates immutable auditability, "
        "tamper-proof compliance, and autonomous machine-to-machine (M2M) microeconomies. However, conventional blockchain "
        "consensus protocols are fundamentally incompatible with edge IoT devices due to acute battery depletion, radio-frequency "
        "packet storms, and static committee structures."
    )
    add_p(
        "This project introduces an intelligent, energy-aware adaptive consensus framework that dynamically scales and rotates "
        "consensus committees based on real-time device health metrics (battery percentage, link latency, and historical reputation). "
        "The architecture is decoupled into three tiers: a physics-based simulated IoT fleet, an off-chain edge AI controller, and "
        "a Solidity-based EVM settlement layer. For the mid-semester evaluation, Phase 1 (Problem Formulation), Phase 2 (Mathematical "
        "Modeling), and Phase 3 (Working Prototype & Streamlit Dashboard) have been fully developed and mathematically validated."
    )
    add_callout(
        "By dynamically rotating low-battery nodes into idle sleep states, individual resting devices experience a 98.3% reduction "
        "in per-round energy consumption while strictly preserving Byzantine Fault Tolerance safety invariants (K_t >= 3f + 1).",
        title="CORE RESEARCH RESULT"
    )

    # 2. Problem Definition & Literature Review
    add_h1("2. Problem Definition & Literature Review (Phase 1)")
    add_h2("2.1 IoT Hardware Constraints Profile")
    add_p(
        "Low-power microcontrollers (e.g. ESP32 Xtensa, STM32 ARM Cortex-M4, nRF52840) rely on finite battery reserves "
        "and operate over constrained wireless radio channels (LoRaWAN, Zigbee IEEE 802.15.4, BLE, NB-IoT). In these devices, "
        "radio transmission is the dominant power sink, dissipating orders of magnitude more energy than computational execution."
    )
    
    # Table of Hardware Profiles
    hw_table = doc.add_table(rows=4, cols=6)
    hw_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Device", "Architecture", "Clock", "SRAM", "Active Current", "Deep Sleep"]
    for i, h in enumerate(headers):
        cell = hw_table.rows[0].cells[i]
        cell.paragraphs[0].add_run(h).bold = True
        set_cell_background(cell, "D9E1F2")
        set_cell_margins(cell, 80, 80, 100, 100)

    hw_rows = [
        ("ESP32", "Xtensa Dual-Core", "240 MHz", "520 KB", "160 mA", "15 uA"),
        ("STM32F4", "ARM Cortex-M4", "84 MHz", "96 KB", "25 mA", "3 uA"),
        ("nRF52840", "ARM Cortex-M4", "64 MHz", "256 KB", "8 mA", "1.5 uA"),
    ]
    for r_idx, row_data in enumerate(hw_rows):
        row = hw_table.rows[r_idx + 1]
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.paragraphs[0].add_run(val)
            set_cell_background(cell, "FFFFFF" if r_idx % 2 == 0 else "F9FBFD")
            set_cell_margins(cell, 60, 60, 100, 100)

    add_h2("2.2 Critique of Traditional Consensus Mechanisms in IoT")
    add_p("Proof of Work (PoW): ", "• ")
    add_p("Requires continuous hash calculations that deplete a standard 2500 mAh battery within 10.4 hours without transmitting meaningful sensor data.")
    add_p("Practical Byzantine Fault Tolerance (PBFT): ", "• ")
    add_p("Requires O(N^2) broadcast messages. In a 20-node IoT mesh, 400 broadcast messages per round trigger packet collisions, hidden terminal issues, and radio saturation.")
    add_p("Proof of Stake (PoS) / DPoS: ", "• ")
    add_p("Statically delegates consensus based on coin stake. PoS is energy-blind: it will force a node with 2% battery to validate until it dies, causing network fragmentation.")

    # 3. Theoretical & Mathematical Formulations
    add_h1("3. Theoretical & Mathematical Formulations (Phase 2)")
    add_h2("3.1 The Heinzelman First-Order Radio Model")
    add_p(
        "Consensus round dissipation comprises radio transmission (E_tx), reception (E_rx), and CPU cryptographic operations (E_cpu). "
        "Radio dissipation follows the Heinzelman model with crossover distance threshold d0:"
    )
    add_p("d0 = sqrt(eps_fs / eps_mp) = sqrt(10e-12 / 0.0013e-12) ≈ 87.71 meters", "Crossover Distance: ")
    add_p("• If distance d < d0 (Free-Space): E_tx(l, d) = l * E_elec + l * eps_fs * d^2")
    add_p("• If distance d >= d0 (Multi-Path Fading): E_tx(l, d) = l * E_elec + l * eps_mp * d^4")
    add_p("• Reception Energy: E_rx(l) = l * E_elec  (where E_elec = 50 nJ/bit)")
    add_p("• Cryptographic CPU Energy: E_cpu = V_dd * I_active * T_crypto  (4.2 ms for secp256k1 sign)")

    add_h2("3.2 Byzantine Fault Tolerance Safety Invariant")
    add_p(
        "To guarantee safety (no two conflicting blocks can be finalized) and liveness (the network can continuously commit blocks) "
        "under dynamic committee scaling, the committee size K_t must strictly satisfy:"
    )
    add_p("K_t >= 3f + 1  (For f=1 tolerated Byzantine node, K_t >= 4)", "Safety Bound: ")
    add_p("Quorum Threshold Q_t = floor(2/3 * K_t) + 1  (e.g., 4 signatures required for K=5)", "Quorum Rule: ")

    add_h2("3.3 Multi-Objective Global Utility Optimization")
    add_p("The edge AI controller optimizes committee composition C_t by maximizing global utility U_t:")
    add_p("max U_t = w1 * S(C_t) + w2 * E_rem(C_t) - w3 * L(C_t)", "Objective Function: ")
    add_p("Subject to: w1 + w2 + w3 = 1.0 (w1=0.35 Security, w2=0.45 Battery, w3=0.20 Latency), Battery > 15%, Trust >= 0.60.")

    # 4. Decoupled 3-Tier Architecture
    add_h1("4. Decoupled 3-Tier System Architecture")
    add_p(
        "The system decouples high-overhead continuous intelligence from immutable blockchain execution across three distinct tiers:"
    )
    add_p("Tier 1: Physical / Simulated IoT Network (Python): ", "1. ")
    add_p("Virtual nodes holding secp256k1 private keys, generating sensor telemetry, signing block proposals, and discharging battery according to radio physics.")
    add_p("Tier 2: Edge AI Controller & Oracle (Python): ", "2. ")
    add_p("Evaluates incoming telemetry, applies feasibility filtering, ranks nodes using MCDM, implements leadership fatigue penalties, and submits epoch directives to the EVM.")
    add_p("Tier 3: Blockchain Settlement Layer (Solidity / Local Hardhat EVM): ", "3. ")
    add_p("NodeRegistry.sol tracks identities, stake, and slashing status. AdaptiveConsensus.sol enforces threshold signature verification (>= 2/3*K+1) and commits immutable block records.")

    # 5. Phase 3 Prototype Implementation & Results
    add_h1("5. Mid-Semester Prototype Implementation & Experimental Results (Phase 3)")
    add_h2("5.1 Smart Contract Implementation & Verification")
    add_p(
        "The smart contracts were compiled with Solidity 0.8.24 targeting the Cancun EVM. Five automated test suites in Hardhat verified "
        "registration, eligibility checks, BFT violation rejection (rejecting committees with size < 4), quorum verification, and signature tampering rejection."
    )
    add_p("Result: 5/5 Hardhat tests passing (100% compliance with EVM settlement specifications).", "Hardhat Test Output: ")

    add_h2("5.2 Empirical Energy Dissipation Disparity")
    add_p("Radio physics profiling revealed significant energy savings between active validators and resting idle nodes:")

    # Table of Energy Results
    energy_table = doc.add_table(rows=4, cols=4)
    energy_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    e_headers = ["Role in Consensus", "Per-Round Dissipation", "Relative Percentage", "Operational Mode"]
    for i, h in enumerate(e_headers):
        cell = energy_table.rows[0].cells[i]
        cell.paragraphs[0].add_run(h).bold = True
        set_cell_background(cell, "D9E1F2")
        set_cell_margins(cell, 80, 80, 100, 100)

    e_rows = [
        ("Committee Leader", "27.330 mJ", "100.0%", "Transmits proposal + verifies K-1 votes"),
        ("Active Validator", "7.201 mJ", "26.3%", "Receives proposal + signs & transmits vote"),
        ("Idle Sleep Node", "0.125 mJ", "0.5%", "Listens to 512-bit header + 15 uA deep sleep"),
    ]
    for r_idx, row_data in enumerate(e_rows):
        row = energy_table.rows[r_idx + 1]
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.paragraphs[0].add_run(val)
            set_cell_background(cell, "FFFFFF" if r_idx % 2 == 0 else "F9FBFD")
            set_cell_margins(cell, 60, 60, 100, 100)

    add_callout(
        "An idle resting node dissipates only 0.125 mJ per round compared to 7.201 mJ for an active validator, yielding a 98.3% energy reduction. "
        "Rotating low-battery nodes into idle states multiplies the total operational lifespan of the IoT fleet.",
        title="EMPIRICAL VALIDATION"
    )

    add_h2("5.3 Dynamic Leader Fatigue & Load Balancing")
    add_p(
        "To prevent a single high-battery device (e.g. Node 11) from being greedily selected as leader repeatedly, a consecutive-term "
        "fatigue penalty was incorporated into the scoring algorithm. The test pipeline confirmed active round-robin leadership: "
        "Node 11 (Epoch 1) -> Node 06 (Epoch 2) -> Node 02 (Epoch 3) -> Node 11 (Epoch 4). In Epoch 6, when Node 06 was force-drained "
        "to 10%, the AI immediately quarantined it to deep sleep, promoting Node 02 as the new leader without interrupting block finalization."
    )

    # 6. Phase 4: Machine Learning Advancement (Deep RL with PPO)
    add_h1("6. Machine Learning Advancement: Deep Reinforcement Learning (Phase 4)")
    add_p(
        "To elevate the system beyond static heuristic weighting, Phase 4 formalizes dynamic committee selection as a "
        "Markov Decision Process (MDP) implemented in an OpenAI Gymnasium environment (IoTConsensusEnv). An Actor-Critic neural "
        "network trained using Proximal Policy Optimization (PPO) with Generalized Advantage Estimation (GAE) learns non-linear "
        "policies that anticipate fleet depletion cascades under volatile network traffic."
    )
    add_h2("6.1 State and Action Space Formulations")
    add_p(
        "Observation Space (S_t in R^(4N + 2)): For each of the N IoT nodes, the state vector captures: [Residual Battery %, "
        "Link Latency ms, Historical Reputation Score, Leadership Fatigue Ratio]. This is concatenated with two global scalars: "
        "the fleet viability ratio (nodes above 15% battery) and normalized epoch progress."
    )
    add_p(
        "Action Space (A_t in R^(N + 1)): The continuous action vector outputs a continuous logit for dynamic committee sizing K_t "
        "(decoded via sigmoid into the valid Byzantine range [3f+1, K_max]), alongside N continuous priority logits for candidate ranking."
    )
    add_h2("6.2 Composite Multi-Objective Reward Function")
    add_p(
        "The PPO policy optimizes a composite reward function balancing consensus speed, fleet battery uniformity, and Byzantine safety:\n"
        "R_t = +3.0 * 1_consensus + 1.5 * E_mean - 1.0 * Var(E) - 1.2 * Latency_mean - 2.0 * ((K_t - K_min)/(K_max - K_min)) - P_BFT\n"
        "Where P_BFT = -15.0 penalizes invariant failures. Pre-trained weights were converged across 60 episodes and saved to models/drl_consensus_agent.pt."
    )

    # 7. Phase 5: Adversarial Stress Testing & Byzantine Slashing Defense
    add_h1("7. Adversarial Stress Testing & Byzantine Slashing Defense (Phase 5)")
    add_p(
        "Phase 5 introduces an automated attack injection and defense layer safeguarding the decentralized protocol against malicious, "
        "selfish, and faulty devices."
    )
    add_h2("7.1 Attack Vector Formulations")
    add_bullet("Telemetry Spoofing (Free-Rider): Low-battery nodes falsify their telemetry packets, reporting 100% battery and 5 ms latency to game the AI into selecting them as leader.")
    add_bullet("Byzantine Equivocation: A malicious validator produces two conflicting block proposal signatures for the same epoch (double-signing).")
    add_bullet("Sybil Infiltration: An unregistered cryptographic identity attempts to inject unauthorized votes into the quorum pool.")
    add_bullet("Silent Dropping (DoS): An elected validator abruptly stops transmitting, simulating packet drops, network partitions, or node death.")

    add_h2("7.2 Multi-Tier Defense Mechanisms")
    add_p(
        "1. Physics-Informed Heinzelman Consistency Checker: The AI controller checks incoming battery claims against the theoretical "
        "minimum discharge from the previous round's role. If a node reports an impossible positive jump or fails to dissipate expected radio "
        "energy, it is flagged as a free-rider, its reading is corrected, and its reputation is degraded by 50%.\n"
        "2. Cryptographic Equivocation Slasher: Conflicting signatures for identical epochs are verified via ecrecover. Upon cryptographic "
        "proof confirmation, the offending node is slashed on-chain in NodeRegistry.sol, zeroing its reputation and permanently disqualifying it.\n"
        "3. Whitelist Sybil Filter: Unregistered identities are rejected before vote aggregation, preventing Sybil attacks.\n"
        "4. Byzantine Liveness Guard: Quorum threshold guarantees that consensus finality proceeds uninterrupted as long as faults <= f."
    )

    # 8. Phase 6: Empirical Benchmarking & Comparative Evaluation
    add_h1("8. Empirical Benchmarking & Research Evaluation (Phase 6)")
    add_p(
        "To rigorously quantify research contributions, Phase 6 conducts long-horizon comparative simulations against two foundational "
        "paradigms under identical radio physics: (1) Classical Static PBFT, and (2) Static Stake-Based PoS with fixed validators."
    )

    # Benchmark Results Table
    bench_table = doc.add_table(rows=4, cols=6)
    bench_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    bench_headers = ["Consensus Protocol", "FND (Round)", "Half-Life", "Energy (J)", "Messages", "Energy Saved %"]
    for c_idx, h in enumerate(bench_headers):
        cell = bench_table.rows[0].cells[c_idx]
        cell.paragraphs[0].add_run(h).bold = True
        set_cell_background(cell, "1F4E79")
        set_cell_margins(cell, 80, 80, 100, 100)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    bench_data = [
        ("Static PBFT (All N=14)", "Round 6", "Round 59", "352,470 J", "6,850", "0.0% (Baseline)"),
        ("Static PoS (Fixed Stake)", "Round 15", "None (>100)", "48,404 J", "240", "86.3% (Unbalanced)"),
        ("AI Adaptive Consensus", "None (>100)", "None (>100)", "246,201 J", "954", "30.1% (Balanced)")
    ]
    for r_idx, row_data in enumerate(bench_data):
        row = bench_table.rows[r_idx + 1]
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.paragraphs[0].add_run(val)
            set_cell_background(cell, "FFFFFF" if r_idx % 2 == 0 else "F9FBFD")
            set_cell_margins(cell, 60, 60, 100, 100)

    add_callout(
        "Key Empirical Finding: In Static PBFT, the first node dies in Round 6 due to continuous N^2 broadcasts. In Static PoS, the fixed leader "
        "burns out in Round 15, partitioning the network. In AI Adaptive Consensus, ZERO nodes died across all 100 rounds (FND > 100), "
        "representing an over 6.67x extension in operational lifespan over PoS, and over 16x extension over PBFT.",
        title="BENCHMARK BREAKTHROUGH"
    )

    add_h2("8.1 Publication Figures & Graphical Analysis")
    import os
    fig_dir = "benchmark_results"
    charts = [
        ("battery_decay_curves.png", "Figure 1: Individual Node Battery Decay Curves Across Consensus Paradigms. Demonstrates uniform, balanced discharge in Adaptive Consensus versus rapid single-node burnout in PoS and parallel collapse in PBFT."),
        ("cumulative_energy_comparison.png", "Figure 2: Cumulative Energy Dissipation Trajectory. Adaptive Consensus preserves over 30% total fleet energy compared to PBFT while maintaining full BFT security."),
        ("network_survival_curves.png", "Figure 3: Network Survival & Node Longevity Curves. Highlights First Node Dead (FND) and Network Half-Life resilience under dynamic AI role rotation."),
        ("message_complexity_scaling.png", "Figure 4: Communication Message Complexity Scaling. Compares O(N^2) quadratic messaging in PBFT versus O(K^2) bounded messaging in AI Adaptive Consensus as network size scales from 10 to 100 devices.")
    ]
    for filename, caption in charts:
        img_path = os.path.join(fig_dir, filename)
        if os.path.exists(img_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_picture(img_path, width=Inches(5.8))
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_after = Pt(14)
            p_cap.add_run(caption).italic = True

    # 9. Complete 10-Slide Presentation Script
    add_h1("9. Complete 10-Slide Project Presentation Script")
    slides_content = [
        ("Slide 1: Title & Overview", "AI-Driven Adaptive Consensus Mechanism for Energy-Efficient Blockchain IoT Networks. Introduces the decoupled 3-tier architecture balancing decentralized Byzantine security with microcontroller battery preservation."),
        ("Slide 2: The Core Problem", "Details why canonical consensus fails on IoT hardware: PoW exhausts battery in hours, PBFT causes O(N^2) packet collision storms, and PoS is energy-blind, burning out peripheral sensors."),
        ("Slide 3: Theoretical System & Radio Physics", "Presents the Heinzelman first-order radio model, the crossover threshold (d0 = 87.71m), and the BFT safety floor (K_t >= 3f + 1, Quorum = floor(2/3*K) + 1)."),
        ("Slide 4: Decoupled 3-Tier Architecture", "Explains architectural separation: Tier 1 Virtual ESP32 Fleet -> Tier 2 Edge AI Controller / Oracle -> Tier 3 Solidity Smart Contracts on the EVM (NodeRegistry.sol and AdaptiveConsensus.sol)."),
        ("Slide 5: Phase 4 Deep Reinforcement Learning", "Details upgrading to Actor-Critic PPO policy network trained in a Gymnasium MDP environment, optimizing composite rewards over a 58-dimensional state space."),
        ("Slide 6: Phase 5 Adversarial Attack Suite", "Outlines simulated attacks: Telemetry Spoofing, Byzantine Double-Signing, Sybil Infiltration, and Validator Silent Dropping, with automated physics-based sanitization and on-chain slashing."),
        ("Slide 7: Phase 6 Empirical Benchmarking", "Compares performance against Static PBFT and Fixed PoS over 100 rounds: Adaptive Consensus extends First Node Dead (FND) by over 6.67x over PoS and over 16x over PBFT."),
        ("Slide 8: Communication & Scalability Gains", "Demonstrates reduction of message complexity from quadratic O(N^2) to bounded O(K^2), cutting network packets by 86% and eliminating RF broadcast storms."),
        ("Slide 9: Interactive Demonstration Interface", "Showcases the real-time Streamlit dashboard with DRL/MCDM toggle, live fleet battery gauges, attack injection controls, and on-chain security audit logging."),
        ("Slide 10: Conclusion & Deliverables", "Summarizes key contributions: complete 6-phase codebase, 29 passing unit tests, verified EVM contracts, publication-ready figures, and full thesis documentation."),
    ]
    for title, desc in slides_content:
        add_p(f"{desc}", f"{title}: ")

    # 10. Review Panel Defense Q&A
    add_h1("10. Review Panel Defense & Viva Q&A Guide")
    qa_list = [
        ("Q: Why is Solidity necessary if the AI runs off-chain?",
         "Defense: Smart contracts cannot perform floating-point neural network inferences or multi-criteria optimization within block gas limits. However, IoT networks require an immutable, trustless ledger for identity registry, slashing, and quorum verification. Solidity acts as the decentralized settlement layer, while Python acts as the off-chain Edge AI compute engine."),
        ("Q: Why not scale the committee down to 2 nodes to save even more power?",
         "Defense: Byzantine Fault Tolerance mathematically requires K >= 3f + 1 to prevent double-spending and network forks. For f = 1 malicious or offline node, the committee must have at least 4 nodes. Our AI algorithm enforces this invariant as a non-negotiable hard constraint."),
        ("Q: How does rotating nodes conserve device battery?",
         "Defense: In wireless IoT devices, radio transmission is the dominant source of power loss. In standard PBFT, all N nodes participate in every round (O(N^2) complexity). By dynamically selecting a smaller committee (K << N) and rotating low-battery devices into low-power idle sleep (15 uA), resting devices consume 98.3% less energy per round, significantly extending fleet survival."),
        ("Q: How do you prevent a node from lying about having 100% battery to seize leadership?",
         "Defense: In Phase 5, we introduced a physics-informed anomaly detector. The controller maintains a historical model of expected energy drain based on past validation duties under the Heinzelman radio model. If an active node reports an impossible positive battery increase or claims 100% after signing blocks, it is flagged as a free-rider, its telemetry is corrected, and its reputation is degraded by 50%."),
        ("Q: What happens if a malicious node signs two conflicting blocks at the same epoch?",
         "Defense: This constitutes Byzantine Equivocation. The defense detector verifies both conflicting ECDSA signatures using ecrecover. Upon proof verification, it invokes slashNode on NodeRegistry.sol, zeroing the node's reputation and permanently blacklisting it from all future committees."),
        ("Q: How does the AI policy achieve load balancing across the fleet?",
         "Defense: Both the MCDM utility function and the DRL policy network incorporate a leadership fatigue penalty. After leading a round, a node incurs a high participation penalty, preventing consecutive-term monopolies and forcing dynamic round-robin rotation among the healthiest nodes.")
    ]
    for q, a in qa_list:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(4)
        p.add_run(q).bold = True
        add_p(a)

    output_path = "AI_Driven_Consensus_Project_Report.docx"
    doc.save(output_path)
    print(f"[SUCCESS] Final Word document generated successfully: {output_path}")


if __name__ == "__main__":
    create_document()
