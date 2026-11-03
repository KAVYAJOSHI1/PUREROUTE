#!/usr/bin/env python3
"""
PureRoute v2 — Automated Logic & Verification Test Suite
Executes the 5 tests specified in PureRoute v2 Decision Engine Playbook Page 9:
1. Clogging ramp test (Fresh -> Half -> Clogged; FHI vs litre counter)
2. Water classification matrix (Clean, Salty 1g/2g, Muddy, Salty+Muddy)
3. Area Lock & Evidence-based Unlock logic test
4. Fault injection timing test (detection time & recovery time)
5. Repeatability test (Mean, SD, CV%)
"""

import math
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from engine.decision_engine import DecisionEngine, State
from engine.lock_module import AreaLockEngine
from engine.simulator import WaterRigSimulator

class PlaybookTestRunner:
    def __init__(self):
        self.lock_engine = AreaLockEngine("district_risk.csv")

    def run_clogging_ramp_test(self) -> Dict[str, Any]:
        """
        Playbook Test 1: Clogging Ramp
        Fresh -> half -> clogged cartridge.
        Records: FHI and litre-counter curves; seconds to REPLACE.
        """
        engine = DecisionEngine()
        sim = WaterRigSimulator(engine)
        sim.set_scenario("CLOGGING_RAMP")
        
        fhi_curve = []
        counter_curve = []
        flow_curve = []
        seconds_to_replace = None

        for t in range(35):
            frame = sim.step()
            fhi_curve.append(frame.fhi)
            counter_curve.append(frame.counter_life_pct)
            flow_curve.append(frame.flow_lpm)

            if frame.state == "REPLACE" and seconds_to_replace is None:
                seconds_to_replace = t

        return {
            "test_name": "Clogging Ramp Test",
            "passed": seconds_to_replace is not None and seconds_to_replace > 5,
            "seconds_to_replace": seconds_to_replace,
            "final_fhi": round(fhi_curve[-1], 1),
            "final_counter_life": round(counter_curve[-1], 1),
            "contrast_demonstrated": f"FHI dropped to {fhi_curve[-1]:.1f}% while legacy litre counter showed falsely confident {counter_curve[-1]:.1f}%",
            "fhi_curve": [round(x, 1) for x in fhi_curve],
            "counter_curve": [round(x, 1) for x in counter_curve],
            "flow_curve": [round(x, 2) for x in flow_curve]
        }

    def run_classification_matrix(self) -> Dict[str, Any]:
        """
        Playbook Test 2: Classification Matrix
        Clean, salty 1g/L, salty 2g/L, muddy, salty + muddy.
        Records: Expected vs actual state/LED, detection rate, false alarms.
        """
        test_cases = [
            {"name": "Clean Tap", "scenario": "CLEAN", "expected_state": "UF+UV", "expected_led": "Green"},
            {"name": "Salty 1 g/L", "scenario": "SALTY_1G", "expected_state": "RO", "expected_led": "Blue"},
            {"name": "Salty 2 g/L", "scenario": "SALTY_2G", "expected_state": "RO", "expected_led": "Blue"},
            {"name": "Muddy Spike", "scenario": "TURBIDITY_SPIKE", "expected_state": "FLUSH", "expected_led": "Yellow"},
            {"name": "Salty + Muddy", "scenario": "SALTY_AND_MUDDY", "expected_state": "FLUSH", "expected_led": "Yellow"},
        ]

        results = []
        correct_count = 0
        total_runs = 0

        for tc in test_cases:
            engine = DecisionEngine()
            sim = WaterRigSimulator(engine)
            sim.set_scenario(tc["scenario"])
            
            # Run for 7 seconds to satisfy 5s persistence
            final_frame = None
            for _ in range(7):
                final_frame = sim.step()
                total_runs += 1

            actual_state = final_frame.state
            is_match = (actual_state == tc["expected_state"])
            if is_match:
                correct_count += 1

            results.append({
                "sample": tc["name"],
                "expected": tc["expected_state"],
                "actual": actual_state,
                "reason": final_frame.reason,
                "ec25": final_frame.ec25_uScm,
                "turb_index": final_frame.turb_index_pct,
                "match": is_match
            })

        detection_rate = (correct_count / len(test_cases)) * 100.0
        return {
            "test_name": "Classification Matrix Test",
            "passed": detection_rate >= 100.0,
            "detection_rate_pct": detection_rate,
            "false_alarms_on_clean": 0 if results[0]["match"] else 1,
            "details": results
        }

    def run_lock_logic_test(self) -> Dict[str, Any]:
        """
        Playbook Test 3: Lock Logic Test
        Set As flag -> failing test -> passing test -> move clock past expiry.
        """
        steps = []
        now = datetime.now()

        # Step 1: Bareilly/Ballia groundwater with no test
        locked, reason = self.lock_engine.evaluate_lock("Ballia", "groundwater", None, now)
        steps.append({"step": "1. Area Flag Active, No Test", "locked": locked, "expected_locked": True, "reason": reason})

        # Step 2: Test strip attempt for Arsenic (Must be rejected)
        test_strip = {"source": "test_strip", "date": now.strftime("%Y-%m-%d"), "values": {"arsenic": 5.0}}
        locked, reason = self.lock_engine.evaluate_lock("Ballia", "groundwater", test_strip, now)
        steps.append({"step": "2. Arsenic Test Strip (Advisory Only)", "locked": locked, "expected_locked": True, "reason": reason})

        # Step 3: Failing lab test result (As = 18 ug/L > 10)
        failing_test = {"source": "accredited_lab", "date": now.strftime("%Y-%m-%d"), "values": {"arsenic": 18.0, "nitrate": 20.0}}
        locked, reason = self.lock_engine.evaluate_lock("Ballia", "groundwater", failing_test, now)
        steps.append({"step": "3. Failing Lab Test (As=18 ug/L > 10)", "locked": locked, "expected_locked": True, "reason": reason})

        # Step 4: Passing lab test result (As = 4 ug/L < 10)
        passing_test = {"source": "accredited_lab", "date": now.strftime("%Y-%m-%d"), "values": {"arsenic": 4.0, "nitrate": 25.0}}
        locked, reason = self.lock_engine.evaluate_lock("Ballia", "groundwater", passing_test, now)
        steps.append({"step": "4. Passing Certified Test (As=4 ug/L)", "locked": locked, "expected_locked": False, "reason": reason})

        # Step 5: Advance clock 7 months (> 180 days -> expired)
        future_date = now + timedelta(days=210)
        locked, reason = self.lock_engine.evaluate_lock("Ballia", "groundwater", passing_test, future_date)
        steps.append({"step": "5. Expired Test (> 6 months)", "locked": locked, "expected_locked": True, "reason": reason})

        all_matched = all(s["locked"] == s["expected_locked"] for s in steps)
        return {
            "test_name": "Area Lock & Unlock Logic Test",
            "passed": all_matched,
            "steps": steps
        }

    def run_fault_injection_benchmark(self) -> Dict[str, Any]:
        """
        Playbook Test 4: Fault Injection Timing
        Runs every fail-safe check, logging detection time and recovery time.
        """
        faults_to_test = [
            ("dry_run", "Dry run / no flow"),
            ("leak_siphon", "Leak or siphon"),
            ("temp_unplugged", "Temp sensor unplugged"),
            ("turb_unplugged", "Turbidity sensor out of range"),
            ("ec_air", "EC probe in air"),
            ("ec_short", "EC probe shorted"),
            ("ec_fouled", "EC probe fouled / polarized"),
        ]

        results = []
        for f_key, f_label in faults_to_test:
            engine = DecisionEngine()
            sim = WaterRigSimulator(engine)
            sim.set_scenario("CLEAN")

            # Stabilize in CLEAN
            for _ in range(6):
                sim.step()

            # Inject fault
            sim.inject_fault(f_key)
            detected_sec = None
            for t in range(1, 15):
                frame = sim.step()
                if frame.state == "FAULT":
                    detected_sec = t
                    break

            # Clear fault and measure recovery time (exit hysteresis requires 5s)
            sim.clear_faults()
            recovered_sec = None
            for t in range(1, 15):
                frame = sim.step()
                if frame.state != "FAULT":
                    recovered_sec = t
                    break

            results.append({
                "fault": f_label,
                "detected": detected_sec is not None,
                "detection_time_s": detected_sec or 99,
                "recovery_time_s": recovered_sec or 99,
                "pump_stopped": (frame.pump == 0 if frame.state == "FAULT" else True)
            })

        all_detected = all(r["detected"] for r in results)
        return {
            "test_name": "Fault Injection Timing Benchmark",
            "passed": all_detected,
            "results": results
        }

    def run_repeatability_test(self, n_runs: int = 10) -> Dict[str, Any]:
        """
        Playbook Test 5: Repeatability Analysis
        Same tap sample across repeated readings.
        Records: EC25 and TI mean ± SD, CV%.
        """
        engine = DecisionEngine()
        sim = WaterRigSimulator(engine)
        sim.set_scenario("CLEAN")

        ec_readings = []
        ti_readings = []

        for _ in range(n_runs):
            frame = sim.step()
            ec_readings.append(frame.ec25_uScm)
            ti_readings.append(frame.turb_index_pct)

        ec_mean = float(np.mean(ec_readings))
        ec_sd = float(np.std(ec_readings))
        ec_cv = (ec_sd / ec_mean * 100.0) if ec_mean > 0 else 0.0

        ti_mean = float(np.mean(ti_readings))
        ti_sd = float(np.std(ti_readings))
        ti_cv = (ti_sd / ti_mean * 100.0) if ti_mean > 0 else 0.0

        return {
            "test_name": "Repeatability Test (10 Runs)",
            "runs": n_runs,
            "ec25_mean": round(ec_mean, 1),
            "ec25_sd": round(ec_sd, 2),
            "ec25_cv_pct": round(ec_cv, 2),
            "ti_mean": round(ti_mean, 1),
            "ti_sd": round(ti_sd, 2),
            "ti_cv_pct": round(ti_cv, 2),
            "passed": ec_cv < 5.0 and ti_cv < 10.0
        }

if __name__ == "__main__":
    runner = PlaybookTestRunner()
    print("--- 1. Clogging Ramp Test ---")
    print(runner.run_clogging_ramp_test())
    print("\n--- 2. Classification Matrix ---")
    print(runner.run_classification_matrix())
    print("\n--- 3. Lock Logic Test ---")
    print(runner.run_lock_logic_test())
    print("\n--- 4. Fault Injection Timing ---")
    print(runner.run_fault_injection_benchmark())
    print("\n--- 5. Repeatability Test ---")
    print(runner.run_repeatability_test())
