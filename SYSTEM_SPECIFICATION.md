# SYSTEM SPECIFICATION: AI-DRIVEN ADAPTIVE CONSENSUS FOR ENERGY-EFFICIENT BLOCKCHAIN IOT NETWORKS

> **Document Purpose:** Self-contained, comprehensive technical specification and architectural blueprint for the AI-Driven Adaptive Consensus project. Designed to provide full context, mathematical models, smart contract interfaces, data flows, and runtime mechanics for developers, researchers, and automated AI agents.

---

## 1. Executive Summary & Problem Formulation

### 1.1 The Research Problem
The integration of Internet of Things (IoT) edge devices with decentralized distributed ledger technologies (DLT / Blockchain) provides tamper-proof compliance, data provenance, and machine-to-machine (M2M) autonomous micro-economies. However, canonical blockchain consensus mechanisms fail fundamentally on low-power IoT hardware:

1. **Proof of Work (PoW):** Requires continuous hashing (SHA-256 / Ethash). An ESP32 microcontroller at 240 MHz dissipates ~240 mA, completely draining a 2500 mAh Li-ion battery in under 10.4 hours without transmitting meaningful telemetry.
2. **Classical Practical Byzantine Fault Tolerance (PBFT):** Incurs $\mathcal{O}(N^2)$ communication message complexity across $N$ participating nodes. Over low-power radio physical layers (LoRaWAN, Zigbee IEEE 802.15.4, BLE Mesh, NB-IoT), broadcast storms trigger packet collisions, RF channel saturation, and duty-cycle exhaustion.
3. **Proof of Stake (PoS) / Delegated PoS (DPoS):** Energy-blind validator selection based solely on capital staking or static delegation. Peripheral devices with near-empty batteries (e.g., 3%) are forced to validate blocks until battery exhaustion, causing localized sensor blackout and network partitioning.

### 1.2 The Proposed Innovation
An **AI-driven, energy-aware adaptive consensus protocol** that decouples computationally heavy multi-objective optimization from the blockchain settlement layer:
* **Dynamic Committee Sizing ($K_t$):** Scales down active consensus participation from $N$ to $K_t \ll N$ during stable network epochs, reducing packet complexity from $\mathcal{O}(N^2)$ to $\mathcal{O}(K_t^2)$.
* **Health-Aware Validator Rotation:** Actively offloads validation responsibilities to healthy nodes while allowing depleted nodes ($<15\%$) to enter deep-sleep ($15\text{ }\mu\text{A}$), saving up to **98.3% energy per round**.
* **Byzantine Fault Tolerance Guarantee:** Strictly enforces the theoretical floor $K_t \ge 3f + 1$, preventing security degradation.
* **Decoupled 3-Tier Architecture:** Heavy floating-point multi-criteria optimization runs off-chain in Python (as an Edge AI Oracle), while Solidity smart contracts on the EVM act purely as a decentralized identity registry, quorum verifier, and slashing enforcer.

---

## 2. Theoretical & Mathematical Foundations

### 2.1 Heinzelman First-Order Radio Energy Model
Radio communication energy consumption per consensus round ($E_{round}^{(i)}$) is modeled using first-principles physics:

$$E_{tx}(l, d) = \begin{cases} l \cdot E_{elec} + l \cdot \epsilon_{fs} \cdot d^2, & \text{if } d < d_0 \\ l \cdot E_{elec} + l \cdot \epsilon_{mp} \cdot d^4, & \text{if } d \ge d_0 \end{cases}$$

$$E_{rx}(l) = l \cdot E_{elec}$$

$$E_{cpu} = P_{cpu} \cdot T_{crypto} = (V_{dd} \cdot I_{active}) \cdot T_{crypto}$$

#### Physical Constants & Parameters:
* $E_{elec} = 50 \times 10^{-9}\text{ J/bit}$ ($50\text{ nJ/bit}$ transmitter/receiver electronics dissipation).
* $\epsilon_{fs} = 10 \times 10^{-12}\text{ J/bit/m}^2$ ($10\text{ pJ/bit/m}^2$ free-space amplifier factor).
* $\epsilon_{mp} = 0.0013 \times 10^{-12}\text{ J/bit/m}^4$ ($0.0013\text{ pJ/bit/m}^4$ multi-path fading amplifier factor).
* **Crossover Distance Threshold ($d_0$):**
  $$d_0 = \sqrt{\frac{\epsilon_{fs}}{\epsilon_{mp}}} = \sqrt{\frac{10 \times 10^{-12}}{0.0013 \times 10^{-12}}} \approx 87.71\text{ meters}$$
* $V_{dd} = 3.3\text{ V}$, $I_{active} = 160\text{ mA}$ (ESP32 active current) $\implies P_{cpu} = 0.528\text{ W}$.
* $I_{sleep} = 15\text{ }\mu\text{A}$ (ESP32 deep-sleep current).
* $T_{crypto} = 4.2\text{ ms}$ (`secp256k1` ECDSA signature generation time).

#### Node Role Energy Profiles:
* **Committee Leader ($E_{leader}$):** Transmits proposal ($8192\text{ bits}$) to $K-1$ members, receives $K-1$ votes ($1024\text{ bits}$), verifies $K-1$ signatures, signs proposal $\implies \mathbf{\approx 27.33\text{ mJ/round}}$.
* **Active Validator ($E_{validator}$):** Receives proposal, verifies proposal, signs vote, transmits vote to leader, receives commit notification $\implies \mathbf{\approx 7.20\text{ mJ/round}}$.
* **Idle Node ($E_{idle}$):** Turns off radio power amplifier, enters $15\text{ }\mu\text{A}$ deep sleep, wakes up briefly for $512\text{-bit}$ header commit notice $\implies \mathbf{\approx 0.125\text{ mJ/round}}$ (**98.3% energy reduction**).

---

### 2.2 Byzantine Fault Tolerance Safety Invariants
In a network tolerating $f$ Byzantine (malicious, offline, or faulty) nodes:

1. **Minimum Committee Size Floor:**
   $$K_t \ge 3f + 1$$
   *(For $f = 1$ tolerated faulty node, $K_t \ge 4$).*
2. **On-Chain Cryptographic Quorum Threshold ($Q_t$):**
   $$Q_t = \left\lfloor \frac{2}{3} K_t \right\rfloor + 1$$
   Ensures that any two quorums must overlap by at least $f + 1$ honest nodes, preventing conflicting forks or double-spending.

---

### 2.3 Multi-Objective Utility Function & Load Balancing
At each epoch $t$, the controller evaluates candidate nodes across three normalized criteria:

$$U(i) = w_1 \cdot \mathcal{S}_i + w_2 \cdot \overline{E}_{i} - w_3 \cdot \mathcal{L}_i - \mathcal{F}_i(t)$$

#### Terms:
* **Security / Reputation ($\mathcal{S}_i$):** $R_i \in [0.0, 1.0]$ derived from past honest consensus validations.
* **Normalized Battery ($\overline{E}_i$):** $\frac{\text{Battery}_i}{100.0} \in [0.0, 1.0]$.
* **Normalized Latency ($\mathcal{L}_i$):** $\frac{\text{Latency}_i}{\text{MaxLatency}} \in [0.0, 1.0]$.
* **Leadership Workload Fatigue ($\mathcal{F}_i(t)$):**
  $$\mathcal{F}_i(t) = \begin{cases} \frac{0.20}{\max(1, t - t_{last\_lead})}, & \text{if } t - t_{last\_lead} \le 2 \\ 0.0, & \text{otherwise} \end{cases}$$
  Penalizes consecutive leader re-election, forcing dynamic round-robin rotation among the healthiest committee members.
* **Weight Constraint:** $w_1 + w_2 + w_3 = 1.0$ (Default: $w_1 = 0.35$ Security, $w_2 = 0.45$ Energy, $w_3 = 0.20$ Latency).
* **Hard Feasibility Filter:**
  $$\mathcal{A}_t = \{ i \in \mathcal{N} \mid \text{is\_alive}_i \land \text{Battery}_i > 15.0\% \land R_i \ge 0.60 \}$$

---

## 3. Decoupled 3-Tier Architecture

```
+-----------------------------------------------------------------------------------+
|                           Tier 1: IoT Device Network                              |
|   - N heterogeneous virtual/physical microcontrollers (ESP32 / STM32 / nRF52840)   |
|   - Cryptographic Identity: secp256k1 keypairs (Address, Private Key)             |
|   - Physics Engine: Heinzelman first-order radio dissipation (E_tx, E_rx, E_cpu)  |
|   - Emits real-time telemetry: [Node ID, Address, Battery %, Latency ms, Trust]  |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Telemetry Heartbeat
                                          v
+-----------------------------------------------------------------------------------+
|                        Tier 2: Edge AI Controller & Oracle                        |
|   - Feasibility Filtering: Rejects dead, low-battery (<=15%), or low-trust (<0.6)  |
|   - Multi-Objective Decision Making (MCDM): Ranks feasible pool via utility U(i)  |
|   - Dynamic Committee Sizing: Calculates K_t >= 3f + 1                            |
|   - Consecutive Fatigue Penalization: Rotates round leader                        |
|   - Directives: Submits epoch committee and threshold to EVM via JSON-RPC        |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | JSON-RPC Transactions & Cryptographic Sigs
                                          v
+-----------------------------------------------------------------------------------+
|                     Tier 3: Blockchain Settlement Layer (EVM)                     |
|   - Local EVM Node (Hardhat / Cancun target @ http://127.0.0.1:8545)             |
|   - NodeRegistry.sol: Whitelist, public keys, staking, slashing, eligibility     |
|   - AdaptiveConsensus.sol: Epoch registration, threshold ecrecover, block commit  |
|   - Emits immutable events: EpochScheduled, BlockCommitted, NodeSlashed           |
+-----------------------------------------------------------------------------------+
```

---

## 4. End-to-End Consensus Round Trace (Execution Flow)

For every consensus epoch $t$:

1. **Telemetry Streaming:** All $N$ nodes stream telemetry packets `[node_id, address, battery_pct, latency_ms, reputation]` to Tier 2.
2. **Feasibility Filtering:** Nodes with battery $\le 15\%$ or reputation $< 0.60$ are assigned role `IDLE_SLEEP` and excluded from candidate set $\mathcal{A}_t$.
3. **AI Committee Election:**
   * Dynamic committee size determined: $K_t = \min(\max(3f+1, 3f+1 + \lfloor|\mathcal{A}_t|/5\rfloor), K_{max})$.
   * Nodes ranked by utility $U(i)$ taking into account the fatigue penalty.
   * Top $K_t$ nodes form committee $\mathcal{C}_t$; rank #1 node designated as **Round Leader**.
4. **On-Chain Epoch Registration:** Edge Oracle calls `AdaptiveConsensus.setEpochCommittee(epochId, members[], leader)`. Contract validates $K_t \ge 4$ and sets quorum threshold $Q_t = \lfloor 2/3 K_t \rfloor + 1$.
5. **Block Proposal & Hashing:**
   * Leader packages sensor data, computes state root and telemetry hash:
     $$\text{rawHash} = \text{keccak256}(\text{abi.encodePacked}(epochId, blockNumber, stateRoot, telemetryHash))$$
   * Broadcasts proposal packet ($8192\text{ bits}$) to $K_t - 1$ validators.
6. **Cryptographic Signing (Attestation):**
   * Each validator verifies proposal and signs `rawHash` using local private key (`secp256k1` ECDSA).
   * Validators return $65\text{-byte}$ signature strings to Leader.
7. **On-Chain Quorum Settlement:**
   * Leader bundles block metadata and signatures array: `AdaptiveConsensus.commitBlock(..., signatures[])`.
   * Contract recovers signers via `ECDSA.recover(ethSignedMessageHash, sig)`.
   * Verifies each signer belongs to epoch committee, ensures zero duplicate signatures, and validates count $\ge Q_t$.
   * State recorded on-chain; `BlockCommitted` event emitted.
8. **Physical Discharge:**
   * Leader drains $\approx 27.3\text{ mJ}$.
   * Validators drain $\approx 7.2\text{ mJ}$.
   * Idle nodes drain $\approx 0.125\text{ mJ}$.
   * Fleet battery states updated for epoch $t+1$.

---

## 5. Technology Stack & Component Mapping

| Component | Technology | Version | Location in Codebase |
| :--- | :--- | :--- | :--- |
| **Smart Contracts** | Solidity | `^0.8.24` (Cancun target) | `contracts/NodeRegistry.sol`, `contracts/AdaptiveConsensus.sol` |
| **Contract Security** | OpenZeppelin | `v5.0.2` | `Ownable`, `ECDSA`, `MessageHashUtils` |
| **EVM Engine & Tests**| Hardhat | `2.22.18` | `hardhat.config.js`, `tests/contracts/ConsensusTest.js` |
| **Language Runtime** | Python | `3.11.9` | Core simulation, optimization, orchestrator, and UI |
| **Cryptography** | `eth-account` | `>=0.11.0` | `simulator/iot_node.py` (`Account.create()`, `sign_message()`) |
| **Blockchain Bridge** | `web3.py` | `>=6.15.0` | `bridge/web3_client.py` (JSON-RPC contract interactions) |
| **Optimization Math** | `NumPy`, `SciPy` | `>=1.26.0`, `>=1.11.0` | `ai_engine/objective.py`, `simulator/energy_model.py` |
| **Unit Testing** | `pytest` | `>=8.0.0` | `tests/test_math_models.py` |
| **Interactive UI** | `Streamlit` | `>=1.31.0` | `dashboard/app.py` |
| **Visualization** | `Matplotlib`, `Pandas` | `>=3.8.0`, `>=2.2.0` | `dashboard/app.py` |
| **Report Generation** | `python-docx` | `>=1.1.0` | `generate_report_docx.py` |

---

## 6. Directory Structure & File Manifest

```text
AI_driven_consensus/
│
├── contracts/                        # TIER 3: Solidity Smart Contracts
│   ├── NodeRegistry.sol              # On-chain node identity, status, eligibility, slashing
│   └── AdaptiveConsensus.sol         # Epoch committee scheduling, quorum threshold verification
│
├── simulator/                        # TIER 1: Physical IoT Fleet Simulation
│   ├── models.py                     # Data contracts (IoTDeviceSpec, TelemetryPacket, Directive, Vote)
│   ├── energy_model.py               # Heinzelman First-Order Radio Model (d^2 / d^4, CPU, presets)
│   ├── iot_node.py                   # Virtual ESP32 node with ECDSA signing & Heinzelman discharge
│   └── fleet_simulator.py            # Multi-node fleet coordinator & telemetry streaming
│
├── ai_engine/                        # TIER 2: Intelligent Committee Selection
│   └── objective.py                  # Multi-Objective Optimizer (MCDM, fatigue, BFT safety invariant)
│
├── bridge/                           # Integration Bridge Layer
│   ├── web3_client.py                # Web3.py JSON-RPC client interacting with local EVM contracts
│   └── orchestrator.py               # End-to-end consensus round coordinator
│
├── dashboard/                        # Presentation & Demonstration UI
│   └── app.py                        # Streamlit interactive dashboard with live fleet & ledger
│
├── docs/                             # Academic & Research Documentation
│   ├── PROBLEM_AND_LITERATURE.md     # Hardware constraints & consensus critique
│   └── SYSTEM_AND_MATHEMATICAL_MODEL.md # Radio physics & BFT formulations
│
├── tests/                            # Automated Verification Suites
│   ├── test_math_models.py           # Pytest suite (9 tests) for radio physics & AI math
│   └── contracts/ConsensusTest.js    # Hardhat suite (5 tests) for EVM contracts
│
├── main.py                           # Master CLI Unified Pipeline (all, demo, benchmark, train, report)
├── ai_engine/                        # Artificial Intelligence & Multi-Objective Layer
│   ├── objective.py                  # Analytical Multi-Criteria Decision-Making (MCDM)
│   ├── drl_agent.py                  # PPO Actor-Critic Neural Policy Network
│   ├── consensus_env.py              # OpenAI Gymnasium IoT Consensus Environment (MDP)
│   ├── train_rl.py                   # PPO Training Pipeline
│   └── defense_detector.py           # Physics-informed Anomaly & Equivocation Slashing Detector
│
├── benchmark/                        # Empirical Research & Evaluation Suite
│   ├── benchmark_engine.py           # Multi-protocol simulator (Adaptive vs PBFT vs PoS)
│   └── plot_generator.py             # Publication chart generator and CSV/JSON exporter
│
├── contracts/                        # Smart Contracts (EVM Cancun / Solidity 0.8.24)
│   ├── NodeRegistry.sol              # Staking, node identities, reputation, and on-chain slashing
│   └── AdaptiveConsensus.sol         # Quorum threshold verification & epoch commitment
│
├── simulator/                        # IoT Fleet Physics & Adversarial Simulator
│   ├── energy_model.py               # Heinzelman First-Order Radio Model implementation
│   ├── iot_node.py                   # Virtual ESP32 node with ECDSA secp256k1 keypairs
│   ├── fleet_simulator.py            # Heterogeneous mesh network manager & topology
│   ├── adversarial.py                # Attack injection (spoofing, double-signing, Sybil, DoS)
│   └── models.py                     # Strongly-typed Dataclasses & EVM types
│
├── dashboard/                        # Presentation & Demonstration GUI
│   └── app.py                        # Streamlit interactive dashboard with live fleet & ledger
│
├── docs/                             # Academic & Research Documentation
│   ├── PROBLEM_AND_LITERATURE.md     # Hardware constraints & consensus critique
│   └── SYSTEM_AND_MATHEMATICAL_MODEL.md # Radio physics & BFT formulations
│
├── tests/                            # Automated Verification Suites
│   ├── test_math_models.py           # Pytest suite for radio physics & utility math
│   ├── test_drl_agent.py             # Pytest suite for Gymnasium MDP & PPO network
│   ├── test_adversarial_defense.py   # Pytest suite for attack vectors & slashing
│   ├── test_benchmarks.py            # Pytest suite for comparative simulations
│   └── contracts/ConsensusTest.js    # Hardhat suite (5 tests) for EVM contracts
│
├── generate_report_docx.py           # Dissertation/Report Generator (.docx)
├── hardhat.config.js                 # Hardhat configuration (Solidity 0.8.24, Cancun EVM)
├── package.json                      # Node.js dependencies
└── requirements.txt                  # Python dependencies
```

---

## 7. Edge Cases & Protocol Fault Handling

| Edge Case | Failure Risk | Protocol Defense & Handling |
| :--- | :--- | :--- |
| **All fleet nodes drop $< 15\%$ battery** | Fleet death or broken BFT bound ($K < 3f + 1$) | **Consensus Safe Hibernation:** AI halts block emission; devices cut radios to $15\text{ }\mu\text{A}$ sleep; data queues in flash memory until solar/energy harvesters recharge past $25\%$. |
| **Leader dies mid-round** | Stalled block production | **$500\text{ ms}$ Round Timeout:** Validators abort round; leader penalized with liveness fault ($\beta_i = \beta_i + 1$); #2 deputy promoted immediately. |
| **Network partition (Split-brain)** | Conflicting blockchain forks | **Quorum Invariant ($\ge \lfloor 2/3 K \rfloor + 1$):** Neither isolated partition can gather a supermajority; safety preserved over liveness. |
| **Telemetry battery spoofing (Free-rider)**| Selfish node claiming $5\%$ to sleep forever | **Reputation Decay:** Chronic failure to validate degrades trust score below $0.60$, disqualifying node from rewards. |
| **Telemetry spoofing to hijack leadership**| Malicious node falsely claiming $100\%$ battery | **Physics Cross-Validation & Leadership Fatigue:** AI compares claimed battery against expected $\Delta E$; fatigue penalty rotates leader regardless. |
| **Double-signing (Equivocation)** | Byzantine ledger corruption | **On-Chain Slashing:** Conflicting signatures submitted to `NodeRegistry.sol`; reputation zeroed and address permanently blacklisted. |

---

## 8. Core Subsystems & Implementation Verification

The system integrates five interdependent engineering subsystems into one unified, end-to-end framework:

### 8.1 Mathematical & Radio Physics Foundation
* Formalized Heinzelman radio physics ($d^2/d^4$ free-space/multi-path propagation), CPU cryptographic dissipation, and multi-objective global utility function.
* Proved BFT safety bound $K_t \ge 3f + 1$ and quorum rule $\lfloor 2/3 K_t \rfloor + 1$.
* Verified via unit tests in `tests/test_math_models.py`.

### 8.2 Smart Contract Settlement Layer (EVM)
* Implemented `NodeRegistry.sol` and `AdaptiveConsensus.sol` compiled targeting Solidity 0.8.24 and the Cancun EVM.
* Enforces on-chain cryptographic quorum verification ($\ge \lfloor 2/3 K \rfloor + 1$), node staking, registration whitelisting, and automated slashing.
* Verified via 5 automated Hardhat test suites (`tests/contracts/ConsensusTest.js`).

### 8.3 Intelligent Optimization Engine (MCDM & Deep Reinforcement Learning)
* **Heuristic MCDM Optimizer (`ai_engine/objective.py`):** Analytical Pareto ranking balancing residual battery, link latency, reputation, and consecutive-term leadership fatigue penalties.
* **Deep Reinforcement Learning Agent (`ai_engine/drl_agent.py`, `ai_engine/consensus_env.py`):**
  * Formalized consensus optimization as a **Markov Decision Process (MDP)** in Gymnasium environment (`IoTConsensusEnv`).
  * **Observation State Space ($S_t \in \mathbb{R}^{4N + 2}$):** For each of the $N$ nodes: normalized residual battery, normalized latency, reputation score, and participation/leadership fatigue, augmented with global fleet viability ratio and normalized epoch counter.
  * **Continuous Action Space ($A_t \in \mathbb{R}^{N + 1}$):** Single committee sizing logit $\alpha_{size}$ decoded via sigmoid to $K_t \in [3f+1, \min(N_{viable}, K_{max})]$, plus $N$ continuous priority logits for ranking candidates.
  * **Composite Multi-Objective Reward Function ($R_t$):**
    $$R_t = +3.0 \cdot \mathbf{1}_{\text{consensus}} + 1.5 \cdot \overline{E}_{comm} - 1.0 \cdot \sigma^2(E) - 1.2 \cdot \overline{\mathcal{L}}_{comm} - 2.0 \cdot \left(\frac{K_t - K_{min}}{K_{max} - K_{min}}\right) - \mathcal{P}_{BFT}$$
  * **Actor-Critic Neural Policy with PPO:** Dual MLP backbones trained with clipped surrogate objective and Generalized Advantage Estimation (GAE). Pre-trained weights saved to `models/drl_consensus_agent.pt`.
* Fully integrated `DRLCommitteeSelector` into both the interactive Streamlit dashboard (`dashboard/app.py`) and the unified pipeline (`main.py`).
* Verified via unit tests in `tests/test_drl_agent.py`.

### 8.4 Byzantine Defense & Slashing Anomaly Detector
* **Adversarial Attack Simulation Engine (`simulator/adversarial.py`):**
  * **Telemetry Spoofing (Free-Rider):** Depleted nodes faking 100% battery and 5 ms latency to game the AI into selecting them as leader.
  * **Byzantine Double-Signing (Equivocation):** Conflicting block proposals signed by the same keypair at the same epoch.
  * **Sybil Infiltration:** Rogue votes signed by unregistered cryptographic identities.
  * **Silent Dropping (DoS):** Unresponsiveness of elected validators testing Byzantine quorum tolerance ($K_t \ge 3f + 1$).
* **Byzantine Defense & Anomaly Detector Layer (`ai_engine/defense_detector.py`):**
  * **Physics-Informed Sanitization:** Uses Heinzelman radio model equations to detect negative battery discharge and unphysical energy claims, sanitizing telemetry and penalizing reputation.
  * **Cryptographic Equivocation Slashing:** Automatically verifies dual conflicting signatures via `ecrecover` / `Account.recover_message`, triggers on-chain slashing, zeroes reputation, and blacklists rogue nodes.
  * **Sybil Whitelist Filter:** Drops unauthorized signatures before quorum aggregation.
  * **Liveness & Quorum Assurance:** Guarantees consensus finality when faulty nodes $\le f$.
* Verified via unit tests in `tests/test_adversarial_defense.py`.

### 8.5 Empirical Benchmarking & Comparative Evaluation
* Long-horizon comparative benchmarking engine (`benchmark/benchmark_engine.py`) evaluating **Adaptive Consensus** against **Static PBFT** and **Fixed Stake-based PoS** under identical radio physics.
* **Publication Chart Generator (`benchmark/plot_generator.py`):** Exports high-resolution charts (`battery_decay_curves.png`, `cumulative_energy_comparison.png`, `network_survival_curves.png`, `message_complexity_scaling.png`) and metrics (`benchmark_metrics_summary.json`, `.csv`).
* **Key Empirical Results:**
  * **First Node Dead (FND) Longevity:** Static PBFT experiences FND at Round 6; Static PoS exhausts its fixed leader at Round 15; Adaptive Consensus operates over 100 rounds without a single node dying ($FND > 100$), achieving **> 6.67x extension** over PoS and **> 16x extension** over PBFT.
  * **Message Complexity:** Reduced from $\mathcal{O}(N^2)$ (6,850 messages) to bounded $\mathcal{O}(K^2)$ (954 messages), delivering an **86.1% communication reduction**.
  * **Fleet Energy Uniformity:** Dynamic leadership fatigue successfully eliminated single-node burnout.
* Verified via unit tests in `tests/test_benchmarks.py`. Total automated test suite: **29/29 passing**.

---

## 9. Verification & Quickstart Commands

The entire system is controlled via the master CLI runner `main.py` and modular tool scripts:

```bash
# 1. Install Node.js & Hardhat dependencies
npm install --legacy-peer-deps

# 2. Compile Solidity contracts (EVM target: Cancun)
npx hardhat compile

# 3. Run automated Hardhat smart contract tests (5 passing)
npx hardhat test

# 4. Install Python dependencies (PyTorch, Gymnasium, Web3, Streamlit, etc.)
pip install -r requirements.txt

# 5. Run all 29 automated unit tests across the entire system
python -m pytest tests/ -v

# 6. Execute complete unified end-to-end pipeline (consensus + defense + benchmarks)
python main.py

# 7. Execute interactive consensus and Byzantine attack defense demo
python main.py --mode demo

# 8. Execute empirical benchmark against PBFT and PoS baselines
python main.py --mode benchmark

# 9. Train the Deep Reinforcement Learning (PPO) neural policy
python main.py --mode train

# 10. Generate the complete publication Word dissertation report (.docx)
python main.py --mode report

# 11. Launch the real-time interactive Streamlit dashboard
streamlit run dashboard/app.py
```
