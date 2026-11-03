#!/usr/bin/env python3
"""
PureRoute v2 — Calibration Helper & Sensor Fitting Suite
Playbook Section: Calibration (Flow K, Bipolar Conductivity Curve, Turbidity Index)
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Any

class CalibrationHelper:
    @staticmethod
    def calculate_flow_k(measured_litres: float, pulse_count: int, duration_sec: float = 60.0) -> Dict[str, Any]:
        """
        Flow Constant K (pulses per litre).
        Playbook: K = pulses ÷ litres. Expect 4,000–6,000.
        """
        if measured_litres <= 0:
            raise ValueError("Measured litres must be greater than zero.")
        k = pulse_count / measured_litres
        flow_lpm = (measured_litres / duration_sec) * 60.0
        return {
            "k_flow": round(k, 1),
            "measured_litres": measured_litres,
            "pulse_count": pulse_count,
            "calculated_flow_lpm": round(flow_lpm, 2),
            "command_arduino": f"K{int(round(k))}",
            "within_expected_range": 3500 <= k <= 6500
        }

    @staticmethod
    def fit_conductivity_curve(
        data_points: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Fits probe conductance G = 1/Rx to reference pen EC (uS/cm):
        EC = a + b*G + c*G^2
        data_points list of dicts: [{'salt_g_per_l': 0.5, 'rx_ohms': 650.0, 'pen_ec_uScm': 820.0}, ...]
        """
        if len(data_points) < 3:
            raise ValueError("At least 3 calibration points required for 2nd order polynomial fit.")

        g_vals = []
        ec_ref_vals = []

        for pt in data_points:
            rx = pt["rx_ohms"]
            if rx <= 0:
                continue
            g = 1.0 / rx # Conductance in Siemens
            ec_ref = pt["pen_ec_uScm"]
            g_vals.append(g)
            ec_ref_vals.append(ec_ref)

        g_arr = np.array(g_vals)
        ec_arr = np.array(ec_ref_vals)

        # 2nd order polynomial fit: EC = c0 + c1*G + c2*G^2
        poly_coeffs = np.polyfit(g_arr, ec_arr, 2)
        c, b, a = poly_coeffs[0], poly_coeffs[1], poly_coeffs[2]

        # Calculate R^2 coefficient of determination
        residuals = ec_arr - np.polyval(poly_coeffs, g_arr)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((ec_arr - np.mean(ec_arr))**2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0

        return {
            "ec_a": round(float(a), 4),
            "ec_b": round(float(b), 4),
            "ec_c": round(float(c), 4),
            "r_squared": round(float(r_squared), 4),
            "num_points": len(data_points),
            "arduino_snippet": f"cal.ecA = {a:.2f}; cal.ecB = {b:.2f}; cal.ecC = {c:.2f};"
        }

    @staticmethod
    def calculate_turbidity_index(current_mv: float, baseline_v0_mv: float) -> float:
        """
        Relative index TI = 100 * (1 - V / V0)
        Never report NTU.
        """
        if baseline_v0_mv <= 0:
            return 0.0
        ti = 100.0 * (1.0 - (current_mv / baseline_v0_mv))
        return max(0.0, min(100.0, round(ti, 1)))

if __name__ == "__main__":
    print("Testing CalibrationHelper:")
    k_res = CalibrationHelper.calculate_flow_k(measured_litres=1.12, pulse_count=5640)
    print(f"K-factor result: {k_res}")

    sample_pts = [
        {"salt_g_per_l": 0.0, "rx_ohms": 2800.0, "pen_ec_uScm": 250.0},
        {"salt_g_per_l": 0.25, "rx_ohms": 1400.0, "pen_ec_uScm": 510.0},
        {"salt_g_per_l": 0.50, "rx_ohms": 820.0, "pen_ec_uScm": 860.0},
        {"salt_g_per_l": 1.00, "rx_ohms": 480.0, "pen_ec_uScm": 1520.0},
        {"salt_g_per_l": 2.00, "rx_ohms": 270.0, "pen_ec_uScm": 2850.0},
    ]
    ec_res = CalibrationHelper.fit_conductivity_curve(sample_pts)
    print(f"Conductivity fit: {ec_res}")
