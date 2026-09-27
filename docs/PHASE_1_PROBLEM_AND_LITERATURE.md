# Phase 1: Problem Definition & Comprehensive Literature Review

## 1. Executive Summary
This document formalizes **Phase 1** of the *AI-Based Adaptive Consensus Mechanism for Energy-Efficient Blockchain IoT Networks*. It articulates the fundamental tension between distributed consensus guarantees and physical Internet of Things (IoT) hardware constraints, surveys existing consensus paradigms, and formalizes the research gap that motivates this project.

---

## 2. IoT Hardware & Communication Constraints

IoT deployments typically consist of low-power microcontrollers operating over resource-constrained wireless personal/wide area networks (WPAN/LPWAN). 

### 2.1 Microcontroller Constraints Profile
Typical IoT edge nodes (e.g., Espressif ESP32, STMicroelectronics STM32 / ARM Cortex-M4, Nordic nRF52840) operate under severe computational and thermodynamic envelopes:

| Device | Core Architecture | Clock Speed | SRAM | Typical Battery Supply | Active Current (Tx/Compute) | Sleep Current |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ESP32** | Xtensa Dual-core 32-bit LX6 | 160–240 MHz | 520 KB | 2500 mAh (Li-ion) | 160–260 mA | 10–150 $\mu$A |
| **STM32F401** | ARM Cortex-M4 (w/ FPU) | 84 MHz | 96 KB | 2x AA (2000 mAh) | 15–25 mA | 2.5 $\mu$A |
| **nRF52840** | ARM Cortex-M4 (BLE/802.15.4) | 64 MHz | 256 KB | CR2032 (220 mAh) | 4.8–15 mA | 1.5 $\mu$A |

### 2.2 Wireless Radio Constraints (LPWAN & WPAN)
Consensus protocols rely on network broadcasts to reach agreement. In IoT, radio transmission dominates total power consumption by several orders of magnitude compared to CPU execution:
* **LoRaWAN:** Data rate 0.3 kbps to 50 kbps; duty-cycle limits (1% in EU868); payload limit 51–222 bytes. High message complexity immediately leads to channel saturation and packet drops.
* **Zigbee / IEEE 802.15.4:** Data rate 250 kbps at 2.4 GHz; maximum physical payload 127 bytes. Mesh routing overhead causes exponential latency growth under broadcast traffic.
* **Bluetooth Low Energy (BLE):** Point-to-point or mesh; limited packet MTU (~23–247 bytes); high power draw when maintaining active peer-to-peer scanning states.
* **NB-IoT:** Cellular uplink; high latency (1.5 to 10 seconds per message); cellular modem power spikes up to 200 mA during transmission.

---

## 3. Critical Analysis of Existing Consensus Protocols in IoT

Traditional blockchain consensus mechanisms fail when applied directly to IoT networks. Below is a comparative critique:

### 3.1 Proof of Work (PoW)
* **Mechanics:** Nodes repeatedly compute SHA-256 or Ethash hash puzzles until finding a digest below a target difficulty.
* **Failure in IoT:** 
  * Running an ESP32 at 240 MHz continuously computing SHA-256 draws ~240 mA. A 2500 mAh battery will fully deplete in under **10.4 hours** without transmitting a single useful piece of sensor data.
  * Massive compute disparity: Any ASIC or GPU node can instantly execute a 51% attack against an IoT mining pool.

### 3.2 Classical Practical Byzantine Fault Tolerance (PBFT)
* **Mechanics:** Leader proposes a block; network executes three phases: `Pre-Prepare`, `Prepare`, and `Commit`. Each phase requires every node to broadcast its vote to all other $N-1$ nodes.
* **Failure in IoT:**
  * **Communication Complexity:** $\mathcal{O}(N^2)$ message exchanges per consensus round.
    * For $N = 20$ nodes: 400 messages/round.
    * For $N = 100$ nodes: 10,000 messages/round.
  * **The Broadcast Storm:** Over low-power radios (e.g., Zigbee or LoRa), 10,000 broadcast packets cause continuous RF collisions, hidden terminal problems, packet drops exceeding 60%, and rapid battery exhaustion from transceiver duty-cycle saturation.

### 3.3 Proof of Stake (PoS) & Delegated PoS (DPoS)
* **Mechanics:** Validators are selected proportionally to staked financial capital. In DPoS, token holders vote for a static set of delegates (e.g., 21 delegates in EOS).
* **Failure in IoT:**
  * **Plutocratic Stagnation:** IoT sensors do not naturally hold large liquid balances of cryptocurrency.
  * **Energy Blindness:** Traditional PoS algorithms are completely unaware of physical device state. If a validator node has 2% battery remaining, PoS will continue assigning it validation and block generation duties until the device dies, causing permanent sensor loss and network partitioning.

---

## 4. State-of-the-Art Literature Survey

| Approach / Paper | Technique | Strengths | Critical Limitations |
| :--- | :--- | :--- | :--- |
| **Dorri et al. (LSB - 2017)** | Lightweight Scalable Blockchain; cluster heads handle local consensus. | Eliminates PoW for sensors; reduces message hops. | Static cluster heads become single points of failure (SPOF) and experience rapid localized battery death. |
| **Kang et al. (2019)** | Delegated BFT with reputation-based voting in edge computing. | Replaces financial stake with historical task reputation. | Does not model real-time physical battery drain or radio propagation latency dynamically. |
| **Huang et al. (Credit-BFT, 2020)** | Credit-based PBFT selecting dynamic leader based on transaction volume. | Lowers latency; penalizes faulty leaders. | Committee size remains static ($N$ nodes or fixed $K$); no protection for depleted peripheral nodes. |
| **Adaptive RL Consensus (Recent Works, 2022–2024)** | Reinforcement learning for transaction sharding and throughput tuning. | High throughput in high-compute server environments. | Evaluated purely in data-center simulations; ignores physical IoT transceiver physics ($E_{tx} \propto d^2$). |

---

## 5. Identified Research Gap & Project Thesis

### 5.1 The Gap
Existing literature bifurcates into two extremes:
1. **Blockchain-Centric Solutions:** Focus on cryptographic proofs and throughput, treating edge nodes as homogeneous compute units with infinite wall-power.
2. **IoT-Centric Solutions:** Sacrifice decentralization entirely by introducing a centralized cloud gateway (AWS/Azure) that aggregates data and writes to the blockchain on behalf of devices, reintroducing single points of failure and trust bottlenecks.

### 5.2 The Project Thesis
> **Thesis:** *By introducing an intelligent off-chain edge controller that continuously evaluates multi-dimensional device telemetry (residual energy, link latency, historical honesty) and dynamically adapts the consensus committee size ($K_t$) and member rotation, we can preserve Byzantine fault tolerance ($K_t \ge 3f + 1$) while significantly extending the operational lifespan (First Node Dead metric) of the IoT network.*
