# PureRoute v2 — Autonomous Multi-Sensor Decision Engine & Industrial SCADA Console

**Autonomous Multi-Sensor Water Monitoring, Predictive Filter Health & Regional Groundwater Hazard Enforcement**  
Built strictly according to the **PureRoute v2 Decision Engine Playbook** and **PureRoute v2 Hardware Playbook** for industrial water treatment and decentralized purification systems.

---

## 🚀 Quick Start

### 1. Launch the Live SCADA Dashboard
```bash
# Clone the repository
git clone git@github.com:KAVYAJOSHI1/PUREROUTE.git
cd PUREROUTE

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Launch the dashboard
./run.sh
```
Access the console at **[http://localhost:8501](http://localhost:8501)**.

### 2. Run Automated Verification Test Suite
```bash
python3 tools/run_logic_tests.py
```

---

## 🎨 Professional Industrial Design Language

The interface is built to enterprise SCADA standards (Linear, Stripe Dashboard, Vercel design language):
* **Strict Light Mode Foundation**: `#F7F8FA` background, `#FFFFFF` card surfaces, `#20242B` primary typography, and `#E5E7EB` borders.
* **Restrained Functional Palette**: Status colors are strictly isolated to active telemetry badges and threshold indicators:
  * **Healthy / UF+UV**: Muted Green (`#39815B` / `#EBF5F0`)
  * **RO+UV / Regional Hazard**: Muted Blue (`#2B5880` / `#EDF4FA`)
  * **Warning / Flush / Replace**: Muted Amber (`#8C5E1B` / `#FDF6EB`)
  * **Fault / Emergency Cutoff**: Muted Red (`#93302E` / `#FDF0ED`)
* **Zero Decorative Clutter**: No neon, no gradients, no glassmorphism, and no emojis used as UI decoration.

---

## 🖥️ 8 Dedicated System Views

| View | Purpose | Key Metrics & Features |
| :--- | :--- | :--- |
| **⊞ Overview** | High-level status & primary KPIs | Operating state banner, 4 primary metric cards (`DS18B20`, `YF-S401`, `SS304`, Optical Tip), FHI card, Decision Priority Hierarchy, Plotly time-series trends, and Essential Control Panel. |
| **〰 Live Monitoring** | Signal integrity & oscilloscope | 5-channel bus report showing pin wiring, raw acquisition signals, processed values, diagnostic states, and dual high-resolution oscilloscope charts. |
| **⏣ Filter Health** | Darcy's Law hydrodynamic analysis | Measured flow ratio FHI ($Q / Q_0$) vs blind litre counter comparison, membrane caking detection, manometer backpressure, and degradation forecast. |
| **⌥ Decision Engine** | State machine & fail-safe monitor | Active decision evaluation trace, 5s persistence counter, and 7-rule Firmware Fail-Safe Interlock Diagnostic Monitor. |
| **◎ Area Risk** | CGWB 2024 groundwater hazard engine | Regional hazard lookup, groundwater vs piped source selector, 4 contaminant indicators (As, F, $\text{NO}_3$, U), and Playbook Rules 1–7 summary. |
| **☑ Test Results** | Evidence-based BIS IS 10500 registry | Certified test report submission, **Rule 7 Arsenic test strip rejection**, 180-day validity tracking, and post-monsoon Nitrate surge re-locking. |
| **☲ Historical Logs** | Regulatory audit trail | 15-column immutable telemetry table conforming to Playbook specs, interactive state/query filtering, and full CSV export. |
| **⚙ Calibration & Settings** | Hardware sensor calibration deck | 60s flow turbine $K$ factor calculator, clear-water $V_0$ baseline save, fresh $Q_0$ baseline save, 5-point standard conductivity polynomial curve fit, and sensor diagnostic bus table. |

---

## 🧠 Decision Hierarchy & State Machine

The decision engine evaluates conditions top-to-bottom every second. A state transition requires holding for **5 consecutive seconds** (eliminating relay chatter) and only exits when hysteresis boundaries are satisfied:

| Priority | State | Indicator LED | Dispense Pump | Enter Condition | Exit Hysteresis | Example Rationale |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | `FAULT` | Red (Solid) | **DE-ENERGIZED (OFF)** | Any of 7 hardware fail-safe conditions active | Clear for 5 continuous seconds | `NO FLOW >3s pump ON -> dry run; pump OFF` |
| **2** | `LOCKED_RO` | Blue (Blinking) | **ENERGIZED (ON)** | Groundwater in CGWB flagged district & no certified test | Approved BIS test report on file | `District flag: As, NO3; no test on file -> RO forced` |
| **3** | `REPLACE` | Yellow (Solid) | **ENERGIZED (ON)** | $FHI < 40\%$ or $Q < 0.30\text{ L/min}$ | $FHI > 50\%$ | `FHI=35<40 (Q=0.42/Q0=1.10) -> REPLACE filter` |
| **4** | `FLUSH` | Yellow (Blinking) | **ENERGIZED (Routes Drain)** | Turbidity Index $TI > 25\%$ | $TI < 20\%$ | `TI=38%>25% -> FLUSH prefilter, protect UF/RO` |
| **5** | `RO` | Blue (Solid) | **ENERGIZED (ON)** | $EC25 > 500\ \mu\text{S/cm}$ or TDS $> 300\text{ ppm}$ | $EC25 < 450\ \mu\text{S/cm}$ | `EC25=812>500 -> RO+UV` |
| **6** | `UF+UV` | Green (Solid) | **ENERGIZED (ON)** | $EC25 \le 500\ \mu\text{S/cm}$, $TI < 10\%$, & no Area Lock | Continuous evaluation | `Clean water -> UF+UV (RO skipped)` |

---

## 🛡️ CGWB Area Risk & Evidence-Based Unlock Rules

1. **Rule 1 (Default Stance)**: Water sources default to their regional CGWB risk profile unless verified by an approved test on file.
2. **Rule 2 (Groundwater Only)**: Regional lock applies exclusively to groundwater (borewells/handpumps). Piped municipal water bypasses area lock because centralized municipal treatment removes heavy metal hazards.
3. **Rule 3 (Unlisted Districts)**: Unlisted districts show *"No flag found"*, but are **NEVER assumed safe without testing**.
4. **Rule 4 (No Test on File)**: Any flagged parameter forces RO+UV until certified proof is submitted.
5. **Rule 5 (Evidence Limits)**: Test reports must prove all flagged contaminants are strictly within BIS IS 10500 limits:
   * **Arsenic (As)**: $< 10\ \mu\text{g/L}$
   * **Fluoride (F)**: $\le 1.5\text{ mg/L}$
   * **Nitrate ($\text{NO}_3$)**: $\le 45\text{ mg/L}$
   * **Uranium (U)**: $\le 30\ \mu\text{g/L}$
6. **Rule 6 (Expiration & Monsoon)**: Test certificates expire after 180 days (6 months). Nitrate re-locks post-monsoon due to agricultural runoff surges.
7. **Rule 7 (Arsenic Strip Rejection)**: Colorimetric test strips CANNOT unlock Arsenic due to high false-negative risk (~54% in peer-reviewed field studies). An accredited NABL laboratory report is mandatory.

---

## ⚡ Hardware Pin Wiring & Serial Protocol

### ATmega328P Arduino Uno Pin Map
* **Pin D4**: Dallas DS18B20 1-Wire Temperature (4.7kΩ pull-up to 5V)
* **Pin D2**: YF-S401 Hall-Effect Flow Turbine (INT0 interrupt vector)
* **Pin A0**: Optical Turbidity Sensor Phototransistor (100nF filter capacitor)
* **Pins D7, D8, A1**: SS304 Bipolar AC Conductance Probe (alternating $\pm 400\mu\text{s}$ pulses)
* **Pin D5**: 12V Dispense Pump Relay / Logic-Level MOSFET
* **Pins D10, D11, D12, D13**: Status LEDs (Green: UF, Blue: RO, Yellow: Flush/Replace, Red: Fault)

### Supported Serial Commands (115200 Baud)
* `P1` / `P0`: Energize / De-energize dispense pump relay (requires confirmation in UI).
* `B`: Save current optical voltage as clear-water baseline $V_0$ to EEPROM.
* `F`: Save current flow rate as fresh-cartridge baseline $Q_0$ to EEPROM.
* `K<n>`: Set flow turbine calibration constant $K$ (pulses/L) to EEPROM.
* `S<tag>`: Set sample stream tag (e.g. `BENCH_01`).
* `L1` / `L0`: Enforce / Release regional groundwater hazard lock.

### 15-Column Telemetry Output Format
Every 1000ms, the Arduino emits a CSV row matching the Playbook specification:
```text
t_ms,temp_c,flow_lpm,pulses,turb_mv,turb_index_pct,ec25_uScm,tds_ppm,fhi,counter_life_pct,pump,lock,state,reason,tag
```

---

## 📁 Repository Directory Structure

```text
PUREROUTE/
├── app.py                             # Professional 8-View SCADA Console
├── dashboard_min.py                   # Minimal Matplotlib 4-Panel Verification Script
├── district_risk.csv                  # Official CGWB 2024 regional groundwater hazard dataset
├── requirements.txt                   # Production Python dependencies
├── run.sh                             # One-click dashboard startup script
├── sample_telemetry.csv               # Sample 15-column telemetry recording
├── .gitignore                         # Clean git exclusions (venv, logs, caches)
│
├── .streamlit/
│   └── config.toml                    # Explicit light-mode SCADA theme configuration
│
├── engine/                            # PureRoute Decision & Physics Engine
│   ├── __init__.py
│   ├── decision_engine.py             # 6-state state machine, 5s persistence, 7 fail-safes, FHI
│   ├── lock_module.py                 # CGWB regional lock & Rules 1–7 evidence engine
│   ├── simulator.py                   # Darcy's law bench rig simulation & scenario injection
│   ├── serial_reader.py               # 115200 baud USB serial reader with auto-reconnect
│   └── ui_components.py               # Linear-grade light-mode UI cards, Plotly charts, and badges
│
├── firmware/                          # Microcontroller Firmware
│   ├── PureRoute_Uno.ino              # Production Arduino Uno firmware
│   └── bringup/                       # Step-by-step bench rig bring-up sketches (Steps 1–8)
│
├── tools/                             # Calibration & Benchmarks
│   ├── calibration_helper.py          # Flow K factor & 5-point conductivity curve fit
│   └── run_logic_tests.py             # Automated CLI test suite for 5 Playbook benchmarks
│
├── PureRoute_v2_Decision_Engine_Playbook.pdf # Decision Engine Specification Document
└── PureRoute_v2_Hardware_Playbook.pdf        # Hardware Bench Rig & Bring-Up Playbook
```

---

## 🧪 Verification & Benchmark Results

Run the verification suite:
```bash
python3 tools/run_logic_tests.py
```
* **Test 1: Clogging Ramp Benchmark**: Demonstrates Darcy's law fouling ($Q$ drops to $0.24\text{ L/min}$, $FHI = 25.3\%$ in 31s while volume counter reads $99.4\%$).
* **Test 2: 5-Sample Classification Matrix**: 100% accurate classification across Clean Tap, Saline 1g/L, Saline 2g/L, Muddy Spike, and Salty+Muddy.
* **Test 3: Area Lock & BIS Unlock**: Full verification of Rules 1 through 7 (Arsenic strip rejection, failing test, passing test, 6-month expiry).
* **Test 4: Fault Injection Timing**: Benchmark proving all 7 physical fail-safe interlocks trigger automatic pump cutoff in $\le 7\text{s}$.
* **Test 5: Repeatability Benchmark**: 10 continuous runs proving $EC_{25}\ \text{CV} = 0.09\%$ and $\text{TI}\ \text{CV} = 1.47\%$.
* **Streamlit AppTest Suite**: All 8 pages verified with zero runtime exceptions.
