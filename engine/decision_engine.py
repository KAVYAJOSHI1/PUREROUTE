from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import math
import time
from typing import Dict, Any, List, Optional, Tuple

class State(Enum):
    FAULT = "FAULT"
    LOCKED_RO = "LOCKED_RO"
    REPLACE = "REPLACE"
    FLUSH = "FLUSH"
    RO = "RO"
    UF_UV = "UF+UV"

STATE_LED_MAP = {
    State.FAULT: {"color": "Red", "mode": "Solid", "hex": "#FF4B4B"},
    State.LOCKED_RO: {"color": "Blue", "mode": "Blinking", "hex": "#1E90FF"},
    State.REPLACE: {"color": "Yellow", "mode": "Solid", "hex": "#FFD700"},
    State.FLUSH: {"color": "Yellow", "mode": "Blinking", "hex": "#FFA500"},
    State.RO: {"color": "Blue", "mode": "Solid", "hex": "#0072BB"},
    State.UF_UV: {"color": "Green", "mode": "Solid", "hex": "#00C853"}
}

@dataclass
class CalibrationConstants:
    k_flow: float = 5000.0   # Pulses per litre
    v0_turb_mv: float = 2000.0 # Clear water turbidity baseline in mV
    q0_fresh_flow: float = 1.2 # Fresh cartridge flow in L/min
    ec_a: float = 0.0
    ec_b: float = 700000.0   # Cell constant scale: G (Siemens) * 700,000 -> uS/cm
    ec_c: float = 0.0
    rated_litres: float = 50.0 # Bench test rated cartridge volume

@dataclass
class TelemetryFrame:
    t_ms: int
    temp_c: float
    flow_lpm: float
    pulses: int
    turb_mv: float
    turb_index_pct: float
    ec25_uScm: float
    tds_ppm: float
    fhi: float
    counter_life_pct: float
    pump: int
    lock: int
    state: str
    reason: str
    tag: str

    def to_csv_line(self) -> str:
        return (
            f"{self.t_ms},{self.temp_c:.2f},{self.flow_lpm:.2f},{self.pulses},"
            f"{self.turb_mv:.1f},{self.turb_index_pct:.1f},{self.ec25_uScm:.1f},"
            f"{self.tds_ppm:.1f},{self.fhi:.1f},{self.counter_life_pct:.1f},"
            f"{self.pump},{self.lock},{self.state},{self.reason},{self.tag}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "t_ms": self.t_ms,
            "temp_c": self.temp_c,
            "flow_lpm": self.flow_lpm,
            "pulses": self.pulses,
            "turb_mv": self.turb_mv,
            "turb_index_pct": self.turb_index_pct,
            "ec25_uScm": self.ec25_uScm,
            "tds_ppm": self.tds_ppm,
            "fhi": self.fhi,
            "counter_life_pct": self.counter_life_pct,
            "pump": self.pump,
            "lock": self.lock,
            "state": self.state,
            "reason": self.reason,
            "tag": self.tag
        }

class DecisionEngine:
    def __init__(self, cal: Optional[CalibrationConstants] = None):
        self.cal = cal or CalibrationConstants()
        
        # Thresholds from Playbook
        self.t_lo = 10.0      # Turbidity low threshold (%)
        self.t_hi = 25.0      # Turbidity high threshold (%)
        self.turb_margin = 5.0 # Hysteresis margin
        self.ec_switch_in = 500.0  # uS/cm
        self.ec_switch_out = 450.0 # uS/cm
        
        # Operational State
        self.current_state: State = State.UF_UV
        self.candidate_state: Optional[State] = None
        self.candidate_persistence_count: int = 0
        self.required_persistence_seconds: int = 5
        
        # State reason
        self.last_reason: str = "System initialized; standard UF+UV routing"
        self.active_tag: str = "BOOT"
        self.area_lock_active: bool = False
        
        # Fail-safe counters & history
        self.dry_run_seconds: int = 0
        self.leak_seconds: int = 0
        self.fault_clear_seconds: int = 0
        self.active_faults: List[str] = []
        
        # Filter health & Litre tracking
        self.ema_flow: float = 0.0
        self.ema_fhi: float = 100.0
        self.total_litres_dispensed: float = 0.0
        self.fhi_history: deque = deque(maxlen=360) # Store last ~6 minutes for linear fit
        
        # Stuck sensor detection buffers
        self.turb_history: deque = deque(maxlen=30)
        self.ec_history: deque = deque(maxlen=30)
        self.temp_history: deque = deque(maxlen=30)
        
        # Timestamp
        self.start_time = time.time()

    def set_calibration(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.cal, k):
                setattr(self.cal, k, float(v))

    def update_area_lock(self, locked: bool):
        self.area_lock_active = locked

    def set_tag(self, tag: str):
        self.active_tag = tag.strip()

    def reset_baseline_v0(self, current_turb_mv: float):
        if 500.0 <= current_turb_mv <= 4500.0:
            self.cal.v0_turb_mv = current_turb_mv
            return True, f"Baseline V0 saved: {current_turb_mv:.1f} mV"
        return False, f"Invalid V0: {current_turb_mv:.1f} mV out of expected range"

    def reset_baseline_q0(self, current_flow_lpm: float):
        if current_flow_lpm > 0.2:
            self.cal.q0_fresh_flow = current_flow_lpm
            return True, f"Baseline Q0 saved: {current_flow_lpm:.2f} L/min"
        return False, f"Invalid Q0: {current_flow_lpm:.2f} L/min too low"

    def calculate_turb_index(self, turb_mv: float) -> float:
        if self.cal.v0_turb_mv <= 0:
            return 0.0
        ti = 100.0 * (1.0 - (turb_mv / self.cal.v0_turb_mv))
        return max(0.0, min(100.0, ti))

    def calculate_ec25(self, rx_ohms: float, temp_c: float) -> Tuple[float, bool]:
        """
        Bipolar resistance Rx -> G = 1/Rx -> EC = a + bG + cG^2 -> EC25
        """
        if rx_ohms <= 0 or math.isnan(rx_ohms) or math.isinf(rx_ohms):
            return 0.0, False
        g = 1.0 / rx_ohms
        ec = self.cal.ec_a + (self.cal.ec_b * g) + (self.cal.ec_c * (g ** 2))
        t_comp = 1.0 + 0.019 * (temp_c - 25.0)
        if t_comp <= 0:
            return ec, False
        ec25 = ec / t_comp
        return max(0.0, ec25), True

    def calculate_fhi(self, flow_lpm: float) -> float:
        """
        FHI = 100 * clamp(Q / Q0, 0, 1), smoothed with EMA alpha=0.2
        """
        if self.cal.q0_fresh_flow <= 0:
            raw_fhi = 100.0
        else:
            ratio = flow_lpm / self.cal.q0_fresh_flow
            raw_fhi = 100.0 * max(0.0, min(1.0, ratio))
        # EMA smoothing
        alpha = 0.2
        self.ema_fhi = (alpha * raw_fhi) + ((1.0 - alpha) * self.ema_fhi)
        return self.ema_fhi

    def predict_minutes_to_replace(self) -> Optional[float]:
        """
        Fits a simple linear regression to recent FHI history to predict time until FHI < 40.
        """
        if len(self.fhi_history) < 30:
            return None # Need at least 30 samples (~30s)
        
        y = list(self.fhi_history)
        n = len(y)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        num = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        den = sum((x[i] - x_mean) ** 2 for i in range(n))
        if den == 0:
            return None
        slope = num / den # rate of FHI change per second
        
        if slope >= -0.0001:
            return None # FHI not degrading
        
        current_val = y[-1]
        if current_val <= 40.0:
            return 0.0
        
        seconds_left = (40.0 - current_val) / slope
        minutes_left = max(0.0, seconds_left / 60.0)
        return round(minutes_left, 1)

    def check_faults(
        self,
        pump_on: bool,
        flow_lpm: float,
        temp_c: float,
        turb_mv: float,
        rx_ohms: float,
        rx_asym_ratio: float,
        pulses: int
    ) -> List[str]:
        faults = []
        
        # 1. Dry run / no flow: Pump ON and flow < 0.05 L/min for > 3 s
        if pump_on and flow_lpm < 0.05:
            self.dry_run_seconds += 1
            if self.dry_run_seconds >= 3:
                faults.append(f"NO FLOW {self.dry_run_seconds}s with pump ON -> dry run; pump OFF")
        else:
            self.dry_run_seconds = 0

        # 2. Leak or siphon: Flow > 0.1 L/min with pump OFF for > 3 s
        if (not pump_on) and flow_lpm > 0.10:
            self.leak_seconds += 1
            if self.leak_seconds >= 3:
                faults.append(f"LEAK/SIPHON flow {flow_lpm:.2f} L/min with pump OFF > 3s")
        else:
            self.leak_seconds = 0

        # 3. Temperature sensor: Reads -127 or 85 C, or outside 0-50 C
        if temp_c in (-127.0, 85.0) or temp_c < 0.0 or temp_c > 50.0:
            faults.append(f"TEMP SENSOR FAULT (reading {temp_c:.1f} °C)")

        # 4. Turbidity sensor: ADC below 100 mV or above 2400 mV
        if turb_mv < 100.0 or turb_mv > 2400.0:
            faults.append(f"TURBIDITY SENSOR OUT OF RANGE ({turb_mv:.0f} mV)")

        # 5. Conductivity probe in air: Rx > 200 kOhm
        if rx_ohms > 200000.0:
            faults.append("CONDUCTIVITY PROBE IN AIR (Rx > 200 kΩ)")

        # 6. Conductivity probe shorted: Rx < 50 Ohm
        if rx_ohms < 50.0 and rx_ohms > 0.0:
            faults.append(f"CONDUCTIVITY PROBE SHORTED (Rx={rx_ohms:.1f} Ω)")

        # 7. Probe fouled or polarized: Asymmetry > 20%
        if rx_asym_ratio > 0.20:
            faults.append(f"EC PROBE FOULED/POLARIZED (asymmetry {rx_asym_ratio*100:.1f}% > 20%)")

        # 8. Stuck sensor: 30 identical samples while pump runs
        if pump_on:
            self.turb_history.append(turb_mv)
            self.ec_history.append(rx_ohms)
            self.temp_history.append(temp_c)
            if len(self.turb_history) == 30 and (max(self.turb_history) - min(self.turb_history) == 0.0):
                faults.append("STUCK TURBIDITY SENSOR (unchanged for 30 samples)")
            if len(self.ec_history) == 30 and (max(self.ec_history) - min(self.ec_history) == 0.0):
                faults.append("STUCK EC SENSOR (unchanged for 30 samples)")
            if len(self.temp_history) == 30 and (max(self.temp_history) - min(self.temp_history) == 0.0):
                faults.append("STUCK TEMP SENSOR (unchanged for 30 samples)")

        # 9. Flow sensor dead: pump ON, but 0 pulses
        if pump_on and pulses == 0 and self.dry_run_seconds >= 3:
            if "dry run" not in " ".join(faults).lower():
                faults.append("FLOW SENSOR DEAD (pump ON with 0 pulses)")

        return faults

    def process_second(
        self,
        temp_c: float,
        flow_raw: float,
        pulses: int,
        turb_mv: float,
        rx_ohms: float,
        rx_asym: float = 0.0,
        pump_command: int = 1,
        t_ms: Optional[int] = None
    ) -> TelemetryFrame:
        """
        Executes one 1-second iteration of the decision engine.
        """
        if t_ms is None:
            t_ms = int((time.time() - self.start_time) * 1000)

        # 1. Flow smoothing & volume accumulation
        if pulses == 0 and flow_raw <= 0.02:
            self.ema_flow = 0.0
        else:
            alpha_flow = 0.2
            self.ema_flow = (alpha_flow * flow_raw) + ((1.0 - alpha_flow) * self.ema_flow)
        flow_eff = self.ema_flow
        
        # Accumulate volume if pump is running and flow > 0
        if pump_command == 1 and flow_eff > 0.0:
            litres_this_sec = flow_eff / 60.0
            self.total_litres_dispensed += litres_this_sec

        counter_life_pct = max(0.0, 100.0 * (1.0 - (self.total_litres_dispensed / self.cal.rated_litres)))

        # 2. Calculated metrics
        turb_index = self.calculate_turb_index(turb_mv)
        ec25, ec_ok = self.calculate_ec25(rx_ohms, temp_c)
        tds_ppm = ec25 * 0.6
        fhi = self.calculate_fhi(flow_eff)
        self.fhi_history.append(fhi)

        # 3. Fail-safe checks
        active_faults = self.check_faults(
            pump_on=(pump_command == 1),
            flow_lpm=flow_eff,
            temp_c=temp_c,
            turb_mv=turb_mv,
            rx_ohms=rx_ohms,
            rx_asym_ratio=rx_asym,
            pulses=pulses
        )
        self.active_faults = active_faults

        # 4. Determine Raw Target State (Strict Priority Rules)
        raw_state: State
        raw_reason: str
        
        if len(active_faults) > 0:
            raw_state = State.FAULT
            raw_reason = active_faults[0]
        elif self.area_lock_active:
            raw_state = State.LOCKED_RO
            raw_reason = "District flag active; groundwater locked -> RO forced"
        elif fhi < 40.0 or (pump_command == 1 and flow_eff < 0.30):
            raw_state = State.REPLACE
            raw_reason = f"FHI={fhi:.0f}<40 (Q={flow_eff:.2f}/Q0={self.cal.q0_fresh_flow:.2f}) -> REPLACE filter"
        elif turb_index > self.t_hi:
            raw_state = State.FLUSH
            raw_reason = f"TI={turb_index:.0f}%>{self.t_hi:.0f}% -> FLUSH prefilter, protect UF/RO"
        elif (not ec_ok) or ec25 > self.ec_switch_in:
            raw_state = State.RO
            raw_reason = f"EC25={ec25:.0f}>{self.ec_switch_in:.0f} -> RO+UV"
        elif ec25 <= self.ec_switch_in and turb_index < self.t_lo and (not self.area_lock_active):
            raw_state = State.UF_UV
            raw_reason = f"EC25={ec25:.0f}, TI={turb_index:.0f}% -> UF+UV (RO skipped)"
        else:
            # Fallback to RO for safety
            raw_state = State.RO
            raw_reason = f"Default safe route: EC25={ec25:.0f} -> RO+UV"

        # 5. Apply 5-Second Persistence & Hysteresis
        # Check hysteresis exit barriers for currently active state
        can_exit_current = True
        if self.current_state == State.FAULT:
            if len(active_faults) == 0:
                self.fault_clear_seconds += 1
                if self.fault_clear_seconds < 5:
                    can_exit_current = False
            else:
                self.fault_clear_seconds = 0
                can_exit_current = False
        elif self.current_state == State.REPLACE:
            if fhi <= 50.0:
                can_exit_current = False
        elif self.current_state == State.FLUSH:
            if turb_index >= (self.t_hi - self.turb_margin): # 25 - 5 = 20%
                can_exit_current = False
        elif self.current_state == State.RO and raw_state == State.UF_UV:
            if ec25 >= self.ec_switch_out: # Must drop below 450 uS/cm
                can_exit_current = False

        if not can_exit_current:
            target_to_consider = self.current_state
        else:
            target_to_consider = raw_state

        # Check persistence
        if target_to_consider != self.current_state:
            if self.candidate_state == target_to_consider:
                self.candidate_persistence_count += 1
                if self.candidate_persistence_count >= self.required_persistence_seconds:
                    self.current_state = target_to_consider
                    self.last_reason = raw_reason
                    self.candidate_state = None
                    self.candidate_persistence_count = 0
            else:
                self.candidate_state = target_to_consider
                self.candidate_persistence_count = 1
        else:
            self.candidate_state = None
            self.candidate_persistence_count = 0
            self.last_reason = raw_reason

        # Pump output: In FAULT, pump is forced OFF (no dispensing)
        final_pump = 0 if self.current_state == State.FAULT else pump_command

        return TelemetryFrame(
            t_ms=t_ms,
            temp_c=temp_c,
            flow_lpm=flow_eff,
            pulses=pulses,
            turb_mv=turb_mv,
            turb_index_pct=turb_index,
            ec25_uScm=ec25,
            tds_ppm=tds_ppm,
            fhi=fhi,
            counter_life_pct=counter_life_pct,
            pump=final_pump,
            lock=1 if self.area_lock_active else 0,
            state=self.current_state.value,
            reason=self.last_reason,
            tag=self.active_tag
        )
