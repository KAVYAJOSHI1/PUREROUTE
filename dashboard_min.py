#!/usr/bin/env python3
"""
PureRoute v2 — Minimal Matplotlib Dashboard (Playbook Step 1)
According to PureRoute v2 Decision Engine Playbook Page 8.

Usage:
    python3 dashboard_min.py [--port /dev/ttyACM0] [--baud 115200] [--sim]
"""

import argparse
import collections
import csv
import glob
import os
import sys
import threading
import time
import matplotlib.pyplot as plt
import matplotlib.animation as anim

HDR = [
    "t_ms", "temp_c", "flow_lpm", "pulses", "turb_mv", "turb_index_pct",
    "ec25_uScm", "tds_ppm", "fhi", "counter_life_pct", "pump", "lock",
    "state", "reason", "tag"
]

buf = collections.deque(maxlen=600)

def detect_default_port():
    ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/tty.*")
    if ports:
        return sorted(ports)[0]
    if sys.platform.startswith("win"):
        return "COM3"
    return "/dev/ttyACM0"

def serial_reader(port: str, baud: int):
    import serial
    csv_filename = time.strftime("run_%Y%m%d_%H%M%S.csv")
    print(f"Connecting to Serial {port} at {baud} baud...")
    print(f"Logging telemetry to {csv_filename}")
    
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HDR)
        f.flush()
        
        try:
            ser = serial.Serial(port, baud, timeout=1)
            time.sleep(1.8)
            print("Serial connection established. Reading frames...")
            while True:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) != len(HDR) or parts[0] == "t_ms":
                    continue
                w.writerow(parts)
                f.flush()
                buf.append(dict(zip(HDR, parts)))
        except Exception as e:
            print(f"Serial Error: {e}")
            print("Switching to simulation mode...")
            sim_reader()

def sim_reader():
    from engine.decision_engine import DecisionEngine
    from engine.simulator import WaterRigSimulator
    csv_filename = time.strftime("run_sim_%Y%m%d_%H%M%S.csv")
    print(f"[SIMULATION MODE] Logging to {csv_filename}")
    
    eng = DecisionEngine()
    sim = WaterRigSimulator(eng)
    
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HDR)
        while True:
            frame = sim.step()
            d = frame.to_dict()
            parts = [str(d[k]) for k in HDR]
            w.writerow(parts)
            f.flush()
            buf.append(d)
            time.sleep(1.0)

def main():
    parser = argparse.ArgumentParser(description="PureRoute v2 Step 1 Dashboard")
    parser.add_argument("--port", default=detect_default_port(), help="Serial port")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    parser.add_argument("--sim", action="store_true", help="Force simulation mode")
    args = parser.parse_args()

    if args.sim:
        threading.Thread(target=sim_reader, daemon=True).start()
    else:
        # Check if port exists or try connecting
        try:
            import serial
            threading.Thread(target=serial_reader, args=(args.port, args.baud), daemon=True).start()
        except ImportError:
            print("pyserial not found, running simulated mode")
            threading.Thread(target=sim_reader, daemon=True).start()

    fig, ax = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
    plt.subplots_adjust(hspace=0.25, top=0.92, bottom=0.08)

    def draw(_):
        if not buf:
            return
        rows = list(buf)
        try:
            x = [int(float(r["t_ms"])) / 1000.0 for r in rows]
            
            for a in ax:
                a.clear()
                a.grid(True, linestyle=":", alpha=0.6)

            # Panel 1: EC25
            ec_vals = [float(r["ec25_uScm"]) for r in rows]
            ax[0].plot(x, ec_vals, color="#0072BB", lw=2, label="EC25 (µS/cm)")
            ax[0].axhline(500, color="orange", linestyle="--", alpha=0.7, label="RO Switch (500 µS/cm)")
            ax[0].axhline(450, color="green", linestyle="--", alpha=0.7, label="UF Return (450 µS/cm)")
            ax[0].set_ylabel("EC25 (µS/cm)")
            ax[0].legend(loc="upper right", fontsize=8)

            # Panel 2: Turbidity Index
            turb_vals = [float(r["turb_index_pct"]) for r in rows]
            ax[1].plot(x, turb_vals, color="#E65100", lw=2, label="Turbidity Index (%)")
            ax[1].axhline(25, color="red", linestyle="--", alpha=0.7, label="Flush High (25%)")
            ax[1].axhline(10, color="green", linestyle="--", alpha=0.7, label="UF Low (10%)")
            ax[1].set_ylabel("Turb Index (%)")
            ax[1].legend(loc="upper right", fontsize=8)

            # Panel 3: FHI & Litre Counter
            fhi_vals = [float(r["fhi"]) for r in rows]
            cnt_vals = [float(r["counter_life_pct"]) for r in rows]
            ax[2].plot(x, fhi_vals, color="#2E7D32", lw=2, label="FHI (Measured Health)")
            ax[2].plot(x, cnt_vals, color="#757575", lw=1.5, linestyle="--", label="Litre Counter (Legacy)")
            ax[2].axhline(40, color="red", linestyle=":", alpha=0.8, label="Replace Threshold (40%)")
            ax[2].set_ylabel("Filter Health (%)")
            ax[2].legend(loc="lower left", fontsize=8)

            # Panel 4: Temperature
            temp_vals = [float(r["temp_c"]) for r in rows]
            ax[3].plot(x, temp_vals, color="#00838F", lw=1.8, label="DS18B20 Temp (°C)")
            ax[3].set_ylabel("Temp (°C)")
            ax[3].set_xlabel("Time (seconds)")
            ax[3].legend(loc="upper right", fontsize=8)

            # Title
            latest = rows[-1]
            state = latest["state"]
            reason = latest["reason"]
            pump = "PUMP ON" if str(latest["pump"]) == "1" else "PUMP OFF"
            fig.suptitle(f"[{state}] {reason} | {pump}", fontsize=13, fontweight="bold", color="#1A237E")
        except Exception:
            pass

    _ = anim.FuncAnimation(fig, draw, interval=1000)
    plt.show()

if __name__ == "__main__":
    main()
