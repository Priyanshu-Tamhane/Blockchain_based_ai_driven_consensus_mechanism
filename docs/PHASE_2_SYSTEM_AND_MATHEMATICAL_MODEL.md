# Phase 2: System Modeling & Mathematical Formulations

## 1. System Architecture Overview

The system operates across three strictly decoupled architectural boundaries:

```
+-----------------------------------------------------------------------------------+
|                           Tier 1: IoT Device Network                              |
|   N virtual/physical IoT nodes executing cryptographic primitives and telemetry.  |
|   State per node: e_i(t) in [0, 100]%, Latency l_i in ms, Reputation R_i in [0, 1]  |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Real-time Telemetry: T_i = (ID, e_i, l_i, R_i)
                                          v
+-----------------------------------------------------------------------------------+
|                        Tier 2: Edge AI Controller & Oracle                        |
|   - Ingests telemetry vector T = [T_1, T_2, ..., T_N]                             |
|   - Filters unviable nodes (e_i <= E_threshold or R_i < R_min)                    |
|   - Determines optimal committee size K_t in [K_min, K_max]                       |
|   - Solves Multi-Objective Utility Function U_t to elect committee C_t            |
|   - Submits epoch validator list C_t to Tier 3 via Web3 JSON-RPC                  |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Epoch Directive & Quorum Specification
                                          v
+-----------------------------------------------------------------------------------+
|                     Tier 3: Blockchain Settlement Layer (EVM)                     |
|   - NodeRegistry.sol: Identity, public keys, slashing rules, and stake ledger    |
|   - AdaptiveConsensus.sol: Enforces >= (2/3 * K_t + 1) ECDSA threshold signatures |
|   - Finalizes immutable blocks and logs consensus events                          |
+-----------------------------------------------------------------------------------+
```

---

## 2. Mathematical Energy Depletion Model

Consensus energy consumption per round is formulated based on the first-principles Heinzelman First-Order Radio Model augmented with embedded cryptographic execution energy:

### 2.1 Radio Transmission Energy ($E_{tx}$)
The energy required for node $i$ to transmit an $l$-bit message over Euclidean distance $d$ to a receiver is:

$$E_{tx}(l, d) = l \cdot E_{elec} + l \cdot \epsilon_{amp} \cdot d^\gamma$$

Where:
* $l$: Packet length in bits (e.g., block proposal $\approx 1024$ bytes $= 8192$ bits; vote packet $\approx 128$ bytes $= 1024$ bits).
* $E_{elec}$: Transmitter electronic energy per bit ($50\text{ nJ/bit}$ or $0.05\text{ }\mu\text{J/bit}$).
* $\epsilon_{amp}$: Radio amplifier energy dissipation ($100\text{ pJ/bit/m}^2$ for free space $\gamma = 2$, or $0.0013\text{ pJ/bit/m}^4$ for multi-path fading $\gamma = 4$).
* $d$: Transmission distance in meters.
* $\gamma$: Path loss exponent ($2 \le \gamma \le 4$).

### 2.2 Radio Reception Energy ($E_{rx}$)
The energy required to receive an $l$-bit message:

$$E_{rx}(l) = l \cdot E_{elec}$$

Where $E_{elec} = 50\text{ nJ/bit}$.

### 2.3 Cryptographic CPU Energy ($E_{cpu}$)
The energy consumed during cryptographic signing or ECDSA verification:

$$E_{cpu} = P_{cpu} \cdot T_{crypto} = (V_{dd} \cdot I_{active}) \cdot T_{crypto}$$

Where:
* $V_{dd} = 3.3\text{ V}$ (operating voltage).
* $I_{active}$: Current draw during active crypto execution (e.g., $160\text{ mA}$ for ESP32 $\implies P_{cpu} = 0.528\text{ W}$).
* $T_{crypto}$: Duration of secp256k1 ECDSA signature generation ($\approx 4.2\text{ ms}$ on 240 MHz MCU) or verification ($\approx 8.5\text{ ms}$).

### 2.4 Aggregate Round Energy ($E_{round}^{(i)}$)
For node $i$ in consensus round $t$:

$$E_{round}^{(i)} = M_{tx}^{(i)} \cdot E_{tx}(l_{msg}, d) + M_{rx}^{(i)} \cdot E_{rx}(l_{msg}) + N_{sign}^{(i)} \cdot E_{sign} + N_{verify}^{(i)} \cdot E_{verify}$$

* **If node $i$ is in Committee $\mathcal{C}_t$:** $M_{tx} \ge 1$, $M_{rx} = K_t - 1$, $N_{sign} \ge 1$, $N_{verify} \ge K_t - 1$. High discharge.
* **If node $i$ is Idle (Non-validator):** $M_{tx} = 0$, $M_{rx} = 1$ (listens only to final block commitment announcement), $E_{cpu} \approx 0$. Ultra-low discharge.

---

## 3. Dynamic Multi-Objective Optimization Problem

Let $\mathcal{N} = \{1, 2, \dots, N\}$ be the universe of available IoT nodes.
At epoch $t$, the controller selects a committee $\mathcal{C}_t \subset \mathcal{N}$ of size $|\mathcal{C}_t| = K_t$.

### 3.1 Objective Function Formulation
The AI controller optimizes $\mathcal{C}_t$ by maximizing the global system utility $U_t$:

$$\max_{\mathcal{C}_t \subset \mathcal{N}} U_t(\mathcal{C}_t) = w_1 \cdot \mathcal{S}(\mathcal{C}_t) + w_2 \cdot \overline{E}_{rem}(\mathcal{C}_t) - w_3 \cdot \mathcal{L}(\mathcal{C}_t)$$

Where:
1. **Aggregated Security & Reputation Score:**
   $$\mathcal{S}(\mathcal{C}_t) = \frac{1}{|\mathcal{C}_t|} \sum_{i \in \mathcal{C}_t} R^{(i)}_t$$
   $R^{(i)}_t \in [0, 1]$ represents node $i$'s normalized reputation score based on past consensus honesty.

2. **Normalized Average Residual Battery:**
   $$\overline{E}_{rem}(\mathcal{C}_t) = \frac{1}{|\mathcal{C}_t|} \sum_{i \in \mathcal{C}_t} \left(\frac{e^{(i)}_t}{E_{max}}\right)$$
   $e^{(i)}_t$ is the residual battery in Joules or percentage ($[0, 100]\%$).

3. **Normalized Average Link Latency:**
   $$\mathcal{L}(\mathcal{C}_t) = \frac{1}{|\mathcal{C}_t|} \sum_{i \in \mathcal{C}_t} \left(\frac{L^{(i)}_t - L_{min}}{L_{max} - L_{min}}\right)$$
   $L^{(i)}_t$ is round-trip propagation latency in milliseconds.

4. **Weight Normalization Constraint:**
   $$w_1, w_2, w_3 \in [0, 1], \quad \sum_{j=1}^{3} w_j = 1.0$$

---

## 4. Byzantine Fault Tolerance Safety Invariant

Under classical BFT, a network with total size $N$ can tolerate at most $f$ Byzantine (malicious or offline) nodes if and only if:

$$N \ge 3f + 1$$

In our adaptive scheme, the consensus voting occurs exclusively within the selected dynamic committee $\mathcal{C}_t$ of size $K_t$.

### Theorem 1: Dynamic Committee Safety Invariant
To ensure safety (no two conflicting blocks can both achieve quorum) and liveness (the committee can always finalize a valid block), the committee size $K_t$ must strictly satisfy:

$$K_t \ge 3f_{c} + 1$$

where $f_c$ is the maximum number of tolerated Byzantine nodes within committee $\mathcal{C}_t$.

### Quorum Requirement
For any proposed block in epoch $t$ to be accepted by the smart contract `AdaptiveConsensus.sol`, it must receive $Q_t$ cryptographically valid ECDSA signatures:

$$Q_t = \left\lfloor \frac{2}{3} K_t \right\rfloor + 1$$

### Feasibility Constraints
A node $i$ can be admitted to candidate set $\mathcal{A}_t$ if and only if all three feasibility conditions hold:
1. **Battery Safe-Zone:** $e_i(t) > E_{threshold}$ (where $E_{threshold} = 15\%$). Nodes with $\le 15\%$ battery are immediately quarantined from consensus duties to prevent node death.
2. **Trust Floor:** $R_i(t) \ge R_{min}$ (where $R_{min} = 0.60$). Prevents suspect or unproven nodes from entering quorum.
3. **Availability:** Node $i$ responded to the most recent telemetry heartbeat within window $\tau_{max}$.

---

## 5. Summary of Mathematical Parameters

| Parameter | Symbol | Value | Unit |
| :--- | :--- | :--- | :--- |
| Electronics Energy | $E_{elec}$ | $50 \times 10^{-9}$ | $\text{J/bit}$ |
| Free-space Amplifier Energy | $\epsilon_{fs}$ | $10 \times 10^{-12}$ | $\text{J/bit/m}^2$ |
| Path-loss Amplifier Energy | $\epsilon_{mp}$ | $0.0013 \times 10^{-12}$ | $\text{J/bit/m}^4$ |
| Path-loss Distance Threshold | $d_0 = \sqrt{\epsilon_{fs}/\epsilon_{mp}}$ | $\approx 87$ | $\text{m}$ |
| Battery Threshold Floor | $E_{threshold}$ | $15$ | $\%$ |
| Minimum Reputation Floor | $R_{min}$ | $0.6$ | $[0, 1]$ scale |
| Security Weight | $w_1$ | $0.35$ | Dimensionless |
| Energy Weight | $w_2$ | $0.45$ | Dimensionless |
| Latency Weight | $w_3$ | $0.20$ | Dimensionless |
