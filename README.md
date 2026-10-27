# AI-Driven Adaptive Consensus Mechanism for Energy-Efficient Blockchain IoT Networks

An intelligent, energy-aware adaptive consensus framework that decouples heavy multi-objective optimization from the blockchain settlement layer, extending IoT network survival while strictly preserving Byzantine Fault Tolerance ($K_t \ge 3f + 1$).

---

## 1. Prerequisites

Before running this project, ensure you have the following installed on your machine:

| Prerequisite | Minimum Version | Check Command | Purpose |
| :--- | :--- | :--- | :--- |
| **Node.js** | `v18.x` or higher | `node -v` | Smart contract development & Hardhat EVM |
| **npm** | `v9.x` or higher | `npm -v` | Node package manager |
| **Python** | `3.10.x` or `3.11.x` | `python --version` | IoT fleet simulation, AI engine, and UI |
| **Git** | Any recent version | `git --version` | Repository cloning and version control |

---

## 2. Step-by-Step Installation & Setup

### Step 1: Clone the Repository
```bash
git clone <YOUR_REPOSITORY_URL>
cd AI_driven_consensus
```

### Step 2: Install Blockchain & Hardhat Dependencies
Install the required Ethereum development tools and OpenZeppelin contracts:
```bash
npm install --legacy-peer-deps
```

### Step 3: Compile the Solidity Smart Contracts
Compile `NodeRegistry.sol` and `AdaptiveConsensus.sol` using Hardhat (targeting Cancun EVM):
```bash
npx hardhat compile
```
*Expected output: `Compiled 12 Solidity files successfully (evm target: cancun)`.*

### Step 4: Set Up Python Virtual Environment (Recommended)
Create and activate an isolated Python environment:

* **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
  *(If execution of scripts is disabled, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

* **On macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Step 5: Install Python Dependencies
Install `torch`, `gymnasium`, `web3`, `eth-account`, `streamlit`, `scipy`, `numpy`, `matplotlib`, and `python-docx`:
```bash
pip install -r requirements.txt
```

---

## 3. How to Run & Verify the Project

### A. Run Automated Smart Contract Tests (Hardhat)
Executes 5 automated unit tests verifying node registration, BFT safety rejection ($K < 4$), quorum calculation ($\lfloor\frac{2}{3}K\rfloor + 1$), and cryptographic signature verification:
```bash
npx hardhat test
```
*Expected output: `5 passing`.*

### B. Run Mathematical, Physics, DRL & Byzantine Defense Tests (Pytest)
Executes 26 automated unit tests verifying Heinzelman radio physics ($d^2 / d^4$), crossover distance ($87.7\text{m}$), multi-objective utility functions, MDP gym environment, Actor-Critic networks, telemetry spoofing detection, equivocation slashing, and Sybil filtering:
```bash
python -m pytest tests/ -v
```
*Expected output: `26 passed in ~11s`.*

### C. Run the Phase 5 Adversarial Stress Testing & Byzantine Slashing Pipeline
Demonstrates active defense under 4 attack vectors (Telemetry Spoofing, Double-Signing Equivocation, Sybil Infiltration, and Validator Silent Dropping), with real-time anomaly detection and on-chain slashing:
```bash
python run_phase5_pipeline.py
```

### D. Run the Phase 4 Deep RL Consensus Pipeline (Terminal Demo)
Demonstrates the trained Actor-Critic (PPO) neural policy dynamically sizing committees, electing leaders based on neural logits, verifying ECDSA quorum, and calculating Heinzelman energy savings:
```bash
python run_phase4_pipeline.py
```

### E. (Optional) Re-Train the Deep RL (PPO) Agent
To re-train the PPO agent from scratch through the Gymnasium environment:
```bash
python ai_engine/train_rl.py
```
*Outputs: `models/drl_consensus_agent.pt`.*

### F. Run the Phase 3 Heuristic (MCDM) Pipeline
Demonstrates the original multi-criteria utility heuristic and leadership fatigue load balancing:
```bash
python run_phase3_pipeline.py
```

### G. Launch the Real-Time Streamlit Visual Dashboard
Launches the interactive GUI for presentations and reviews:
```bash
streamlit run dashboard/app.py
```
*Open your browser at `http://localhost:8501`.*
* **Features:**
  * **AI Engine Switcher:** Seamlessly toggle in real time between **Deep RL - PPO Agent (Phase 4)** and **Heuristic MCDM (Phase 3)**.
  * **Adversarial Attack Suite:** Live triggers for Telemetry Spoofing (100% fake battery), Byzantine Equivocation (Double-Signing), Sybil Vote Injection, and Validator Silent Dropping.
  * **Byzantine Defense & Slashing Audit Log:** Real-time table logging security incidents, anomaly detections, and on-chain slashed nodes.
  * **Real-time Fleet Grid:** Color-coded battery bars and role badges (`👑 ROUND LEADER`, `🛡️ VALIDATOR`, `💤 IDLE SLEEP`, `⚠️ QUARANTINED`, `⚔️ SLASHED & BLACKLISTED`).
  * **Comparative Energy Graph:** Real-time plot comparing cumulative energy dissipation of **Adaptive Consensus** vs. **Static PBFT** (showing a 98.3% energy saving for resting nodes).
  * **Live Blockchain Ledger:** Real-time log of committed blocks, state roots, and quorum signatures with active AI engine tags.

### H. (Optional) Generate the Microsoft Word Report
To re-generate the full project documentation document (`.docx`):
```bash
python generate_report_docx.py
```
*Outputs: `AI_Driven_Consensus_Project_Report.docx`.*

---

## 4. System Architecture

The project operates across three strictly decoupled tiers:

```
+-----------------------------------------------------------------------------------+
|                           Tier 1: IoT Device Network                              |
|   - 12-20 virtual ESP32 nodes with individual secp256k1 Ethereum keypairs.        |
|   - First-principles Heinzelman radio model (E_tx ~ d^2/d^4, E_rx, E_cpu).         |
|   - Emits real-time telemetry: [Node ID, Battery %, Latency (ms), Reputation].    |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Telemetry Heartbeat
                                          v
+-----------------------------------------------------------------------------------+
|                        Tier 2: Edge AI Controller & Oracle                        |
|   - Feasibility Filtering: Discards nodes with Battery <= 15% or Trust < 0.60.    |
|   - Dynamic Committee Sizing: Enforces K_t >= 3f + 1.                              |
|   - Multi-Objective Optimization: Maximize U_t = w1*Security + w2*Batt - w3*Lat.  |
|   - Consecutive-Term Fatigue: Rotates leadership to prevent single-node burnout.  |
|   - Computes Quorum Threshold: floor(2/3 * K_t) + 1.                              |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Directives & Threshold Signatures
                                          v
+-----------------------------------------------------------------------------------+
|                     Tier 3: Blockchain Settlement Layer (EVM)                     |
|   - NodeRegistry.sol: Tracks node identities, public keys, and slashing status.   |
|   - AdaptiveConsensus.sol: Verifies threshold ECDSA signatures and commits blocks.|
+-----------------------------------------------------------------------------------+
```

---

## 5. Directory Structure

```text
AI_driven_consensus/
│
├── contracts/                        # TIER 3: Solidity Smart Contracts
│   ├── NodeRegistry.sol              # On-chain node registry & slashing
│   └── AdaptiveConsensus.sol         # Quorum threshold verification & block commitments
│
├── simulator/                        # TIER 1: IoT Network & Physics Simulation
│   ├── models.py                     # Data contracts (Telemetry, Directives, Votes)
│   ├── energy_model.py               # Heinzelman First-Order Radio Model (d^2 / d^4)
│   ├── iot_node.py                   # Virtual ESP32 node with ECDSA signing & discharge
│   ├── fleet_simulator.py            # Multi-node mesh manager & telemetry streaming
│   └── adversarial.py                # Attack injector (Spoofing, Equivocation, Sybil, DoS)
│
├── ai_engine/                        # TIER 2: Intelligent Committee Engine
│   ├── objective.py                  # Multi-Objective MCDM utility function & BFT constraints
│   ├── consensus_env.py              # Gymnasium MDP Environment for RL
│   ├── drl_agent.py                  # Actor-Critic (PPO) Neural Network & Policy
│   ├── train_rl.py                   # PPO Agent Training Script
│   └── defense_detector.py           # Physics-informed anomaly detection & slashing engine
│
├── models/                           # Trained Neural Model Weights
│   └── drl_consensus_agent.pt        # Serialized PyTorch Actor-Critic weights
│
├── bridge/                           # Web3 Orchestration Layer
│   ├── web3_client.py                # Python Web3.py wrapper for EVM JSON-RPC calls
│   └── orchestrator.py               # End-to-end consensus round coordinator with defense
│
├── dashboard/                        # Visual Presentation & Demo UI
│   └── app.py                        # Streamlit dashboard (MCDM/DRL toggle & Adversarial Suite)
│
├── tests/                            # Automated Verification Suites
│   ├── test_math_models.py           # Pytest suite for radio physics & AI math (9 tests)
│   ├── test_drl_agent.py             # Pytest suite for Gym MDP & DRL networks (6 tests)
│   ├── test_adversarial_defense.py   # Pytest suite for Byzantine defense & slashing (11 tests)
│   └── contracts/ConsensusTest.js    # Hardhat test suite for EVM contracts (5 tests)
│
├── run_phase5_pipeline.py            # Phase 5 Adversarial Stress & Slashing Pipeline
├── run_phase4_pipeline.py            # Phase 4 DRL Pipeline Execution Script
├── run_phase3_pipeline.py            # Phase 3 MCDM Prototype Execution Script
├── demo_phase1_phase2.py             # Phase 1 & 2 Math & Physics Demonstration
├── generate_report_docx.py           # Script to generate Word report (.docx)
├── hardhat.config.js                 # Hardhat EVM configuration (Cancun)
├── package.json                      # Node.js dependencies
└── requirements.txt                  # Python dependencies
```

---

## 6. Troubleshooting Common Issues

1. **`mcopy not found` during Hardhat compile:**
   * Ensure `hardhat.config.js` includes `evmVersion: "cancun"` under the Solidity compiler settings (Cancun is required by OpenZeppelin v5).
2. **`ModuleNotFoundError: No module named 'simulator'` in Streamlit:**
   * Handled automatically in `dashboard/app.py` via dynamic root path insertion (`sys.path.insert(0, ...)`).
3. **PowerShell script execution disabled:**
   * Run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in your PowerShell window before activating `venv`.
