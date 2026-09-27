"""
Mathematical formulation of IoT energy consumption based on first-principles radio physics
(Heinzelman First-Order Radio Model) and embedded cryptographic computation overhead.
"""
import math
from enum import Enum
from typing import Dict


class HardwarePreset(Enum):
    ESP32 = "ESP32"
    STM32F4 = "STM32F4"
    NRF52840 = "NRF52840"


class HeinzelmanEnergyModel:
    """
    Implements the Heinzelman first-order radio energy model combined with
    cryptographic processing energy for microcontroller units (MCUs).
    
    Equations:
      E_tx(l, d) = l * E_elec + l * eps_fs * d^2  (if d < d0)
                 = l * E_elec + l * eps_mp * d^4  (if d >= d0)
      E_rx(l)    = l * E_elec
      E_cpu      = V_dd * I_active * T_crypto
    """
    
    # Standard Heinzelman Model Radio Constants (Joules)
    DEFAULT_E_ELEC = 50e-9       # 50 nJ/bit (transceiver electronics)
    DEFAULT_EPS_FS = 10e-12      # 10 pJ/bit/m^2 (free space amplifier)
    DEFAULT_EPS_MP = 0.0013e-12  # 0.0013 pJ/bit/m^4 (multi-path fading amplifier)
    
    # Hardware presets: (V_dd [V], I_active [A], I_sleep [A], T_sign [s], T_verify [s])
    PRESETS: Dict[HardwarePreset, Dict[str, float]] = {
        HardwarePreset.ESP32: {
            "v_dd": 3.3,
            "i_active": 0.160,     # 160 mA
            "i_sleep": 15e-6,      # 15 uA
            "t_sign": 0.0042,      # 4.2 ms for secp256k1 sign
            "t_verify": 0.0085,    # 8.5 ms for secp256k1 verify
        },
        HardwarePreset.STM32F4: {
            "v_dd": 3.3,
            "i_active": 0.025,     # 25 mA
            "i_sleep": 3e-6,       # 3 uA
            "t_sign": 0.0120,      # 12.0 ms
            "t_verify": 0.0240,    # 24.0 ms
        },
        HardwarePreset.NRF52840: {
            "v_dd": 3.0,
            "i_active": 0.008,     # 8 mA
            "i_sleep": 1.5e-6,     # 1.5 uA
            "t_sign": 0.0180,      # 18.0 ms
            "t_verify": 0.0350,    # 35.0 ms
        }
    }

    def __init__(
        self,
        e_elec: float = DEFAULT_E_ELEC,
        eps_fs: float = DEFAULT_EPS_FS,
        eps_mp: float = DEFAULT_EPS_MP,
        hardware: HardwarePreset = HardwarePreset.ESP32
    ):
        self.e_elec = e_elec
        self.eps_fs = eps_fs
        self.eps_mp = eps_mp
        # Crossover distance threshold where multi-path fading takes over
        self.d0 = math.sqrt(self.eps_fs / self.eps_mp)
        
        self.hardware = hardware
        self.hw_params = self.PRESETS[hardware]

    def energy_transmit(self, length_bits: int, distance_m: float) -> float:
        """
        Calculates energy consumed to transmit an l-bit packet over distance d.
        Returns energy in Joules.
        """
        if distance_m < self.d0:
            amp_energy = self.eps_fs * (distance_m ** 2)
        else:
            amp_energy = self.eps_mp * (distance_m ** 4)
            
        return length_bits * (self.e_elec + amp_energy)

    def energy_receive(self, length_bits: int) -> float:
        """
        Calculates energy consumed to receive an l-bit packet.
        Returns energy in Joules.
        """
        return length_bits * self.e_elec

    def energy_crypto_sign(self) -> float:
        """Calculates energy to generate a cryptographic signature (Joules)."""
        power = self.hw_params["v_dd"] * self.hw_params["i_active"]
        return power * self.hw_params["t_sign"]

    def energy_crypto_verify(self) -> float:
        """Calculates energy to verify a cryptographic signature (Joules)."""
        power = self.hw_params["v_dd"] * self.hw_params["i_active"]
        return power * self.hw_params["t_verify"]

    def energy_sleep(self, duration_s: float) -> float:
        """Calculates standby energy during low-power sleep (Joules)."""
        power = self.hw_params["v_dd"] * self.hw_params["i_sleep"]
        return power * duration_s

    def calculate_round_energy(
        self,
        is_validator: bool,
        is_leader: bool,
        committee_size: int,
        distance_m: float = 30.0,
        epoch_duration_s: float = 2.0,
        packet_bits: int = 1024
    ) -> float:
        """
        Calculates total energy dissipated by a node during one consensus round.
        
        If Validator:
          - Leader transmits proposal (8192 bits) to K-1 nodes, receives K-1 votes, verifies K-1 votes.
          - Validator receives proposal, verifies proposal, signs vote, transmits vote, receives K-1 votes.
        If Idle:
          - Only receives 1 commit notification, stays in low-power sleep for epoch_duration.
        """
        if is_leader:
            # Transmit proposal (8192 bits) to (K - 1) members
            proposal_bits = 8192
            e_tx_proposal = (committee_size - 1) * self.energy_transmit(proposal_bits, distance_m)
            # Receive (K - 1) votes
            e_rx_votes = (committee_size - 1) * self.energy_receive(packet_bits)
            # Sign proposal + verify (K - 1) votes
            e_crypto = self.energy_crypto_sign() + (committee_size - 1) * self.energy_crypto_verify()
            return e_tx_proposal + e_rx_votes + e_crypto

        elif is_validator:
            # Receive proposal
            proposal_bits = 8192
            e_rx_proposal = self.energy_receive(proposal_bits)
            # Verify proposal + sign vote
            e_crypto_verify_prop = self.energy_crypto_verify()
            e_crypto_sign_vote = self.energy_crypto_sign()
            # Transmit vote (1024 bits) to leader
            e_tx_vote = self.energy_transmit(packet_bits, distance_m)
            # Receive commit notice (512 bits)
            e_rx_commit = self.energy_receive(512)
            
            return (
                e_rx_proposal +
                e_crypto_verify_prop +
                e_crypto_sign_vote +
                e_tx_vote +
                e_rx_commit
            )
        else:
            # Idle node: receives final block header notice (512 bits), otherwise in low-power sleep
            e_rx_notice = self.energy_receive(512)
            e_sleep = self.energy_sleep(epoch_duration_s)
            return e_rx_notice + e_sleep
