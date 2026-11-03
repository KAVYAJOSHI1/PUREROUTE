import math
import random
import time
from typing import Dict, Any, Optional
from .decision_engine import DecisionEngine, TelemetryFrame

class WaterRigSimulator:
    """
    Simulates the physical bench rig described in the PureRoute v2 Hardware Playbook:
    - Sensing Cup: DS18B20 temp, optical turbidity sensor, SS304 dual-screw bipolar conductivity probe.
    - Water Loop: Pump, YF-S401 flow meter, sealed cartridge jar, and manometer backpressure proxy tube.
    """
    def __init__(self, engine: DecisionEngine):
        self.engine = engine
        
        # Physical variables (simulated defaults for clean tap water)
        self.temp_c = 24.5
        self.pump_on = 1
        self.flow_lpm = 1.15
        self.turb_mv = 1950.0  # Clear water baseline ~2000 mV -> ~2.5% TI
        self.rx_ohms = 2800.0  # Approx 250 uS/cm
        self.rx_asym = 0.02    # Clean probe symmetry (2%)
        
        # Bench Rig Physical State
        self.manometer_cm = 5.2 # Normal fresh cartridge manometer column (5-6 cm)
        self.cartridge_condition = "FRESH" # FRESH, HALF_CLOGGED, CLOGGED
        
        # Active scenario override
        self.scenario_mode = "CLEAN"
        self.fault_injection: Optional[str] = None
        self.clogging_step = 0
        self.is_clogging_active = False

    def set_scenario(self, scenario_name: str):
        self.scenario_mode = scenario_name
        self.fault_injection = None
        self.is_clogging_active = False

        if scenario_name == "CLEAN":
            self.temp_c = 24.5
            self.pump_on = 1
            self.flow_lpm = 1.15
            self.turb_mv = 1950.0 # ~2.5% TI (<10%)
            self.rx_ohms = 2800.0 # ~250 uS/cm (<500)
            self.rx_asym = 0.02
            self.manometer_cm = 5.2
            self.cartridge_condition = "FRESH"
            self.engine.set_tag("CLEAN_TAP")

        elif scenario_name == "RO_OUTPUT":
            # Real water: RO output / permeate (lowest conductivity)
            self.temp_c = 24.2
            self.pump_on = 1
            self.flow_lpm = 1.16
            self.turb_mv = 1990.0 # ~0.5% TI
            self.rx_ohms = 32000.0 # ~25 uS/cm
            self.rx_asym = 0.01
            self.manometer_cm = 5.0
            self.cartridge_condition = "FRESH"
            self.engine.set_tag("RO_PERMEATE")

        elif scenario_name == "RO_REJECT":
            # Real water: RO reject waste line (highest conductivity)
            self.temp_c = 25.5
            self.pump_on = 1
            self.flow_lpm = 1.10
            self.turb_mv = 1920.0 # ~4.0% TI
            self.rx_ohms = 290.0 # ~1850 uS/cm (>500)
            self.rx_asym = 0.03
            self.manometer_cm = 5.4
            self.cartridge_condition = "FRESH"
            self.engine.set_tag("RO_REJECT")

        elif scenario_name == "BOTTLED":
            # Real water: Packaged mineral water
            self.temp_c = 23.8
            self.pump_on = 1
            self.flow_lpm = 1.15
            self.turb_mv = 1980.0 # ~1.0% TI
            self.rx_ohms = 4500.0 # ~140 uS/cm (<500)
            self.rx_asym = 0.02
            self.manometer_cm = 5.1
            self.cartridge_condition = "FRESH"
            self.engine.set_tag("BOTTLED_WATER")

        elif scenario_name == "BOREWELL":
            # Real water: Borewell / hand pump (medium to high mineral content)
            self.temp_c = 23.5
            self.pump_on = 1
            self.flow_lpm = 1.08
            self.turb_mv = 1840.0 # ~8.0% TI (<10%)
            self.rx_ohms = 720.0  # ~720 uS/cm (>500)
            self.rx_asym = 0.04
            self.manometer_cm = 5.6
            self.cartridge_condition = "FRESH"
            self.engine.set_tag("BOREWELL_PUMP")

        elif scenario_name == "RAIN_TANKER":
            # Real water: Rain or tanker water
            self.temp_c = 24.8
            self.pump_on = 1
            self.flow_lpm = 1.12
            self.turb_mv = 1760.0 # ~12% TI (>10% -> triggers safe RO fallback)
            self.rx_ohms = 2100.0 # ~320 uS/cm
            self.rx_asym = 0.03
            self.manometer_cm = 5.3
            self.cartridge_condition = "FRESH"
            self.engine.set_tag("RAIN_TANKER")

        elif scenario_name == "SALTY_1G":
            # 1 g/L table salt in 1 L (~1500 uS/cm EC)
            self.temp_c = 25.0
            self.pump_on = 1
            self.flow_lpm = 1.10
            self.turb_mv = 1930.0
            self.rx_ohms = 600.0  # ~850 uS/cm (>500)
            self.rx_asym = 0.03
            self.manometer_cm = 5.3
            self.cartridge_condition = "FRESH"
            self.engine.set_tag("SALTY_1G")

        elif scenario_name == "SALTY_2G":
            # 2 g/L table salt (~2800 uS/cm EC)
            self.temp_c = 25.2
            self.pump_on = 1
            self.flow_lpm = 1.05
            self.turb_mv = 1900.0
            self.rx_ohms = 320.0  # ~1600 uS/cm
            self.rx_asym = 0.03
            self.manometer_cm = 5.5
            self.cartridge_condition = "FRESH"
            self.engine.set_tag("SALTY_2G")

        elif scenario_name == "TURBIDITY_SPIKE":
            # Muddy spike: TI > 25% -> FLUSH
            self.temp_c = 24.0
            self.pump_on = 1
            self.flow_lpm = 0.95
            self.turb_mv = 1200.0 # TI = 100 * (1 - 1200/2000) = 40% > 25%
            self.rx_ohms = 2500.0
            self.rx_asym = 0.02
            self.manometer_cm = 6.2
            self.cartridge_condition = "FRESH"
            self.engine.set_tag("TURB_SPIKE")

        elif scenario_name == "SALTY_AND_MUDDY":
            # Salty + Muddy combined
            self.temp_c = 24.6
            self.pump_on = 1
            self.flow_lpm = 0.92
            self.turb_mv = 1250.0 # TI = 37.5% > 25% -> FLUSH
            self.rx_ohms = 450.0  # ~1200 uS/cm
            self.rx_asym = 0.04
            self.manometer_cm = 6.8
            self.cartridge_condition = "FRESH"
            self.engine.set_tag("SALT_MUDDY")

        elif scenario_name == "CLOGGING_RAMP":
            self.is_clogging_active = True
            self.clogging_step = 0
            self.flow_lpm = 1.15
            self.turb_mv = 1950.0
            self.rx_ohms = 2800.0
            self.manometer_cm = 5.2
            self.cartridge_condition = "RAMPING"
            self.engine.set_tag("CLOG_RAMP")

    def inject_fault(self, fault_type: str):
        self.fault_injection = fault_type
        self.engine.set_tag(f"FAULT_{fault_type.upper()}")

        if fault_type == "dry_run":
            # Lift pump out of water: Pump is ON but 0 flow
            self.pump_on = 1
            self.flow_lpm = 0.0
            self.manometer_cm = 0.0
        elif fault_type == "leak_siphon":
            # Siphon: Pump is OFF but water moves through tube
            self.pump_on = 0
            self.flow_lpm = 0.35
            self.manometer_cm = 2.0
        elif fault_type == "temp_unplugged":
            # DS18B20 wire unplugged
            self.temp_c = -127.0
        elif fault_type == "temp_read_early":
            # Read before 750ms conversion complete
            self.temp_c = 85.0
        elif fault_type == "temp_overheat":
            # Temperature outside safe operating range (0-50 C)
            self.temp_c = 58.0
        elif fault_type == "turb_unplugged":
            # Signal wire pulled -> 0 mV (< 100 mV)
            self.turb_mv = 0.0
        elif fault_type == "turb_saturated":
            # High voltage saturation (> 2400 mV)
            self.turb_mv = 3200.0
        elif fault_type == "ec_air":
            # Probe lifted out of cup (Rx > 200 kOhm)
            self.rx_ohms = 350000.0
        elif fault_type == "ec_short":
            # Screws touched together (Rx < 50 Ohm)
            self.rx_ohms = 12.0
        elif fault_type == "ec_fouled":
            # Asymmetry > 20%
            self.rx_asym = 0.35
        elif fault_type == "stuck_sensor":
            # Reading fixed for 30 consecutive samples
            self.turb_mv = 1950.0
            self.rx_ohms = 2800.0
            self.temp_c = 24.5
        elif fault_type == "flow_dead":
            # Flow signal wire unplugged while pump running
            self.pump_on = 1
            self.flow_lpm = 0.0
            self.manometer_cm = 8.0

    def clear_faults(self):
        self.fault_injection = None
        self.set_scenario("CLEAN")

    def step(self) -> TelemetryFrame:
        # Progress clogging ramp if active
        if self.is_clogging_active:
            self.clogging_step += 1
            # Progressive 30-second ramp:
            # Step 0-10: Fresh jar (1.15 -> 0.90 L/min, manometer 5 -> 10 cm)
            # Step 10-20: Half-clogged jar (0.90 -> 0.50 L/min, manometer 10 -> 18 cm)
            # Step 20-30: Clogged jar (0.50 -> 0.22 L/min, manometer 18 -> 26 cm)
            decay = max(0.22, 1.15 - (self.clogging_step * 0.034))
            self.flow_lpm = decay
            self.manometer_cm = min(28.0, 5.0 + (self.clogging_step * 0.8))
            if self.flow_lpm > 0.8:
                self.cartridge_condition = "FRESH"
            elif self.flow_lpm > 0.4:
                self.cartridge_condition = "HALF_CLOGGED"
            else:
                self.cartridge_condition = "CLOGGED"

        # Add realistic minor analog jitter unless in a pinned fault mode
        jitter_temp = self.temp_c
        jitter_turb = self.turb_mv
        jitter_rx = self.rx_ohms

        if self.fault_injection != "stuck_sensor":
            if self.temp_c not in (-127.0, 85.0):
                jitter_temp += random.uniform(-0.04, 0.04)
            if self.turb_mv > 0.0 and self.turb_mv < 3000.0:
                jitter_turb += random.uniform(-1.5, 1.5)
            if 100.0 < self.rx_ohms < 100000.0:
                jitter_rx += random.uniform(-4.0, 4.0)
        
        # Calculate pulse count from flow: pulses = flow_lpm * K / 60
        pulses = int((self.flow_lpm * self.engine.cal.k_flow) / 60.0) if self.flow_lpm > 0.02 else 0

        frame = self.engine.process_second(
            temp_c=jitter_temp,
            flow_raw=self.flow_lpm,
            pulses=pulses,
            turb_mv=jitter_turb,
            rx_ohms=jitter_rx,
            rx_asym=self.rx_asym,
            pump_command=self.pump_on
        )
        return frame
